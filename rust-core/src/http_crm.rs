use std::collections::BTreeMap;
use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::{Path, PathBuf};

use chrono::Duration;
use serde_json::{json, Value};

use crate::approval_guard::ensure_approval_for_grant;
use crate::contracts::{
    CapabilityGrant, EventEnvelope, ExecutionReceipt, NodeState, RecoveryRecord, RecoveryStatus,
    ReplayFixture, TaskNode, Timestamp,
};
use crate::error::{CoreError, CoreResult};
use crate::event_log::EventLog;
use crate::projector::{EventProjector, MaterializedState};
use crate::replay::load_builtin_replay;
use crate::workspace::{WorkspaceExecutionOutcome, WorkspaceRecoveryOutcome};

#[derive(Debug, Clone)]
pub struct HttpCrmScenarioResult {
    pub fixture: ReplayFixture,
    pub event_log: EventLog,
    pub state: MaterializedState,
    pub runtime_dir: PathBuf,
}

#[derive(Debug, Clone)]
struct HttpCrmAdapter {
    base_url: String,
    artifact_dir: PathBuf,
}

impl HttpCrmAdapter {
    fn new(base_url: impl AsRef<str>, artifact_dir: impl AsRef<Path>) -> Self {
        Self {
            base_url: base_url.as_ref().trim_end_matches('/').to_owned(),
            artifact_dir: artifact_dir.as_ref().to_path_buf(),
        }
    }

    fn execute_node(
        &self,
        node: &TaskNode,
        action_spec: &Value,
        grant: &CapabilityGrant,
        occurred_at: Timestamp,
    ) -> CoreResult<WorkspaceExecutionOutcome> {
        fs::create_dir_all(&self.artifact_dir).map_err(io_error)?;

        let node_id = &node.node_id;
        let node_type = node.node_type.as_str();
        let (artifact_refs, fact_candidates, verification_evidence, recovery, side_effect_summary) =
            match node_type {
                "observe_sensitive_record" => {
                    let crm_record =
                        self.request_json("GET", "/crm/record", grant, None)?["crm_record"].clone();
                    let baseline_path = self.artifact_dir.join(format!("{node_id}_baseline.json"));
                    write_json(&baseline_path, &crm_record)?;
                    let fact = json!({
                        "fact_id": format!("fact_{node_id}_baseline"),
                        "fact_type": "observed",
                        "statement": format!(
                            "HTTP CRM baseline snapshot captured for {}",
                            crm_record["account_id"].as_str().unwrap_or("unknown")
                        ),
                        "provenance": {
                            "kind": "http-observation",
                            "url": format!("{}/crm/record", self.base_url),
                        },
                        "observed_at": occurred_at.to_rfc3339(),
                        "valid_until": (occurred_at + Duration::hours(2)).to_rfc3339(),
                        "attestation_level": "http_read_observation",
                        "confidence": 0.95,
                        "scope": {"url": format!("{}/crm/record", self.base_url)},
                        "evidence_refs": [artifact_ref(&baseline_path)],
                        "status": "candidate",
                        "version": 1,
                        "conflict_set": []
                    });
                    (
                        vec![artifact_ref(&baseline_path)],
                        vec![fact],
                        vec![artifact_ref(&baseline_path)],
                        None,
                        json!({"mode": "http_read", "url": format!("{}/crm/record", self.base_url)}),
                    )
                }
                "prepare_crm_patch" => {
                    let crm_record =
                        self.request_json("GET", "/crm/record", grant, None)?["crm_record"].clone();
                    let patch_path = self.artifact_dir.join(format!("{node_id}_patch.json"));
                    let draft_path = self
                        .artifact_dir
                        .join(format!("{node_id}_email_draft.json"));
                    let patch = json!({
                        "account_id": crm_record["account_id"],
                        "from_status": crm_record["renewal_status"],
                        "to_status": "ready_to_contact",
                    });
                    let draft = json!({
                        "to": crm_record["contact_email"],
                        "subject": format!("Renewal follow-up for {}", crm_record["account_name"].as_str().unwrap_or("unknown")),
                        "body": "Following up on your renewal review. We have your updated pricing context and can schedule a quick call.",
                    });
                    write_json(&patch_path, &patch)?;
                    write_json(&draft_path, &draft)?;
                    (
                        vec![artifact_ref(&patch_path), artifact_ref(&draft_path)],
                        Vec::new(),
                        vec![artifact_ref(&patch_path), artifact_ref(&draft_path)],
                        None,
                        json!({"mode": "prepare", "artifacts": [file_name(&patch_path)?, file_name(&draft_path)?]}),
                    )
                }
                "operate_crm_update" => {
                    let crm_record =
                        self.request_json("GET", "/crm/record", grant, None)?["crm_record"].clone();
                    let backup_path = self.artifact_dir.join(format!("{node_id}_backup.json"));
                    let rollback_path = self
                        .artifact_dir
                        .join(format!("{node_id}_rollback_plan.json"));
                    write_json(&backup_path, &crm_record)?;
                    self.request_json(
                        "PATCH",
                        "/crm/status",
                        grant,
                        Some(&json!({
                            "renewal_status": "ready_to_contact",
                            "at": occurred_at.to_rfc3339(),
                            "event": "status updated to ready_to_contact",
                        })),
                    )?;
                    write_json(
                        &rollback_path,
                        &json!({
                            "action": "rollback",
                            "restore_status": crm_record["renewal_status"],
                            "target": "/crm/status",
                        }),
                    )?;
                    (
                        vec![artifact_ref(&backup_path), artifact_ref(&rollback_path)],
                        Vec::new(),
                        vec![artifact_ref(&rollback_path)],
                        Some(json!({
                            "recovery_kind": "rollback",
                            "policy_ref": file_name(&rollback_path)?,
                        })),
                        json!({"mode": "http_write", "url": format!("{}/crm/status", self.base_url), "new_status": "ready_to_contact"}),
                    )
                }
                "commit_external_send" => {
                    let crm_record =
                        self.request_json("GET", "/crm/record", grant, None)?["crm_record"].clone();
                    let send_artifact =
                        self.artifact_dir.join(format!("{node_id}_sent_email.json"));
                    let compensation_path = self
                        .artifact_dir
                        .join(format!("{node_id}_compensation_plan.json"));
                    let message = json!({
                        "message_id": format!("msg_{}", crm_record["account_id"].as_str().unwrap_or("unknown")),
                        "to": crm_record["contact_email"],
                        "subject": format!("Renewal follow-up for {}", crm_record["account_name"].as_str().unwrap_or("unknown")),
                        "body": "Following up on your renewal review. Let us know a convenient time this week.",
                        "sent_at": occurred_at.to_rfc3339(),
                    });
                    let send_result =
                        self.request_json("POST", "/messages/send", grant, Some(&message))?;
                    write_json(&send_artifact, &send_result["message"])?;
                    write_json(
                        &compensation_path,
                        &json!({
                            "action": "compensate",
                            "kind": "send_correction_message",
                            "reason": "message send is irreversible; correction message is the bounded compensation path",
                            "target_message_id": send_result["message"]["message_id"],
                        }),
                    )?;
                    (
                        vec![
                            artifact_ref(&send_artifact),
                            artifact_ref(&compensation_path),
                        ],
                        Vec::new(),
                        vec![artifact_ref(&send_artifact)],
                        Some(json!({
                            "recovery_kind": "compensate",
                            "policy_ref": file_name(&compensation_path)?,
                        })),
                        json!({
                            "mode": "http_commit",
                            "url": format!("{}/messages/send", self.base_url),
                            "outbox_entries": send_result["outbox_entries"],
                        }),
                    )
                }
                other => {
                    return Err(CoreError::NotYetImplemented(format!(
                        "unsupported http node type: {other}"
                    )))
                }
            };

        let action_id = action_spec
            .get("action_id")
            .and_then(|value| value.as_str())
            .unwrap_or("action_http_mock_crm");

        let receipt = ExecutionReceipt {
            receipt_id: format!("receipt_{node_id}_{}", occurred_at.format("%H%M%S")),
            action_id: action_id.to_owned(),
            task_id: node.task_id.clone(),
            node_id: node.node_id.clone(),
            grant_id: grant.grant_id.clone(),
            executor_id: "executor.http.mock_crm".to_owned(),
            status: "succeeded_with_receipt".to_owned(),
            started_at: occurred_at,
            ended_at: occurred_at + Duration::seconds(1),
            artifact_refs: artifact_refs.clone(),
            side_effect_summary: side_effect_summary.clone(),
            environment_digest: json!({
                "executor": "executor.http.mock_crm",
                "mode": "http",
                "base_url": self.base_url,
            }),
            retry_index: 0,
            error_summary: json!({}),
        };

        Ok(WorkspaceExecutionOutcome {
            receipt,
            fact_candidates,
            verification_evidence,
            recovery,
            side_effect_summary,
        })
    }

    fn execute_recovery(
        &self,
        recovery: &RecoveryRecord,
        occurred_at: Timestamp,
        grant: &CapabilityGrant,
    ) -> CoreResult<WorkspaceRecoveryOutcome> {
        let policy_path = self.artifact_dir.join(&recovery.policy_ref);
        let policy = read_json(&policy_path)?;

        match recovery.action.as_str() {
            "compensate" => {
                let crm_record =
                    self.request_json("GET", "/crm/record", grant, None)?["crm_record"].clone();
                let correction = json!({
                    "message_id": format!("correction_{}", policy["target_message_id"].as_str().unwrap_or("unknown")),
                    "to": crm_record["contact_email"],
                    "subject": format!("Correction for {} renewal follow-up", crm_record["account_name"].as_str().unwrap_or("unknown")),
                    "body": "Correction: please disregard the previous follow-up if timing is no longer convenient. We can resend on request.",
                    "sent_at": occurred_at.to_rfc3339(),
                    "kind": "correction_message",
                    "target_message_id": policy["target_message_id"],
                });
                let response =
                    self.request_json("POST", "/messages/correction", grant, Some(&correction))?;
                let artifact_path = self
                    .artifact_dir
                    .join(format!("{}_compensation_executed.json", recovery.node_id));
                write_json(&artifact_path, &response["message"])?;
                Ok(WorkspaceRecoveryOutcome {
                    artifact_refs: vec![artifact_ref(&artifact_path)],
                    side_effect_summary: json!({
                        "mode": "compensate",
                        "target_message_id": policy["target_message_id"],
                        "outbox_entries": response["outbox_entries"],
                    }),
                })
            }
            "rollback" => {
                let response = self.request_json(
                    "POST",
                    "/crm/restore-status",
                    grant,
                    Some(&json!({
                        "renewal_status": policy["restore_status"],
                        "restored_at": occurred_at.to_rfc3339(),
                    })),
                )?;
                let artifact_path = self
                    .artifact_dir
                    .join(format!("{}_rollback_executed.json", recovery.node_id));
                write_json(
                    &artifact_path,
                    &json!({
                        "restored_status": response["crm_record"]["renewal_status"],
                        "restored_at": occurred_at.to_rfc3339(),
                    }),
                )?;
                Ok(WorkspaceRecoveryOutcome {
                    artifact_refs: vec![artifact_ref(&artifact_path)],
                    side_effect_summary: json!({
                        "mode": "rollback",
                        "restored_status": response["crm_record"]["renewal_status"],
                    }),
                })
            }
            other => Err(CoreError::NotYetImplemented(format!(
                "unsupported recovery action: {other}"
            ))),
        }
    }

    fn request_json(
        &self,
        method: &str,
        path: &str,
        grant: &CapabilityGrant,
        payload: Option<&Value>,
    ) -> CoreResult<Value> {
        let authority = http_authority(&self.base_url)?;
        let body = payload
            .map(serde_json::to_string)
            .transpose()
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let mut request = format!(
            "{method} {path} HTTP/1.1\r\nHost: {authority}\r\nAccept: application/json\r\nX-Grant-Id: {}\r\nX-Principal-Ref: {}\r\nConnection: close\r\n",
            grant.grant_id, grant.principal_ref
        );
        if let Some(body) = &body {
            request.push_str(&format!(
                "Content-Type: application/json\r\nContent-Length: {}\r\n",
                body.len()
            ));
            request.push_str("\r\n");
            request.push_str(body);
        } else {
            request.push_str("\r\n");
        }

        let mut stream = TcpStream::connect(authority)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        stream
            .write_all(request.as_bytes())
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        let mut response = String::new();
        stream
            .read_to_string(&mut response)
            .map_err(|error| CoreError::Serialization(error.to_string()))?;
        response_json(&response)
    }
}

#[derive(Debug)]
pub struct HttpCrmScenarioRunner {
    fixture: ReplayFixture,
    runtime_dir: PathBuf,
    adapter: HttpCrmAdapter,
    event_log: EventLog,
    projector: EventProjector,
    current_index: usize,
    execution_cache: BTreeMap<String, WorkspaceExecutionOutcome>,
}

impl HttpCrmScenarioRunner {
    pub fn new(base_url: impl AsRef<str>, runtime_dir: impl AsRef<Path>) -> CoreResult<Self> {
        let fixture = load_builtin_replay("crm-followup-flow.json")?;
        let runtime_dir = runtime_dir.as_ref().to_path_buf();
        let adapter = HttpCrmAdapter::new(base_url, runtime_dir.join("artifacts"));
        Ok(Self {
            fixture,
            runtime_dir,
            adapter,
            event_log: EventLog::new(),
            projector: EventProjector::new(),
            current_index: 0,
            execution_cache: BTreeMap::new(),
        })
    }

    pub fn run(mut self) -> CoreResult<HttpCrmScenarioResult> {
        self.prepare_runtime()?;
        self.run_steps()?;
        Ok(self.result())
    }

    pub fn run_with_compensation(mut self) -> CoreResult<HttpCrmScenarioResult> {
        self.prepare_runtime()?;
        self.run_steps()?;
        let armed = self
            .projector
            .state
            .recoveries
            .values()
            .filter(|recovery| recovery.status == RecoveryStatus::Armed)
            .cloned()
            .collect::<Vec<_>>();

        for (index, recovery) in armed.iter().enumerate() {
            let occurred_at =
                base_time() + Duration::minutes(20) + Duration::seconds((index + 1) as i64);
            let grant = self.latest_grant_for_node(&recovery.node_id)?;
            let outcome = self
                .adapter
                .execute_recovery(recovery, occurred_at, &grant)?;
            self.emit_event(
                90 + (index as u32) + 1,
                "recovery.recorded",
                json!({
                    "recovery": {
                        "recovery_id": format!("{}.executed", recovery.recovery_id),
                        "task_id": recovery.task_id,
                        "node_id": recovery.node_id,
                        "action": recovery.action,
                        "recorded_at": occurred_at.to_rfc3339(),
                        "policy_ref": recovery.policy_ref,
                        "status": "executed",
                        "artifact_refs": outcome.artifact_refs,
                        "side_effect_summary": outcome.side_effect_summary,
                    }
                }),
                &recovery.node_id,
                &format!("recovery-executed-{}", index + 1),
            )?;
        }

        Ok(self.result())
    }

    fn result(&self) -> HttpCrmScenarioResult {
        HttpCrmScenarioResult {
            fixture: self.fixture.clone(),
            event_log: self.event_log.clone(),
            state: self.projector.state.clone(),
            runtime_dir: self.runtime_dir.clone(),
        }
    }

    fn prepare_runtime(&self) -> CoreResult<()> {
        if self.runtime_dir.exists() {
            fs::remove_dir_all(&self.runtime_dir).map_err(io_error)?;
        }
        fs::create_dir_all(self.runtime_dir.join("artifacts")).map_err(io_error)
    }

    fn run_steps(&mut self) -> CoreResult<()> {
        self.emit_event(
            0,
            "task.created",
            self.build_task_created_payload(),
            &self.root_node_id(),
            "bootstrap",
        )?;
        let timeline = self.fixture.timeline.clone();
        for step in timeline {
            self.ensure_node_ready(step.step, &step.node_id)?;
            for (token_index, token) in step.events.iter().enumerate() {
                self.emit_token(&step, token, token_index + 1)?;
            }
        }
        Ok(())
    }

    fn emit_token(
        &mut self,
        step: &crate::contracts::ReplayStep,
        token: &str,
        token_index: usize,
    ) -> CoreResult<()> {
        match token {
            "grant.issued" => {
                let grant = self.build_grant(step, token_index)?;
                self.emit_event(step.step, token, json!({ "grant": grant }), &step.node_id, &format!("{token_index}-grant"))
            }
            "approval.recorded" => {
                self.ensure_node_awaiting_approval(step.step, &step.node_id)?;
                self.emit_event(
                    step.step,
                    token,
                    json!({ "approval": self.build_approval(step, token_index) }),
                    &step.node_id,
                    &format!("{token_index}-approval"),
                )?;
                self.restore_node_ready_after_approval(step.step, &step.node_id)
            }
            "action.dispatched" => self.emit_event(
                step.step,
                token,
                json!({
                    "task_id": self.task_id(),
                    "node_id": step.node_id,
                    "action_id": format!("action_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
                    "required_capability": self.required_capability(&step.node_id),
                }),
                &step.node_id,
                &format!("{token_index}-dispatch"),
            ),
            "receipt.recorded" => {
                let receipt = self.build_receipt(step, token_index)?;
                self.emit_event(step.step, token, json!({ "receipt": receipt }), &step.node_id, &format!("{token_index}-receipt"))
            }
            "verification.recorded" => {
                let facts = self.pending_facts(step, token_index)?;
                for (fact_index, fact) in facts.into_iter().enumerate() {
                    self.emit_event(
                        step.step,
                        "fact.observed",
                        json!({ "fact": fact }),
                        &step.node_id,
                        &format!("{token_index}-fact-{fact_index}"),
                    )?;
                }
                let verification = self.build_verification(step, token_index)?;
                self.emit_event(
                    step.step,
                    token,
                    json!({ "verification": verification }),
                    &step.node_id,
                    &format!("{token_index}-verify"),
                )
            }
            "recovery.recorded" => {
                let recovery = self.build_recovery(step, token_index)?;
                self.emit_event(
                    step.step,
                    token,
                    json!({ "recovery": recovery }),
                    &step.node_id,
                    &format!("{token_index}-recovery"),
                )
            }
            token if token.starts_with("node.state_changed(") => {
                let transition = token
                    .trim_start_matches("node.state_changed(")
                    .trim_end_matches(')');
                let mut parts = transition.split("->");
                let from_state = parts.next().unwrap_or("created");
                let to_state = parts.next().unwrap_or("ready");
                self.emit_event(
                    step.step,
                    "node.state_changed",
                    json!({
                        "task_id": self.task_id(),
                        "node_id": step.node_id,
                        "from_state": from_state,
                        "to_state": to_state,
                        "changed_at": self.time_for_step(step.step, token_index).to_rfc3339()
                    }),
                    &step.node_id,
                    &format!("{token_index}-state"),
                )
            }
            other => Err(CoreError::UnsupportedEventType(other.to_owned())),
        }
    }

    fn build_task_created_payload(&self) -> Value {
        let task_type = self
            .fixture
            .task_profile
            .get("task_path")
            .and_then(|value| value.as_array())
            .and_then(|items| items.last())
            .and_then(|value| value.as_str())
            .unwrap_or("Commit");

        let attention_budget = self
            .fixture
            .task_profile
            .get("attention_budget_profile")
            .cloned()
            .unwrap_or_else(|| json!({ "max_interruptions": 2 }));

        let nodes = self
            .fixture
            .nodes
            .iter()
            .enumerate()
            .map(|(index, node)| {
                let dependencies = if index == 0 {
                    Vec::<String>::new()
                } else {
                    vec![self.fixture.nodes[index - 1].node_id.clone()]
                };
                json!({
                    "node_id": node.node_id,
                    "task_id": self.task_id(),
                    "node_type": node.node_type,
                    "objective": node.purpose,
                    "desired_delta": { "purpose": node.purpose },
                    "evidence_of_done": { "expected_terminal": node.expected_terminal },
                    "risk_class": node.risk_band,
                    "state": "created",
                    "dependencies": dependencies,
                    "required_capabilities": [format!("structured.{}", node.node_type)],
                    "principal_ref": "principal.user.primary",
                    "resource_owner_ref": "owner.workspace.primary",
                    "grant_refs": [],
                    "artifact_refs": [],
                    "version": 1,
                    "created_at": base_time().to_rfc3339(),
                    "updated_at": base_time().to_rfc3339()
                })
            })
            .collect::<Vec<_>>();

        json!({
            "task": {
                "task_id": self.task_id(),
                "objective": self.fixture.goal,
                "desired_delta": { "goal": self.fixture.goal },
                "evidence_of_done": { "proof_refs": self.fixture.terminal_expectation.get("proof").cloned().unwrap_or_else(|| json!([])) },
                "task_type": task_type,
                "risk_class": self.fixture.task_profile.get("default_risk_band").cloned().unwrap_or_else(|| json!("R2")),
                "reversibility": { "mode": "bounded-or-none" },
                "attention_budget": attention_budget,
                "constraints": {
                    "source": "http-crm-scenario",
                    "task_path": self.fixture.task_profile.get("task_path").cloned().unwrap_or_else(|| json!([]))
                },
                "root_node_id": self.root_node_id(),
                "principal_ref": "principal.user.primary",
                "resource_owner_ref": "owner.workspace.primary",
                "approver_ref": "principal.user.primary"
            },
            "nodes": nodes
        })
    }

    fn ensure_node_ready(&mut self, step_number: u32, node_id: &str) -> CoreResult<()> {
        if self
            .projector
            .state
            .nodes
            .get(node_id)
            .map(|node| node.state == NodeState::Created)
            .unwrap_or(false)
        {
            self.emit_event(
                step_number,
                "node.state_changed",
                json!({
                    "task_id": self.task_id(),
                    "node_id": node_id,
                    "from_state": "created",
                    "to_state": "ready",
                    "changed_at": self.time_for_step(step_number, 0).to_rfc3339()
                }),
                node_id,
                "synthetic-ready",
            )?;
        }
        Ok(())
    }

    fn ensure_node_awaiting_approval(&mut self, step_number: u32, node_id: &str) -> CoreResult<()> {
        if self
            .projector
            .state
            .nodes
            .get(node_id)
            .map(|node| node.state == NodeState::Ready)
            .unwrap_or(false)
        {
            self.emit_event(
                step_number,
                "node.state_changed",
                json!({
                    "task_id": self.task_id(),
                    "node_id": node_id,
                    "from_state": "ready",
                    "to_state": "awaiting_approval",
                    "changed_at": self.time_for_step(step_number, 0).to_rfc3339()
                }),
                node_id,
                "awaiting-approval",
            )?;
        }
        Ok(())
    }

    fn restore_node_ready_after_approval(
        &mut self,
        step_number: u32,
        node_id: &str,
    ) -> CoreResult<()> {
        if self
            .projector
            .state
            .nodes
            .get(node_id)
            .map(|node| node.state == NodeState::AwaitingApproval)
            .unwrap_or(false)
        {
            self.emit_event(
                step_number,
                "node.state_changed",
                json!({
                    "task_id": self.task_id(),
                    "node_id": node_id,
                    "from_state": "awaiting_approval",
                    "to_state": "ready",
                    "changed_at": self.time_for_step(step_number, 1).to_rfc3339()
                }),
                node_id,
                "approval-restored-ready",
            )?;
        }
        Ok(())
    }

    fn build_approval(&self, step: &crate::contracts::ReplayStep, token_index: usize) -> Value {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self
            .projector
            .state
            .nodes
            .get(&step.node_id)
            .expect("node present");
        json!({
            "approval_id": format!("approval_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "approver_id": "principal.user.primary",
            "approved_at": occurred_at.to_rfc3339(),
            "status": "approved",
            "risk_class": node.risk_class,
            "approval_kind": "explicit",
            "selection_ref": step.node_id,
            "summary": step.notes.clone().unwrap_or_else(|| step.command.clone()),
        })
    }

    fn build_grant(
        &self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<CapabilityGrant> {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self
            .projector
            .state
            .nodes
            .get(&step.node_id)
            .expect("node present");
        let task = self
            .projector
            .state
            .tasks
            .get(&self.task_id())
            .expect("task present");
        ensure_approval_for_grant(&self.projector.state.approvals, node, task, None)?;
        serde_json::from_value(json!({
            "grant_id": format!("grant_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "who": "executor.http.mock_crm",
            "what": self.required_capability(&step.node_id),
            "where": { "node_id": step.node_id },
            "when": {
                "not_before": occurred_at.to_rfc3339(),
                "not_after": (occurred_at + Duration::minutes(10)).to_rfc3339()
            },
            "budget": { "max_retries": 1, "max_minutes": 10 },
            "why": step.command,
            "approval_ref": format!("approval_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "postcondition_ref": format!("postcondition_{}_{}", self.fixture.replay_id, step.node_id),
            "principal_ref": "principal.user.primary",
            "resource_owner_ref": "owner.workspace.primary",
            "approver_ref": "principal.user.primary",
            "status": "active",
            "issued_at": occurred_at.to_rfc3339(),
            "expires_at": (occurred_at + Duration::minutes(10)).to_rfc3339()
        }))
        .map_err(|error| CoreError::Serialization(error.to_string()))
    }

    fn build_receipt(
        &mut self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<Value> {
        let outcome = self.execution_outcome(step, token_index)?;
        serde_json::to_value(outcome.receipt.clone())
            .map_err(|error| CoreError::Serialization(error.to_string()))
    }

    fn pending_facts(
        &mut self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<Vec<Value>> {
        let outcome = self.execution_outcome(step, token_index)?;
        Ok(outcome.fact_candidates.clone())
    }

    fn build_verification(
        &self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<Value> {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self
            .fixture
            .nodes
            .iter()
            .find(|node| node.node_id == step.node_id)
            .expect("fixture node present");
        let receipt_refs = self
            .projector
            .state
            .node_receipts
            .get(&step.node_id)
            .cloned()
            .unwrap_or_default();
        let mut supporting_evidence = receipt_refs.clone();
        if let Some(last_receipt) = receipt_refs
            .last()
            .and_then(|receipt_id| self.projector.state.receipts.get(receipt_id))
        {
            supporting_evidence.extend(last_receipt.artifact_refs.clone());
        }
        let target_state =
            if step.events.iter().any(|token| {
                token.starts_with("node.state_changed(") && token.contains("->completed")
            }) {
                self.projector
                    .state
                    .nodes
                    .get(&step.node_id)
                    .map(|node| node.state.clone())
                    .unwrap_or(NodeState::Completed)
            } else {
                node.expected_terminal.clone()
            };
        let fact_promotions = if node.node_type == "observe_sensitive_record" {
            vec![format!("fact_{}_baseline", step.node_id)]
        } else {
            Vec::new()
        };
        Ok(json!({
            "verification_id": format!("verification_{}_{}_{}", self.task_id(), step.node_id, occurred_at.format("%H%M%S")),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "receipt_refs": receipt_refs,
            "result": "verified_success",
            "supporting_evidence": supporting_evidence,
            "remaining_uncertainties": [],
            "state_transition": {
                "to": target_state,
                "fact_promotions": fact_promotions
            },
            "verified_at": occurred_at.to_rfc3339(),
            "verifier_id": "verifier.http.mock_crm",
            "recommended_recovery_action": self.fixture.terminal_expectation.get("recovery_mode").cloned(),
        }))
    }

    fn build_recovery(
        &mut self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<Value> {
        let occurred_at = self.time_for_step(step.step, token_index);
        let outcome = self.execution_outcome(step, token_index)?;
        let recovery = outcome
            .recovery
            .clone()
            .ok_or_else(|| CoreError::Serialization("expected recovery metadata".to_owned()))?;
        Ok(json!({
            "recovery_id": format!("recovery_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "action": recovery.get("recovery_kind").cloned().unwrap_or_else(|| json!("rollback")),
            "recorded_at": occurred_at.to_rfc3339(),
            "policy_ref": recovery.get("policy_ref").cloned().unwrap_or_else(|| json!("policy.json")),
            "status": "armed"
        }))
    }

    fn execution_outcome(
        &mut self,
        step: &crate::contracts::ReplayStep,
        token_index: usize,
    ) -> CoreResult<&WorkspaceExecutionOutcome> {
        if !self.execution_cache.contains_key(&step.node_id) {
            let occurred_at = self.time_for_step(step.step, token_index);
            let node = self
                .projector
                .state
                .nodes
                .get(&step.node_id)
                .expect("node present");
            let grant = self.latest_grant_for_node(&step.node_id)?;
            let action_spec = json!({
                "action_id": format!("action_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
                "required_capability": self.required_capability(&step.node_id),
                "side_effect_class": self.side_effect_class(node),
            });
            let outcome = self
                .adapter
                .execute_node(node, &action_spec, &grant, occurred_at)?;
            self.execution_cache.insert(step.node_id.clone(), outcome);
        }
        self.execution_cache
            .get(&step.node_id)
            .ok_or_else(|| CoreError::Serialization("missing cached execution outcome".to_owned()))
    }

    fn latest_grant_for_node(&self, node_id: &str) -> CoreResult<CapabilityGrant> {
        self.projector
            .state
            .grants
            .values()
            .filter(|grant| grant.task_id == self.task_id() && grant.node_id == node_id)
            .cloned()
            .max_by(|left, right| left.issued_at.cmp(&right.issued_at))
            .ok_or_else(|| CoreError::DispatchDenied {
                task_id: self.task_id(),
                node_id: node_id.to_owned(),
            })
    }

    fn emit_event(
        &mut self,
        step_number: u32,
        event_type: &str,
        payload: Value,
        node_id: &str,
        suffix: &str,
    ) -> CoreResult<()> {
        let event = EventEnvelope {
            event_id: format!("{}.{}.{}", self.fixture.replay_id, step_number, suffix),
            event_type: event_type.to_owned(),
            actor_id: "http_crm.runner".to_owned(),
            occurred_at: self.time_for_step(step_number, self.current_index + 1),
            payload,
            task_id: self.task_id(),
            node_id: node_id.to_owned(),
            trace_ref: self.fixture.replay_id.clone(),
            causation_ref: self
                .event_log
                .as_slice()
                .last()
                .map(|event| event.event_id.clone()),
            correlation_ref: Some(self.fixture.replay_id.clone()),
        };
        if self.event_log.append(event.clone())? {
            self.projector.apply(&event)?;
            self.current_index += 1;
        }
        Ok(())
    }

    fn required_capability(&self, node_id: &str) -> String {
        self.projector
            .state
            .nodes
            .get(node_id)
            .and_then(|node| node.required_capabilities.first().cloned())
            .unwrap_or_else(|| "structured.http".to_owned())
    }

    fn side_effect_class(&self, node: &TaskNode) -> &'static str {
        if node.node_type.starts_with("commit_")
            || matches!(node.risk_class, crate::contracts::RiskBand::R3)
        {
            "irreversible_external_send"
        } else if matches!(node.risk_class, crate::contracts::RiskBand::R2) {
            "bounded_external_modify"
        } else {
            "bounded_local"
        }
    }

    fn task_id(&self) -> String {
        format!("task_{}", self.fixture.replay_id)
    }

    fn root_node_id(&self) -> String {
        self.fixture
            .nodes
            .first()
            .map(|node| node.node_id.clone())
            .unwrap_or_else(|| "node_root".to_owned())
    }

    fn time_for_step(&self, step_number: u32, offset: usize) -> Timestamp {
        base_time() + Duration::minutes((step_number * 2) as i64) + Duration::seconds(offset as i64)
    }
}

pub fn run_http_crm_scenario(
    base_url: impl AsRef<str>,
    runtime_dir: impl AsRef<Path>,
) -> CoreResult<HttpCrmScenarioResult> {
    HttpCrmScenarioRunner::new(base_url, runtime_dir)?.run()
}

pub fn run_http_crm_with_compensation(
    base_url: impl AsRef<str>,
    runtime_dir: impl AsRef<Path>,
) -> CoreResult<HttpCrmScenarioResult> {
    HttpCrmScenarioRunner::new(base_url, runtime_dir)?.run_with_compensation()
}

fn base_time() -> Timestamp {
    Timestamp::parse_from_rfc3339("2026-04-10T09:00:00+08:00").expect("valid base time")
}

fn artifact_ref(path: &Path) -> String {
    format!(
        "artifact::{}",
        path.file_name()
            .expect("artifact path should have file name")
            .to_string_lossy()
    )
}

fn file_name(path: &Path) -> CoreResult<String> {
    path.file_name()
        .map(|name| name.to_string_lossy().to_string())
        .ok_or_else(|| CoreError::Serialization("artifact path should have file name".to_owned()))
}

fn read_json(path: &Path) -> CoreResult<Value> {
    let raw = fs::read_to_string(path).map_err(io_error)?;
    serde_json::from_str(&raw).map_err(|error| CoreError::Serialization(error.to_string()))
}

fn write_json(path: &Path, payload: &Value) -> CoreResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(io_error)?;
    }
    let serialized = serde_json::to_string_pretty(payload)
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
    fs::write(path, serialized).map_err(io_error)
}

fn http_authority(base_url: &str) -> CoreResult<&str> {
    let authority = base_url.strip_prefix("http://").ok_or_else(|| {
        CoreError::Serialization("mock HTTP adapter only supports http:// base URLs".to_owned())
    })?;
    if authority.contains('/') {
        return Err(CoreError::Serialization(
            "mock HTTP adapter base URL should not include a path".to_owned(),
        ));
    }
    Ok(authority)
}

fn response_json(response: &str) -> CoreResult<Value> {
    let (head, body) = response
        .split_once("\r\n\r\n")
        .ok_or_else(|| CoreError::Serialization("invalid HTTP response".to_owned()))?;
    let status_code = head
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse::<u16>().ok())
        .ok_or_else(|| CoreError::Serialization("invalid HTTP status line".to_owned()))?;
    if !(200..300).contains(&status_code) {
        return Err(CoreError::Serialization(format!(
            "http request failed with status {status_code}"
        )));
    }
    serde_json::from_str(body).map_err(|error| CoreError::Serialization(error.to_string()))
}

fn io_error(error: std::io::Error) -> CoreError {
    CoreError::Serialization(error.to_string())
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use crate::contracts::RiskBand;
    use crate::mock_http_crm::MockHttpCrmServer;

    use super::*;

    fn unique_runtime_dir(name: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time should be after unix epoch")
            .as_nanos();
        std::env::temp_dir()
            .join("device-agent-doc-rust-http-adapter-tests")
            .join(format!("{name}-{}-{nonce}", std::process::id()))
    }

    fn seed_dir() -> PathBuf {
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("sandbox")
            .join("local-crm")
            .join("seed")
    }

    fn sample_write_node() -> TaskNode {
        TaskNode {
            node_id: "node_write_crm".to_owned(),
            task_id: "task_replay_crm_followup_001".to_owned(),
            node_type: "operate_crm_update".to_owned(),
            objective: "write crm status".to_owned(),
            desired_delta: json!({"status": "ready_to_contact"}),
            evidence_of_done: json!({"terminal": "completed"}),
            risk_class: RiskBand::R2,
            state: NodeState::Ready,
            dependencies: Vec::new(),
            required_capabilities: vec!["structured.operate_crm_update".to_owned()],
            principal_ref: "principal.user.primary".to_owned(),
            resource_owner_ref: "owner.workspace.primary".to_owned(),
            grant_refs: Vec::new(),
            artifact_refs: Vec::new(),
            version: 1,
            created_at: base_time(),
            updated_at: base_time(),
        }
    }

    fn sample_grant(node_id: &str) -> CapabilityGrant {
        CapabilityGrant {
            grant_id: format!("grant_{node_id}"),
            task_id: "task_replay_crm_followup_001".to_owned(),
            node_id: node_id.to_owned(),
            who: "executor.http.mock_crm".to_owned(),
            what: format!("structured.{node_id}"),
            scope: json!({"node_id": node_id}),
            window: json!({
                "not_before": base_time().to_rfc3339(),
                "not_after": (base_time() + Duration::minutes(10)).to_rfc3339(),
            }),
            budget: json!({"max_retries": 1}),
            reason: "test".to_owned(),
            approval_ref: format!("approval_{node_id}"),
            postcondition_ref: format!("postcondition_{node_id}"),
            principal_ref: "principal.user.primary".to_owned(),
            resource_owner_ref: "owner.workspace.primary".to_owned(),
            approver_ref: "principal.user.primary".to_owned(),
            status: "active".to_owned(),
            issued_at: base_time(),
            expires_at: base_time() + Duration::minutes(10),
        }
    }

    #[test]
    fn http_adapter_rollback_recovery_restores_remote_status() {
        let server = MockHttpCrmServer::new(seed_dir()).expect("server should start");
        let runtime_dir = unique_runtime_dir("rollback");
        let adapter = HttpCrmAdapter::new(server.base_url(), runtime_dir.join("artifacts"));
        let node = sample_write_node();
        let grant = sample_grant(&node.node_id);

        let outcome = adapter
            .execute_node(
                &node,
                &json!({
                    "action_id": "action_node_write_crm",
                    "required_capability": "structured.operate_crm_update",
                    "side_effect_class": "bounded_external_modify",
                }),
                &grant,
                base_time() + Duration::minutes(1),
            )
            .expect("http write should succeed");

        assert_eq!(
            outcome.recovery.expect("rollback should be armed")["recovery_kind"],
            json!("rollback")
        );
        assert_eq!(
            server
                .snapshot()
                .expect("snapshot should succeed")
                .crm_record["renewal_status"],
            json!("ready_to_contact")
        );

        let rollback = RecoveryRecord {
            recovery_id: "recovery_node_write_crm".to_owned(),
            task_id: "task_replay_crm_followup_001".to_owned(),
            node_id: node.node_id.clone(),
            action: "rollback".to_owned(),
            recorded_at: base_time() + Duration::minutes(2),
            policy_ref: "node_write_crm_rollback_plan.json".to_owned(),
            status: RecoveryStatus::Armed,
            artifact_refs: Vec::new(),
            side_effect_summary: None,
        };

        let recovery_outcome = adapter
            .execute_recovery(&rollback, base_time() + Duration::minutes(3), &grant)
            .expect("rollback should succeed");

        assert_eq!(
            recovery_outcome.side_effect_summary["mode"],
            json!("rollback")
        );
        assert_eq!(
            server
                .snapshot()
                .expect("snapshot should succeed")
                .crm_record["renewal_status"],
            json!("pending_review")
        );
        assert!(runtime_dir
            .join("artifacts")
            .join("node_write_crm_rollback_executed.json")
            .exists());
    }
}

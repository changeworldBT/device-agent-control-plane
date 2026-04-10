use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::Duration;
use serde_json::{json, Value};

use crate::approval_guard::ensure_approval_for_grant;
use crate::contracts::{
    CapabilityGrant, EventEnvelope, NodeState, RecoveryStatus, ReplayFixture, TaskNode, Timestamp,
};
use crate::error::{CoreError, CoreResult};
use crate::event_log::EventLog;
use crate::projector::{EventProjector, MaterializedState};
use crate::replay::load_builtin_replay;
use crate::workspace::{LocalWorkspaceAdapter, WorkspaceAdapter, WorkspaceExecutionOutcome};

#[derive(Debug, Clone)]
pub struct LocalCrmScenarioResult {
    pub fixture: ReplayFixture,
    pub event_log: EventLog,
    pub state: MaterializedState,
    pub runtime_dir: PathBuf,
}

#[derive(Debug)]
pub struct LocalCrmScenarioRunner {
    fixture: ReplayFixture,
    adapter: LocalWorkspaceAdapter,
    event_log: EventLog,
    projector: EventProjector,
    current_index: usize,
    execution_cache: BTreeMap<String, WorkspaceExecutionOutcome>,
}

impl LocalCrmScenarioRunner {
    pub fn new(seed_dir: impl AsRef<Path>, runtime_dir: impl AsRef<Path>) -> CoreResult<Self> {
        let fixture = load_builtin_replay("crm-followup-flow.json")?;
        let adapter = LocalWorkspaceAdapter::new(runtime_dir.as_ref());
        adapter.reset_workspace(seed_dir)?;
        Ok(Self {
            fixture,
            adapter,
            event_log: EventLog::new(),
            projector: EventProjector::new(),
            current_index: 0,
            execution_cache: BTreeMap::new(),
        })
    }

    pub fn run(mut self) -> CoreResult<LocalCrmScenarioResult> {
        self.run_steps()?;
        Ok(LocalCrmScenarioResult {
            fixture: self.fixture.clone(),
            event_log: self.event_log.clone(),
            state: self.projector.state.clone(),
            runtime_dir: self.adapter.workspace_dir().to_path_buf(),
        })
    }

    pub fn run_with_compensation(mut self) -> CoreResult<LocalCrmScenarioResult> {
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
            let outcome = self.adapter.execute_recovery(recovery, occurred_at)?;
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

        Ok(LocalCrmScenarioResult {
            fixture: self.fixture.clone(),
            event_log: self.event_log.clone(),
            state: self.projector.state.clone(),
            runtime_dir: self.adapter.workspace_dir().to_path_buf(),
        })
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
                    "source": "local-crm-scenario",
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
            "who": "executor.local.workspace",
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
            "verifier_id": "verifier.local.workspace",
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
            let grant = self
                .projector
                .state
                .grants
                .values()
                .filter(|grant| grant.task_id == self.task_id() && grant.node_id == step.node_id)
                .cloned()
                .max_by(|left, right| left.issued_at.cmp(&right.issued_at))
                .ok_or_else(|| CoreError::DispatchDenied {
                    task_id: self.task_id(),
                    node_id: step.node_id.clone(),
                })?;
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
            actor_id: "local_crm.runner".to_owned(),
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
            .unwrap_or_else(|| "structured.local".to_owned())
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

pub fn run_local_crm_scenario(
    seed_dir: impl AsRef<Path>,
    runtime_dir: impl AsRef<Path>,
) -> CoreResult<LocalCrmScenarioResult> {
    LocalCrmScenarioRunner::new(seed_dir, runtime_dir)?.run()
}

pub fn run_local_crm_with_compensation(
    seed_dir: impl AsRef<Path>,
    runtime_dir: impl AsRef<Path>,
) -> CoreResult<LocalCrmScenarioResult> {
    LocalCrmScenarioRunner::new(seed_dir, runtime_dir)?.run_with_compensation()
}

fn base_time() -> Timestamp {
    Timestamp::parse_from_rfc3339("2026-04-10T09:00:00+08:00").expect("valid base time")
}

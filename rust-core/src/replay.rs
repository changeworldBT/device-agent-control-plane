use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use chrono::Duration;
use serde_json::{json, Value};

use crate::contracts::{ReplayFixture, SelectionDecision};
use crate::approval_guard::ensure_approval_for_grant;
use crate::contracts::{CapabilityGrant, EventEnvelope, NodeState, ReplayStep, RiskBand, Timestamp};
use crate::error::{CoreError, CoreResult};
use crate::event_log::EventLog;
use crate::projector::{EventProjector, MaterializedState};
use crate::selector::select_next_node;

#[derive(Debug, Clone)]
pub struct ReplayResult {
    pub fixture: ReplayFixture,
    pub event_log: EventLog,
    pub state: MaterializedState,
    pub selection_history: Vec<SelectionDecision>,
}

#[derive(Debug)]
pub struct ReplayRunner {
    pub fixture: ReplayFixture,
    pub event_log: EventLog,
    pub projector: EventProjector,
    pub selection_history: Vec<SelectionDecision>,
    pub action_specs: BTreeMap<String, serde_json::Value>,
    current_index: usize,
    bootstrapped: bool,
}

impl ReplayRunner {
    pub fn new(fixture: ReplayFixture) -> Self {
        Self {
            fixture,
            event_log: EventLog::new(),
            projector: EventProjector::new(),
            selection_history: Vec::new(),
            action_specs: BTreeMap::new(),
            current_index: 0,
            bootstrapped: false,
        }
    }

    pub fn from_path(path: impl AsRef<Path>) -> CoreResult<Self> {
        Ok(Self::new(load_replay(path)?))
    }

    pub fn run(&mut self, step_limit: Option<u32>) -> CoreResult<ReplayResult> {
        self.bootstrap_if_needed()?;
        let steps = self.fixture.timeline.clone();
        for step in steps.iter() {
            if step_limit.map(|limit| step.step > limit).unwrap_or(false) {
                break;
            }
            self.record_selection_snapshot(step);
            self.run_step(step)?;
        }
        Ok(ReplayResult {
            fixture: self.fixture.clone(),
            event_log: self.event_log.clone(),
            state: self.projector.state.clone(),
            selection_history: self.selection_history.clone(),
        })
    }

    fn bootstrap_if_needed(&mut self) -> CoreResult<()> {
        if self.bootstrapped {
            return Ok(());
        }
        let explicit_task_created = self
            .fixture
            .timeline
            .first()
            .map(|step| step.events.iter().any(|event| event == "task.created"))
            .unwrap_or(false);
        if !explicit_task_created {
            let payload = self.build_task_created_payload();
            let root_node_id = self.root_node_id();
            self.emit_event(0, "task.created", payload, &root_node_id, "bootstrap")?;
        }
        self.bootstrapped = true;
        Ok(())
    }

    fn run_step(&mut self, step: &ReplayStep) -> CoreResult<()> {
        if step.command == "task.create" {
            if !self.projector.state.tasks.contains_key(&self.task_id()) {
                self.emit_event(step.step, "task.created", self.build_task_created_payload(), &step.node_id, "taskcreate")?;
            }
            let explicit_ready = step
                .events
                .iter()
                .any(|token| token.starts_with("node.state_changed(created->ready)"));
            self.ensure_node_ready(step.step, &step.node_id, explicit_ready)?;
        } else {
            let explicit_ready = step
                .events
                .iter()
                .any(|token| token.starts_with("node.state_changed(created->ready)"));
            self.ensure_node_ready(step.step, &step.node_id, explicit_ready)?;
        }

        for (index, token) in step.events.iter().enumerate() {
            self.emit_token(step, token, index + 1)?;
        }
        Ok(())
    }

    fn build_task_created_payload(&self) -> Value {
        let task_type = self
            .fixture
            .task_profile
            .get("task_path")
            .and_then(|value| value.as_array())
            .and_then(|items| items.last())
            .and_then(|value| value.as_str())
            .unwrap_or("Observe");

        let attention_budget = self
            .fixture
            .task_profile
            .get("attention_budget_profile")
            .cloned()
            .unwrap_or_else(|| json!({ "max_interruptions": 0 }));

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
                "risk_class": self.fixture.task_profile.get("default_risk_band").cloned().unwrap_or_else(|| json!("R0")),
                "reversibility": { "mode": "bounded-or-none" },
                "attention_budget": attention_budget,
                "constraints": {
                    "source": "replay-fixture",
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

    fn record_selection_snapshot(&mut self, step: &ReplayStep) {
        if let Some(task) = self.projector.state.tasks.get(&self.task_id()) {
            let mut selection = select_next_node(&self.projector.state, task, self.time_for_step(step.step, 0));
            let rationale = json!({
                "before_step": step.step,
                "expected_node": step.node_id,
                "selection": selection.rationale,
            });
            selection.rationale = rationale;
            self.selection_history.push(selection);
        }
    }

    fn ensure_node_ready(&mut self, step_number: u32, node_id: &str, explicit_transition_present: bool) -> CoreResult<()> {
        let node = match self.projector.state.nodes.get(node_id) {
            Some(node) => node,
            None => return Ok(()),
        };
        if node.state != NodeState::Created || explicit_transition_present {
            return Ok(());
        }
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
        )
    }

    fn emit_token(&mut self, step: &ReplayStep, token: &str, token_index: usize) -> CoreResult<()> {
        match token {
            "task.created" => self.emit_event(step.step, token, self.build_task_created_payload(), &step.node_id, &format!("{token_index}-task")),
            "grant.issued" => self.emit_event(
                step.step,
                token,
                json!({ "grant": self.build_grant(step, token_index)? }),
                &step.node_id,
                &format!("{token_index}-grant"),
            ),
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
            "action.dispatched" => {
                let action_spec = self.build_action_spec(step, token_index);
                self.emit_event(
                    step.step,
                    token,
                    json!({
                        "task_id": self.task_id(),
                        "node_id": step.node_id,
                        "action_id": action_spec.get("action_id").cloned().unwrap_or_else(|| json!("")),
                        "required_capability": action_spec.get("required_capability").cloned().unwrap_or_else(|| json!("")),
                    }),
                    &step.node_id,
                    &format!("{token_index}-dispatch"),
                )
            }
            "receipt.recorded" => {
                let receipt = self.build_receipt(step, token_index)?;
                self.emit_event(
                    step.step,
                    token,
                    json!({ "receipt": receipt }),
                    &step.node_id,
                    &format!("{token_index}-receipt"),
                )
            }
            "verification.recorded" => {
                for (fact_index, fact) in self.build_candidate_facts(step, token_index).into_iter().enumerate() {
                    self.emit_event(
                        step.step,
                        "fact.observed",
                        json!({ "fact": fact }),
                        &step.node_id,
                        &format!("{token_index}-fact-{fact_index}"),
                    )?;
                }
                self.emit_event(
                    step.step,
                    token,
                    json!({ "verification": self.build_verification(step, token_index) }),
                    &step.node_id,
                    &format!("{token_index}-verify"),
                )
            }
            "recovery.recorded" => self.emit_event(
                step.step,
                token,
                json!({ "recovery": self.build_recovery(step, token_index) }),
                &step.node_id,
                &format!("{token_index}-recovery"),
            ),
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

    fn build_approval(&self, step: &ReplayStep, token_index: usize) -> Value {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self.projector.state.nodes.get(&step.node_id).expect("node present");
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

    fn restore_node_ready_after_approval(&mut self, step_number: u32, node_id: &str) -> CoreResult<()> {
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

    fn build_grant(&self, step: &ReplayStep, token_index: usize) -> CoreResult<CapabilityGrant> {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self.projector.state.nodes.get(&step.node_id).expect("node present");
        let task = self.projector.state.tasks.get(&self.task_id()).expect("task present");
        ensure_approval_for_grant(&self.projector.state.approvals, node, task, None)?;
        let grant: CapabilityGrant = serde_json::from_value(json!({
            "grant_id": format!("grant_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "who": "executor.local.structured",
            "what": node.required_capabilities.first().cloned().unwrap_or_else(|| "structured.default".to_owned()),
            "where": { "node_id": step.node_id },
            "when": {
                "not_before": occurred_at.to_rfc3339(),
                "not_after": (occurred_at + Duration::minutes(10)).to_rfc3339(),
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
        .map_err(|error| CoreError::Serialization(error.to_string()))?;
        Ok(grant)
    }

    fn build_action_spec(&mut self, step: &ReplayStep, token_index: usize) -> Value {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self.projector.state.nodes.get(&step.node_id).expect("node present");
        let mut action_spec = json!({
            "action_id": format!("action_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "required_capability": node.required_capabilities.first().cloned().unwrap_or_else(|| "structured.default".to_owned()),
            "occurred_at": occurred_at.to_rfc3339(),
        });
        if matches!(node.risk_class, RiskBand::R3) || node.node_type.starts_with("commit_") {
            action_spec["compensation_policy_ref"] = json!(format!("compensate_{}_{}", self.fixture.replay_id, step.node_id));
            action_spec["side_effect_class"] = json!("irreversible_external_send");
        } else if matches!(node.risk_class, RiskBand::R2) {
            action_spec["compensation_policy_ref"] = json!(format!("rollback_{}_{}", self.fixture.replay_id, step.node_id));
            action_spec["side_effect_class"] = json!("bounded_external_modify");
        }
        self.action_specs.insert(step.node_id.clone(), action_spec.clone());
        action_spec
    }

    fn build_receipt(&mut self, step: &ReplayStep, token_index: usize) -> CoreResult<Value> {
        let occurred_at = self.time_for_step(step.step, token_index);
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
        let action_spec = self
            .action_specs
            .get(&step.node_id)
            .cloned()
            .unwrap_or_else(|| self.build_action_spec(step, token_index));
        let artifacts = vec![
            format!("artifact_{}_{}_primary", step.node_id, step.step),
            format!("artifact_{}_{}_support", step.node_id, step.step),
        ];
        Ok(json!({
            "receipt_id": format!("receipt_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "action_id": action_spec.get("action_id").cloned().unwrap_or_else(|| json!("")),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "grant_id": grant.grant_id,
            "executor_id": "executor.local.structured",
            "status": "succeeded_with_receipt",
            "started_at": occurred_at.to_rfc3339(),
            "ended_at": (occurred_at + Duration::seconds(1)).to_rfc3339(),
            "artifact_refs": artifacts,
            "side_effect_summary": { "mode": "replay" },
            "environment_digest": { "executor": "replay.runner", "mode": "replay" },
            "retry_index": 0,
            "error_summary": {}
        }))
    }

    fn build_candidate_facts(&self, step: &ReplayStep, token_index: usize) -> Vec<Value> {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self
            .fixture
            .nodes
            .iter()
            .find(|node| node.node_id == step.node_id)
            .expect("node present");
        match node.node_type.as_str() {
            "synthesize_facts" => ["a", "b"]
                .into_iter()
                .map(|variant| {
                    json!({
                        "fact_id": format!("fact_{}_{}", step.node_id, variant),
                        "fact_type": "derived",
                        "statement": format!("Candidate vendor claim {variant} extracted for {}", step.node_id),
                        "provenance": { "kind": "replay-extraction", "step": step.step },
                        "observed_at": occurred_at.to_rfc3339(),
                        "valid_until": (occurred_at + Duration::days(1)).to_rfc3339(),
                        "attestation_level": "candidate_extraction",
                        "confidence": 0.6,
                        "scope": { "node_id": step.node_id },
                        "evidence_refs": [format!("artifact_{}_{}_support", step.node_id, step.step)],
                        "status": "candidate",
                        "version": 1,
                        "conflict_set": ["conflict.vendor.claims"],
                    })
                })
                .collect(),
            "observe_sensitive_record" => vec![json!({
                "fact_id": format!("fact_{}_baseline", step.node_id),
                "fact_type": "observed",
                "statement": format!("Baseline CRM snapshot captured for {}", step.node_id),
                "provenance": { "kind": "replay-observation", "step": step.step },
                "observed_at": occurred_at.to_rfc3339(),
                "valid_until": (occurred_at + Duration::hours(2)).to_rfc3339(),
                "attestation_level": "receipt_pending_verification",
                "confidence": 0.8,
                "scope": { "node_id": step.node_id },
                "evidence_refs": [format!("artifact_{}_{}_primary", step.node_id, step.step)],
                "status": "candidate",
                "version": 1,
                "conflict_set": [],
            })],
            _ => Vec::new(),
        }
    }

    fn build_verification(&self, step: &ReplayStep, token_index: usize) -> Value {
        let occurred_at = self.time_for_step(step.step, token_index);
        let node = self
            .fixture
            .nodes
            .iter()
            .find(|node| node.node_id == step.node_id)
            .expect("node present");
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
        let target_state = if self.has_explicit_terminal_transition(step) {
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
        json!({
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
            "verifier_id": "verifier.replay.core",
            "recommended_recovery_action": self.fixture.terminal_expectation.get("recovery_mode").cloned()
        })
    }

    fn build_recovery(&self, step: &ReplayStep, token_index: usize) -> Value {
        let occurred_at = self.time_for_step(step.step, token_index);
        let action_spec = self.action_specs.get(&step.node_id).cloned().unwrap_or_default();
        let action = if action_spec
            .get("side_effect_class")
            .and_then(|value| value.as_str())
            == Some("irreversible_external_send")
        {
            "compensate"
        } else {
            "rollback"
        };
        json!({
            "recovery_id": format!("recovery_{}_{}_{}", self.fixture.replay_id, step.node_id, step.step),
            "task_id": self.task_id(),
            "node_id": step.node_id,
            "action": action,
            "recorded_at": occurred_at.to_rfc3339(),
            "policy_ref": action_spec.get("compensation_policy_ref").cloned().unwrap_or_else(|| json!(format!("policy_{}_{}", self.fixture.replay_id, step.node_id))),
            "status": "armed"
        })
    }

    fn has_explicit_terminal_transition(&self, step: &ReplayStep) -> bool {
        step.events
            .iter()
            .any(|token| token.starts_with("node.state_changed(") && token.contains("->completed"))
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
            actor_id: "replay.runner".to_owned(),
            occurred_at: self.time_for_step(step_number, self.current_index + 1),
            payload,
            task_id: self.task_id(),
            node_id: node_id.to_owned(),
            trace_ref: self.fixture.replay_id.clone(),
            causation_ref: self.event_log.as_slice().last().map(|event| event.event_id.clone()),
            correlation_ref: Some(self.fixture.replay_id.clone()),
        };
        if self.event_log.append(event.clone())? {
            self.projector.apply(&event)?;
            self.current_index += 1;
        }
        Ok(())
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

fn base_time() -> Timestamp {
    Timestamp::parse_from_rfc3339("2026-04-10T09:00:00+08:00").expect("valid base time")
}

pub fn load_replay(path: impl AsRef<Path>) -> CoreResult<ReplayFixture> {
    let raw = std::fs::read_to_string(path.as_ref()).map_err(|error| CoreError::Serialization(error.to_string()))?;
    let mut fixture: ReplayFixture =
        serde_json::from_str(&raw).map_err(|error| CoreError::Serialization(error.to_string()))?;
    fixture.timeline.sort_by_key(|step| step.step);
    Ok(fixture)
}

pub fn load_builtin_replay(file_name: &str) -> CoreResult<ReplayFixture> {
    let base = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("schemas")
        .join("examples")
        .join("flows")
        .join(file_name);
    load_replay(base)
}

use std::collections::{BTreeMap, BTreeSet};

use serde::Deserialize;
use serde_json::Value;

use crate::contracts::{
    ApprovalRecord, CapabilityGrant, EventEnvelope, ExecutionReceipt, FactRecord, NodeState,
    RecoveryRecord, Task, TaskNode, Timestamp, VerificationResult,
};
use crate::error::{CoreError, CoreResult};
use crate::fact_semantics::materialize_fact_status;
use crate::grant_guard::ensure_dispatch_allowed;
use crate::task_guard::ensure_transition_allowed;

#[derive(Debug, Clone, Default)]
pub struct MaterializedState {
    pub tasks: BTreeMap<String, Task>,
    pub task_states: BTreeMap<String, NodeState>,
    pub nodes: BTreeMap<String, TaskNode>,
    pub facts: BTreeMap<String, FactRecord>,
    pub grants: BTreeMap<String, CapabilityGrant>,
    pub approvals: BTreeMap<String, ApprovalRecord>,
    pub receipts: BTreeMap<String, ExecutionReceipt>,
    pub verifications: BTreeMap<String, VerificationResult>,
    pub recoveries: BTreeMap<String, RecoveryRecord>,
    pub artifacts: BTreeSet<String>,
    pub node_receipts: BTreeMap<String, Vec<String>>,
    pub node_verifications: BTreeMap<String, Vec<String>>,
    pub last_event_at: Option<Timestamp>,
}

impl MaterializedState {
    pub fn has_successful_verification(&self, node_id: &str) -> bool {
        self.node_verifications
            .get(node_id)
            .into_iter()
            .flatten()
            .rev()
            .filter_map(|verification_id| self.verifications.get(verification_id))
            .any(|verification| verification.result == "verified_success")
    }
}

#[derive(Debug, Default, Clone)]
pub struct EventProjector {
    pub state: MaterializedState,
}

impl EventProjector {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn rebuild(
        &mut self,
        events: &[EventEnvelope],
        as_of: Option<Timestamp>,
    ) -> CoreResult<MaterializedState> {
        self.state = MaterializedState::default();
        for event in events {
            self.apply(event)?;
        }
        if let Some(at_time) = as_of {
            self.refresh_fact_statuses(at_time);
        }
        Ok(self.state.clone())
    }

    pub fn apply(&mut self, event: &EventEnvelope) -> CoreResult<&MaterializedState> {
        match event.event_type.as_str() {
            "task.created" => {
                let payload: TaskCreatedPayload = from_payload(event.payload.clone())?;
                self.apply_task_created(payload);
            }
            "node.state_changed" => {
                let payload: NodeStateChangedPayload = from_payload(event.payload.clone())?;
                self.apply_node_state_change(payload)?;
            }
            "grant.issued" => {
                let payload: GrantIssuedPayload = from_payload(event.payload.clone())?;
                self.apply_grant_issued(payload);
            }
            "approval.recorded" => {
                let payload: ApprovalRecordedPayload = from_payload(event.payload.clone())?;
                self.state
                    .approvals
                    .insert(payload.approval.approval_id.clone(), payload.approval);
            }
            "action.dispatched" => {
                let payload: ActionDispatchedPayload = from_payload(event.payload.clone())?;
                self.apply_action_dispatched(payload, event.occurred_at)?;
            }
            "receipt.recorded" => {
                let payload: ReceiptRecordedPayload = from_payload(event.payload.clone())?;
                self.apply_receipt_recorded(payload, event.occurred_at)?;
            }
            "verification.recorded" => {
                let payload: VerificationRecordedPayload = from_payload(event.payload.clone())?;
                self.apply_verification_recorded(payload, event.occurred_at)?;
            }
            "recovery.recorded" => {
                let payload: RecoveryRecordedPayload = from_payload(event.payload.clone())?;
                self.state
                    .recoveries
                    .insert(payload.recovery.recovery_id.clone(), payload.recovery);
            }
            "fact.observed" => {
                let payload: FactObservedPayload = from_payload(event.payload.clone())?;
                self.apply_fact_observed(payload);
            }
            other => return Err(CoreError::UnsupportedEventType(other.to_owned())),
        }

        self.state.last_event_at = Some(event.occurred_at);
        self.refresh_fact_statuses(event.occurred_at);
        self.recompute_task_states();
        Ok(&self.state)
    }

    fn apply_task_created(&mut self, payload: TaskCreatedPayload) {
        let task_id = payload.task.task_id.clone();
        self.state.tasks.insert(task_id.clone(), payload.task);
        self.state.task_states.insert(task_id, NodeState::Created);
        for node in payload.nodes {
            self.state.nodes.insert(node.node_id.clone(), node);
        }
    }

    fn apply_node_state_change(&mut self, payload: NodeStateChangedPayload) -> CoreResult<()> {
        let has_verification = self.state.has_successful_verification(&payload.node_id);
        let node = self
            .state
            .nodes
            .get_mut(&payload.node_id)
            .expect("node must exist before transition");
        ensure_transition_allowed(&node.state, &payload.to_state, has_verification)?;
        node.state = payload.to_state;
        node.version += 1;
        node.updated_at = payload.changed_at;
        Ok(())
    }

    fn apply_grant_issued(&mut self, payload: GrantIssuedPayload) {
        let grant = payload.grant;
        let node_id = grant.node_id.clone();
        let grant_id = grant.grant_id.clone();
        self.state.grants.insert(grant_id.clone(), grant);
        if let Some(node) = self.state.nodes.get_mut(&node_id) {
            push_missing(&mut node.grant_refs, grant_id);
        }
    }

    fn apply_action_dispatched(
        &mut self,
        payload: ActionDispatchedPayload,
        occurred_at: Timestamp,
    ) -> CoreResult<()> {
        let _grant = ensure_dispatch_allowed(
            &self.state.grants,
            &payload.task_id,
            &payload.node_id,
            occurred_at,
        )?;
        let node = self
            .state
            .nodes
            .get_mut(&payload.node_id)
            .expect("node must exist before dispatch");
        ensure_transition_allowed(&node.state, &NodeState::Running, false)?;
        node.state = NodeState::Running;
        node.version += 1;
        node.updated_at = occurred_at;
        Ok(())
    }

    fn apply_receipt_recorded(
        &mut self,
        payload: ReceiptRecordedPayload,
        occurred_at: Timestamp,
    ) -> CoreResult<()> {
        let receipt = payload.receipt;
        let node_id = receipt.node_id.clone();
        let receipt_id = receipt.receipt_id.clone();
        let artifact_refs = receipt.artifact_refs.clone();
        self.state.receipts.insert(receipt_id.clone(), receipt);
        self.state
            .node_receipts
            .entry(node_id.clone())
            .or_default()
            .push(receipt_id);
        for artifact_ref in artifact_refs.iter() {
            self.state.artifacts.insert(artifact_ref.clone());
        }
        let node = self
            .state
            .nodes
            .get_mut(&node_id)
            .expect("node must exist before receipt");
        ensure_transition_allowed(&node.state, &NodeState::Verifying, false)?;
        node.state = NodeState::Verifying;
        node.version += 1;
        node.updated_at = occurred_at;
        for artifact_ref in artifact_refs {
            push_missing(&mut node.artifact_refs, artifact_ref);
        }
        Ok(())
    }

    fn apply_verification_recorded(
        &mut self,
        payload: VerificationRecordedPayload,
        occurred_at: Timestamp,
    ) -> CoreResult<()> {
        let verification = payload.verification;
        let verification_id = verification.verification_id.clone();
        let node_id = verification.node_id.clone();
        let transition = verification.state_transition.clone();
        let verified_at = verification.verified_at;
        self.state
            .verifications
            .insert(verification_id.clone(), verification);
        self.state
            .node_verifications
            .entry(node_id.clone())
            .or_default()
            .push(verification_id);

        for fact_id in transition.fact_promotions {
            if let Some(fact) = self.state.facts.get_mut(&fact_id) {
                fact.status = crate::contracts::FactStatus::Verified;
                fact.verified_at = Some(verified_at);
                fact.version += 1;
            }
        }

        if let Some(target_state) = transition.to {
            let node = self
                .state
                .nodes
                .get_mut(&node_id)
                .expect("node must exist before verification");
            ensure_transition_allowed(&node.state, &target_state, true)?;
            node.state = target_state;
            node.version += 1;
            node.updated_at = occurred_at;
        }

        Ok(())
    }

    fn apply_fact_observed(&mut self, payload: FactObservedPayload) {
        match self.state.facts.get(&payload.fact.fact_id) {
            Some(existing) if existing.version > payload.fact.version => {}
            _ => {
                self.state
                    .facts
                    .insert(payload.fact.fact_id.clone(), payload.fact);
            }
        }
    }

    fn refresh_fact_statuses(&mut self, as_of: Timestamp) {
        for fact in self.state.facts.values_mut() {
            fact.status = materialize_fact_status(fact, as_of);
        }
    }

    fn recompute_task_states(&mut self) {
        for task_id in self.state.tasks.keys() {
            let node_states: Vec<NodeState> = self
                .state
                .nodes
                .values()
                .filter(|node| &node.task_id == task_id)
                .map(|node| node.state.clone())
                .collect();

            let task_state = if node_states.is_empty() {
                NodeState::Created
            } else if node_states
                .iter()
                .all(|state| *state == NodeState::Completed)
            {
                NodeState::Completed
            } else if node_states.iter().any(|state| *state == NodeState::Failed) {
                NodeState::Failed
            } else if node_states
                .iter()
                .any(|state| matches!(state, NodeState::Running | NodeState::Verifying))
            {
                NodeState::Running
            } else if node_states
                .iter()
                .any(|state| *state == NodeState::AwaitingApproval)
            {
                NodeState::AwaitingApproval
            } else if node_states.iter().any(|state| *state == NodeState::Blocked) {
                NodeState::Blocked
            } else if node_states.iter().any(|state| *state == NodeState::Ready) {
                NodeState::Ready
            } else {
                NodeState::Created
            };

            self.state.task_states.insert(task_id.clone(), task_state);
        }
    }
}

fn push_missing(values: &mut Vec<String>, candidate: String) {
    if !values.iter().any(|existing| existing == &candidate) {
        values.push(candidate);
    }
}

fn from_payload<T>(payload: Value) -> CoreResult<T>
where
    T: for<'de> Deserialize<'de>,
{
    serde_json::from_value(payload).map_err(|error| CoreError::Serialization(error.to_string()))
}

#[derive(Debug, Deserialize)]
struct TaskCreatedPayload {
    task: Task,
    nodes: Vec<TaskNode>,
}

#[derive(Debug, Deserialize)]
struct NodeStateChangedPayload {
    #[allow(dead_code)]
    task_id: String,
    node_id: String,
    #[allow(dead_code)]
    from_state: NodeState,
    to_state: NodeState,
    changed_at: Timestamp,
}

#[derive(Debug, Deserialize)]
struct GrantIssuedPayload {
    grant: CapabilityGrant,
}

#[derive(Debug, Deserialize)]
struct ApprovalRecordedPayload {
    approval: ApprovalRecord,
}

#[derive(Debug, Deserialize)]
struct ActionDispatchedPayload {
    task_id: String,
    node_id: String,
    #[allow(dead_code)]
    action_id: String,
    #[allow(dead_code)]
    required_capability: String,
}

#[derive(Debug, Deserialize)]
struct ReceiptRecordedPayload {
    receipt: ExecutionReceipt,
}

#[derive(Debug, Deserialize)]
struct VerificationRecordedPayload {
    verification: VerificationResult,
}

#[derive(Debug, Deserialize)]
struct RecoveryRecordedPayload {
    recovery: RecoveryRecord,
}

#[derive(Debug, Deserialize)]
struct FactObservedPayload {
    fact: FactRecord,
}

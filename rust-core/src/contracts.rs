use chrono::{DateTime, FixedOffset};
use serde::{Deserialize, Serialize};
use serde_json::Value;

pub type Timestamp = DateTime<FixedOffset>;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum RiskBand {
    #[serde(rename = "R0")]
    R0,
    #[serde(rename = "R1")]
    R1,
    #[serde(rename = "R2")]
    R2,
    #[serde(rename = "R3")]
    R3,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[serde(rename_all = "snake_case")]
pub enum NodeState {
    Created,
    Ready,
    Blocked,
    AwaitingApproval,
    Running,
    Verifying,
    Completed,
    Failed,
    RolledBack,
    PausedForHuman,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[serde(rename_all = "snake_case")]
pub enum FactStatus {
    Candidate,
    Verified,
    Stale,
    Revoked,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum FactType {
    Observed,
    Inferred,
    Policy,
    Derived,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RecoveryStatus {
    Armed,
    Executed,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AttentionBudget {
    #[serde(default)]
    pub max_interruptions: u32,
    #[serde(default)]
    pub must_confirm_before_commit: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Task {
    pub task_id: String,
    pub objective: String,
    pub desired_delta: Value,
    pub evidence_of_done: Value,
    pub task_type: String,
    pub risk_class: RiskBand,
    pub reversibility: Value,
    #[serde(default)]
    pub deadline: Option<String>,
    #[serde(default)]
    pub recurrence: Option<String>,
    #[serde(default)]
    pub attention_budget: AttentionBudget,
    pub constraints: Value,
    pub root_node_id: String,
    pub principal_ref: String,
    pub resource_owner_ref: String,
    pub approver_ref: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskNode {
    pub node_id: String,
    pub task_id: String,
    pub node_type: String,
    pub objective: String,
    pub desired_delta: Value,
    pub evidence_of_done: Value,
    pub risk_class: RiskBand,
    pub state: NodeState,
    #[serde(default)]
    pub dependencies: Vec<String>,
    #[serde(default)]
    pub required_capabilities: Vec<String>,
    pub principal_ref: String,
    pub resource_owner_ref: String,
    #[serde(default)]
    pub grant_refs: Vec<String>,
    #[serde(default)]
    pub artifact_refs: Vec<String>,
    pub version: u64,
    pub created_at: Timestamp,
    pub updated_at: Timestamp,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FactRecord {
    pub fact_id: String,
    pub fact_type: FactType,
    pub statement: String,
    pub provenance: Value,
    pub observed_at: Timestamp,
    #[serde(default)]
    pub verified_at: Option<Timestamp>,
    #[serde(default)]
    pub valid_until: Option<Timestamp>,
    #[serde(default)]
    pub ttl: Option<i64>,
    pub attestation_level: String,
    pub confidence: f64,
    pub scope: Value,
    #[serde(default)]
    pub evidence_refs: Vec<String>,
    pub status: FactStatus,
    pub version: u64,
    #[serde(default)]
    pub supersedes: Option<String>,
    #[serde(default)]
    pub conflict_set: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilityGrant {
    pub grant_id: String,
    pub task_id: String,
    pub node_id: String,
    pub who: String,
    pub what: String,
    #[serde(rename = "where")]
    pub scope: Value,
    #[serde(rename = "when")]
    pub window: Value,
    pub budget: Value,
    #[serde(rename = "why")]
    pub reason: String,
    pub approval_ref: String,
    pub postcondition_ref: String,
    pub principal_ref: String,
    pub resource_owner_ref: String,
    pub approver_ref: String,
    pub status: String,
    pub issued_at: Timestamp,
    pub expires_at: Timestamp,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApprovalRecord {
    pub approval_id: String,
    pub task_id: String,
    pub node_id: String,
    pub approver_id: String,
    pub approved_at: Timestamp,
    pub status: String,
    pub risk_class: RiskBand,
    pub approval_kind: String,
    #[serde(default)]
    pub selection_ref: Option<String>,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionReceipt {
    pub receipt_id: String,
    pub action_id: String,
    pub task_id: String,
    pub node_id: String,
    pub grant_id: String,
    pub executor_id: String,
    pub status: String,
    pub started_at: Timestamp,
    pub ended_at: Timestamp,
    #[serde(default)]
    pub artifact_refs: Vec<String>,
    pub side_effect_summary: Value,
    pub environment_digest: Value,
    pub retry_index: u32,
    pub error_summary: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationTransition {
    #[serde(default)]
    pub to: Option<NodeState>,
    #[serde(default)]
    pub fact_promotions: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerificationResult {
    pub verification_id: String,
    pub task_id: String,
    pub node_id: String,
    #[serde(default)]
    pub receipt_refs: Vec<String>,
    pub result: String,
    #[serde(default)]
    pub supporting_evidence: Vec<String>,
    #[serde(default)]
    pub remaining_uncertainties: Vec<String>,
    pub state_transition: VerificationTransition,
    pub verified_at: Timestamp,
    pub verifier_id: String,
    #[serde(default)]
    pub recommended_recovery_action: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecoveryRecord {
    pub recovery_id: String,
    pub task_id: String,
    pub node_id: String,
    pub action: String,
    pub recorded_at: Timestamp,
    pub policy_ref: String,
    pub status: RecoveryStatus,
    #[serde(default)]
    pub artifact_refs: Vec<String>,
    #[serde(default)]
    pub side_effect_summary: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventEnvelope {
    pub event_id: String,
    pub event_type: String,
    pub actor_id: String,
    pub occurred_at: Timestamp,
    pub payload: Value,
    pub task_id: String,
    pub node_id: String,
    pub trace_ref: String,
    #[serde(default)]
    pub causation_ref: Option<String>,
    #[serde(default)]
    pub correlation_ref: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelectionDecision {
    pub node_id: Option<String>,
    pub path_kind: String,
    #[serde(default)]
    pub score: Option<f64>,
    pub rationale: Value,
    pub max_interruptions: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplayStep {
    pub step: u32,
    pub node_id: String,
    pub command: String,
    pub events: Vec<String>,
    #[serde(default)]
    pub notes: Option<String>,
    #[serde(default)]
    pub invariant_refs: Vec<String>,
    #[serde(default)]
    pub policy_refs: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplayNode {
    pub node_id: String,
    pub node_type: String,
    pub purpose: String,
    pub risk_band: RiskBand,
    pub expected_terminal: NodeState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReplayFixture {
    pub replay_id: String,
    pub title: String,
    pub goal: String,
    pub task_profile: Value,
    pub nodes: Vec<ReplayNode>,
    pub timeline: Vec<ReplayStep>,
    #[serde(default)]
    pub invariants_exercised: Vec<String>,
    #[serde(default)]
    pub policy_surfaces: Vec<String>,
    pub terminal_expectation: Value,
}

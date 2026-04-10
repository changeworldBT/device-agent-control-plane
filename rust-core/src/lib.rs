pub mod approval_guard;
pub mod cli_banner;
pub mod contracts;
pub mod error;
pub mod event_log;
pub mod fact_semantics;
pub mod grant_guard;
pub mod http_crm;
pub mod local_crm;
pub mod mock_http_crm;
pub mod model_config;
pub mod projector;
pub mod replay;
pub mod selector;
pub mod task_guard;
pub mod workspace;

pub use approval_guard::{approval_required, ensure_approval_for_grant, has_active_approval};
pub use cli_banner::render_welcome;
pub use contracts::{
    ApprovalRecord, CapabilityGrant, EventEnvelope, ExecutionReceipt, FactRecord, FactStatus,
    FactType, NodeState, RecoveryRecord, RecoveryStatus, ReplayFixture, ReplayNode, ReplayStep,
    RiskBand, SelectionDecision, Task, TaskNode, VerificationResult,
};
pub use error::{CoreError, CoreResult};
pub use event_log::EventLog;
pub use fact_semantics::{effective_valid_until, is_fact_expired, materialize_fact_status};
pub use grant_guard::{ensure_dispatch_allowed, find_active_grant, is_grant_active};
pub use http_crm::{
    run_http_crm_scenario, run_http_crm_with_compensation, HttpCrmScenarioResult,
    HttpCrmScenarioRunner,
};
pub use local_crm::{
    run_local_crm_scenario, run_local_crm_with_compensation, LocalCrmScenarioResult,
    LocalCrmScenarioRunner,
};
pub use mock_http_crm::{MockHttpCrmServer, MockHttpCrmSnapshot};
pub use model_config::{
    load_model_config_json, AgentMember, AgentMode, AgentTeamConfig, ModelProvider,
    ModelProviderConfig, ModelRoute, ModelRunMode,
};
pub use projector::{EventProjector, MaterializedState};
pub use replay::{load_builtin_replay, load_replay, ReplayResult, ReplayRunner};
pub use selector::{composite_risk_score, select_next_node};
pub use task_guard::{ensure_transition_allowed, is_terminal};
pub use workspace::{
    LocalWorkspaceAdapter, WorkspaceAdapter, WorkspaceExecutionOutcome, WorkspaceRecoveryOutcome,
};

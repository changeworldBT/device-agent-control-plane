use std::collections::BTreeMap;

use chrono::{DateTime, FixedOffset};
use device_agent_core::{
    approval_required, ensure_approval_for_grant, ensure_dispatch_allowed, materialize_fact_status,
    load_builtin_replay, select_next_node, CapabilityGrant, CoreError, EventEnvelope, EventLog, EventProjector, FactRecord,
    ReplayRunner,
    MaterializedState, NodeState, RiskBand, Task, TaskNode,
};
use serde_json::json;

fn ts(raw: &str) -> DateTime<FixedOffset> {
    DateTime::parse_from_rfc3339(raw).expect("valid timestamp")
}

fn attention_budget(max_interruptions: u32, must_confirm_before_commit: bool) -> device_agent_core::contracts::AttentionBudget {
    device_agent_core::contracts::AttentionBudget {
        max_interruptions,
        must_confirm_before_commit,
    }
}

fn sample_task(task_id: &str) -> Task {
    Task {
        task_id: task_id.to_owned(),
        objective: "sample objective".to_owned(),
        desired_delta: json!({"goal": "done"}),
        evidence_of_done: json!({"proof": ["artifact::done"]}),
        task_type: "Prepare".to_owned(),
        risk_class: RiskBand::R1,
        reversibility: json!({"mode": "bounded"}),
        deadline: None,
        recurrence: None,
        attention_budget: attention_budget(0, false),
        constraints: json!({"source": "test"}),
        root_node_id: "node_alpha".to_owned(),
        principal_ref: "principal.user.primary".to_owned(),
        resource_owner_ref: "owner.workspace.primary".to_owned(),
        approver_ref: "principal.user.primary".to_owned(),
    }
}

fn sample_node(node_id: &str, node_type: &str, risk_class: RiskBand, state: NodeState) -> TaskNode {
    TaskNode {
        node_id: node_id.to_owned(),
        task_id: "task_alpha".to_owned(),
        node_type: node_type.to_owned(),
        objective: format!("objective for {node_id}"),
        desired_delta: json!({"node": node_id}),
        evidence_of_done: json!({"terminal": "completed"}),
        risk_class,
        state,
        dependencies: Vec::new(),
        required_capabilities: vec!["structured.test".to_owned()],
        principal_ref: "principal.user.primary".to_owned(),
        resource_owner_ref: "owner.workspace.primary".to_owned(),
        grant_refs: Vec::new(),
        artifact_refs: Vec::new(),
        version: 1,
        created_at: ts("2026-04-10T09:00:00+08:00"),
        updated_at: ts("2026-04-10T09:00:00+08:00"),
    }
}

fn sample_grant() -> CapabilityGrant {
    CapabilityGrant {
        grant_id: "grant_alpha".to_owned(),
        task_id: "task_alpha".to_owned(),
        node_id: "node_alpha".to_owned(),
        who: "executor.local.structured".to_owned(),
        what: "structured.test".to_owned(),
        scope: json!({"node_id": "node_alpha"}),
        window: json!({"not_before": "2026-04-10T09:00:00+08:00", "not_after": "2026-04-10T09:10:00+08:00"}),
        budget: json!({"max_retries": 1}),
        reason: "test".to_owned(),
        approval_ref: "approval_alpha".to_owned(),
        postcondition_ref: "postcondition_alpha".to_owned(),
        principal_ref: "principal.user.primary".to_owned(),
        resource_owner_ref: "owner.workspace.primary".to_owned(),
        approver_ref: "principal.user.primary".to_owned(),
        status: "active".to_owned(),
        issued_at: ts("2026-04-10T09:00:00+08:00"),
        expires_at: ts("2026-04-10T09:10:00+08:00"),
    }
}

fn sample_fact(valid_until: &str) -> FactRecord {
    FactRecord {
        fact_id: "fact_alpha".to_owned(),
        fact_type: device_agent_core::contracts::FactType::Observed,
        statement: "baseline captured".to_owned(),
        provenance: json!({"kind": "test"}),
        observed_at: ts("2026-04-10T09:00:00+08:00"),
        verified_at: None,
        valid_until: Some(ts(valid_until)),
        ttl: None,
        attestation_level: "candidate".to_owned(),
        confidence: 0.9,
        scope: json!({"node_id": "node_alpha"}),
        evidence_refs: vec!["artifact::baseline".to_owned()],
        status: device_agent_core::contracts::FactStatus::Verified,
        version: 1,
        supersedes: None,
        conflict_set: Vec::new(),
    }
}

fn sample_event(event_type: &str, payload: serde_json::Value) -> EventEnvelope {
    EventEnvelope {
        event_id: format!("evt_{event_type}"),
        event_type: event_type.to_owned(),
        actor_id: "test.runner".to_owned(),
        occurred_at: ts("2026-04-10T09:00:00+08:00"),
        payload,
        task_id: "task_alpha".to_owned(),
        node_id: "node_alpha".to_owned(),
        trace_ref: "trace_alpha".to_owned(),
        causation_ref: None,
        correlation_ref: None,
    }
}

#[test]
fn event_log_rejects_duplicate_event_ids() {
    let mut log = EventLog::new();
    let event = sample_event("task.created", json!({"task": {}, "nodes": []}));
    assert!(log.append(event.clone()).is_ok());
    let duplicate = log.append(event).expect_err("duplicate should fail");
    assert!(matches!(duplicate, CoreError::DuplicateEventId(_)));
}

#[test]
fn fact_status_becomes_stale_after_expiry() {
    let fact = sample_fact("2026-04-10T10:00:00+08:00");
    let status = materialize_fact_status(&fact, ts("2026-04-10T10:05:00+08:00"));
    assert_eq!(status, device_agent_core::contracts::FactStatus::Stale);
}

#[test]
fn task_guard_requires_verification_for_completed_transition() {
    let result = device_agent_core::task_guard::ensure_transition_allowed(&NodeState::Ready, &NodeState::Completed, false);
    assert!(matches!(result, Err(CoreError::VerificationRequired { .. })));
}

#[test]
fn grant_guard_accepts_active_grant() {
    let grant = sample_grant();
    let mut grants = BTreeMap::new();
    grants.insert(grant.grant_id.clone(), grant);
    let active = ensure_dispatch_allowed(&grants, "task_alpha", "node_alpha", ts("2026-04-10T09:05:00+08:00"));
    assert!(active.is_ok());
}

#[test]
fn approval_guard_blocks_commit_without_approval() {
    let mut task = sample_task("task_alpha");
    task.attention_budget.must_confirm_before_commit = true;
    let node = sample_node("node_alpha", "commit_external_send", RiskBand::R3, NodeState::Ready);
    assert!(approval_required(&node, &task, Some(7.0)));
    let approvals = BTreeMap::new();
    let result = ensure_approval_for_grant(&approvals, &node, &task, Some(7.0));
    assert!(matches!(result, Err(CoreError::ApprovalDenied { .. })));
}

#[test]
fn selector_prefers_ready_low_risk_node_within_attention_budget() {
    let mut state = MaterializedState::default();
    let task = sample_task("task_alpha");
    state.tasks.insert(task.task_id.clone(), task.clone());
    state.nodes.insert(
        "node_alpha".to_owned(),
        sample_node("node_alpha", "observe_sources", RiskBand::R0, NodeState::Ready),
    );
    state.nodes.insert(
        "node_beta".to_owned(),
        sample_node("node_beta", "operate_crm_update", RiskBand::R2, NodeState::Ready),
    );

    let selection = select_next_node(&state, &task, ts("2026-04-10T09:00:00+08:00"));
    assert_eq!(selection.node_id.as_deref(), Some("node_alpha"));
    assert_eq!(selection.path_kind, "structured");
}

#[test]
fn projector_materializes_verified_fact_and_completed_task() {
    let mut projector = EventProjector::new();
    let task_event = sample_event(
        "task.created",
        json!({
            "task": {
                "task_id": "task_alpha",
                "objective": "sample objective",
                "desired_delta": {"goal": "done"},
                "evidence_of_done": {"proof": ["artifact::done"]},
                "task_type": "Observe",
                "risk_class": "R1",
                "reversibility": {"mode": "bounded"},
                "attention_budget": {"max_interruptions": 0, "must_confirm_before_commit": false},
                "constraints": {"source": "test"},
                "root_node_id": "node_alpha",
                "principal_ref": "principal.user.primary",
                "resource_owner_ref": "owner.workspace.primary",
                "approver_ref": "principal.user.primary"
            },
            "nodes": [{
                "node_id": "node_alpha",
                "task_id": "task_alpha",
                "node_type": "observe_sensitive_record",
                "objective": "capture baseline",
                "desired_delta": {"node": "node_alpha"},
                "evidence_of_done": {"terminal": "completed"},
                "risk_class": "R1",
                "state": "created",
                "dependencies": [],
                "required_capabilities": ["structured.test"],
                "principal_ref": "principal.user.primary",
                "resource_owner_ref": "owner.workspace.primary",
                "grant_refs": [],
                "artifact_refs": [],
                "version": 1,
                "created_at": "2026-04-10T09:00:00+08:00",
                "updated_at": "2026-04-10T09:00:00+08:00"
            }]
        }),
    );
    projector.apply(&task_event).expect("task created");

    projector
        .apply(&sample_event(
            "node.state_changed",
            json!({
                "task_id": "task_alpha",
                "node_id": "node_alpha",
                "from_state": "created",
                "to_state": "ready",
                "changed_at": "2026-04-10T09:01:00+08:00"
            }),
        ))
        .expect("node ready");

    projector
        .apply(&sample_event(
            "grant.issued",
            json!({
                "grant": {
                    "grant_id": "grant_alpha",
                    "task_id": "task_alpha",
                    "node_id": "node_alpha",
                    "who": "executor.local.structured",
                    "what": "structured.test",
                    "where": {"node_id": "node_alpha"},
                    "when": {"not_before": "2026-04-10T09:00:00+08:00", "not_after": "2026-04-10T09:10:00+08:00"},
                    "budget": {"max_retries": 1},
                    "why": "test",
                    "approval_ref": "approval_alpha",
                    "postcondition_ref": "postcondition_alpha",
                    "principal_ref": "principal.user.primary",
                    "resource_owner_ref": "owner.workspace.primary",
                    "approver_ref": "principal.user.primary",
                    "status": "active",
                    "issued_at": "2026-04-10T09:00:00+08:00",
                    "expires_at": "2026-04-10T09:10:00+08:00"
                }
            }),
        ))
        .expect("grant issued");

    projector
        .apply(&sample_event(
            "action.dispatched",
            json!({
                "task_id": "task_alpha",
                "node_id": "node_alpha",
                "action_id": "action_alpha",
                "required_capability": "structured.test"
            }),
        ))
        .expect("dispatch");

    projector
        .apply(&sample_event(
            "receipt.recorded",
            json!({
                "receipt": {
                    "receipt_id": "receipt_alpha",
                    "action_id": "action_alpha",
                    "task_id": "task_alpha",
                    "node_id": "node_alpha",
                    "grant_id": "grant_alpha",
                    "executor_id": "executor.local.structured",
                    "status": "succeeded_with_receipt",
                    "started_at": "2026-04-10T09:02:00+08:00",
                    "ended_at": "2026-04-10T09:02:30+08:00",
                    "artifact_refs": ["artifact::baseline"],
                    "side_effect_summary": {"mode": "read"},
                    "environment_digest": {"executor": "test"},
                    "retry_index": 0,
                    "error_summary": {}
                }
            }),
        ))
        .expect("receipt");

    projector
        .apply(&sample_event(
            "fact.observed",
            json!({
                "fact": {
                    "fact_id": "fact_alpha",
                    "fact_type": "observed",
                    "statement": "baseline captured",
                    "provenance": {"kind": "test"},
                    "observed_at": "2026-04-10T09:02:00+08:00",
                    "valid_until": "2026-04-10T11:00:00+08:00",
                    "attestation_level": "candidate",
                    "confidence": 0.9,
                    "scope": {"node_id": "node_alpha"},
                    "evidence_refs": ["artifact::baseline"],
                    "status": "candidate",
                    "version": 1,
                    "conflict_set": []
                }
            }),
        ))
        .expect("fact observed");

    projector
        .apply(&sample_event(
            "verification.recorded",
            json!({
                "verification": {
                    "verification_id": "verification_alpha",
                    "task_id": "task_alpha",
                    "node_id": "node_alpha",
                    "receipt_refs": ["receipt_alpha"],
                    "result": "verified_success",
                    "supporting_evidence": ["artifact::baseline"],
                    "remaining_uncertainties": [],
                    "state_transition": {"to": "completed", "fact_promotions": ["fact_alpha"]},
                    "verified_at": "2026-04-10T09:03:00+08:00",
                    "verifier_id": "verifier.test"
                }
            }),
        ))
        .expect("verification");

    let node = projector.state.nodes.get("node_alpha").expect("node present");
    let task_state = projector.state.task_states.get("task_alpha").expect("task state present");
    let fact = projector.state.facts.get("fact_alpha").expect("fact present");
    assert_eq!(node.state, NodeState::Completed);
    assert_eq!(*task_state, NodeState::Completed);
    assert_eq!(fact.status, device_agent_core::contracts::FactStatus::Verified);
}

#[test]
fn replay_loader_reads_builtin_fixtures() {
    let research = load_builtin_replay("research-brief-flow.json").expect("research fixture should load");
    let crm = load_builtin_replay("crm-followup-flow.json").expect("crm fixture should load");

    assert_eq!(research.replay_id, "replay_research_brief_001");
    assert_eq!(crm.replay_id, "replay_crm_followup_001");
    assert!(!research.timeline.is_empty());
    assert!(!crm.timeline.is_empty());
    assert!(crm.timeline.windows(2).all(|pair| pair[0].step <= pair[1].step));
}

#[test]
fn replay_runner_completes_builtin_research_flow() {
    let fixture = load_builtin_replay("research-brief-flow.json").expect("fixture loads");
    let mut runner = ReplayRunner::new(fixture.clone());
    let result = runner.run(None).expect("runner completes");

    assert_eq!(result.event_log.len(), 18);
    assert_eq!(
        result.state.task_states.get("task_replay_research_brief_001"),
        Some(&NodeState::Completed)
    );
    assert!(!result.selection_history.is_empty());
}

#[test]
fn replay_runner_completes_builtin_crm_flow() {
    let fixture = load_builtin_replay("crm-followup-flow.json").expect("fixture loads");
    let mut runner = ReplayRunner::new(fixture.clone());
    let result = runner.run(None).expect("runner completes");

    assert_eq!(result.event_log.len(), 29);
    assert_eq!(
        result.state.task_states.get("task_replay_crm_followup_001"),
        Some(&NodeState::Completed)
    );
    assert_eq!(result.state.approvals.len(), 2);
    assert_eq!(result.state.recoveries.len(), 1);
}

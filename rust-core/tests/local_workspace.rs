use std::fs;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use chrono::{DateTime, FixedOffset};
use device_agent_core::{
    CapabilityGrant, LocalWorkspaceAdapter, RecoveryRecord, RecoveryStatus, RiskBand, TaskNode, WorkspaceAdapter,
};
use serde_json::{json, Value};

fn ts(raw: &str) -> DateTime<FixedOffset> {
    DateTime::parse_from_rfc3339(raw).expect("valid timestamp")
}

fn unique_runtime_dir(name: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time should be after unix epoch")
        .as_nanos();
    std::env::temp_dir()
        .join("device-agent-doc-rust-tests")
        .join(format!("{name}-{}-{nonce}", std::process::id()))
}

fn seed_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("sandbox")
        .join("local-crm")
        .join("seed")
}

fn read_json(path: PathBuf) -> Value {
    let raw = fs::read_to_string(path).expect("json file should exist");
    serde_json::from_str(&raw).expect("json should parse")
}

fn sample_grant(node_id: &str) -> CapabilityGrant {
    CapabilityGrant {
        grant_id: format!("grant_{node_id}"),
        task_id: "task_replay_crm_followup_001".to_owned(),
        node_id: node_id.to_owned(),
        who: "executor.local.workspace".to_owned(),
        what: "structured.local".to_owned(),
        scope: json!({"node_id": node_id}),
        window: json!({"not_before": "2026-04-10T09:00:00+08:00", "not_after": "2026-04-10T09:30:00+08:00"}),
        budget: json!({"max_retries": 1}),
        reason: "test".to_owned(),
        approval_ref: format!("approval_{node_id}"),
        postcondition_ref: format!("postcondition_{node_id}"),
        principal_ref: "principal.user.primary".to_owned(),
        resource_owner_ref: "owner.workspace.primary".to_owned(),
        approver_ref: "principal.user.primary".to_owned(),
        status: "active".to_owned(),
        issued_at: ts("2026-04-10T09:00:00+08:00"),
        expires_at: ts("2026-04-10T09:30:00+08:00"),
    }
}

fn sample_node(node_id: &str, node_type: &str, risk_class: RiskBand) -> TaskNode {
    TaskNode {
        node_id: node_id.to_owned(),
        task_id: "task_replay_crm_followup_001".to_owned(),
        node_type: node_type.to_owned(),
        objective: format!("objective for {node_id}"),
        desired_delta: json!({"node": node_id}),
        evidence_of_done: json!({"terminal": "completed"}),
        risk_class,
        state: device_agent_core::NodeState::Ready,
        dependencies: Vec::new(),
        required_capabilities: vec!["structured.local".to_owned()],
        principal_ref: "principal.user.primary".to_owned(),
        resource_owner_ref: "owner.workspace.primary".to_owned(),
        grant_refs: Vec::new(),
        artifact_refs: Vec::new(),
        version: 1,
        created_at: ts("2026-04-10T09:00:00+08:00"),
        updated_at: ts("2026-04-10T09:00:00+08:00"),
    }
}

fn sample_action_spec(node_id: &str, extra: Value) -> Value {
    let mut action = json!({
        "action_id": format!("action_{node_id}"),
        "task_id": "task_replay_crm_followup_001",
        "node_id": node_id,
        "required_capability": "structured.local",
    });
    if let Some(object) = action.as_object_mut() {
        if let Some(extra_object) = extra.as_object() {
            for (key, value) in extra_object {
                object.insert(key.clone(), value.clone());
            }
        }
    }
    action
}

#[test]
fn local_workspace_reset_restores_seed_state() {
    let runtime_dir = unique_runtime_dir("reset");
    let adapter = LocalWorkspaceAdapter::new(&runtime_dir);
    adapter.reset_workspace(seed_dir()).expect("seed copy should succeed");

    let crm_path = runtime_dir.join("crm_record.json");
    let mut crm_record = read_json(crm_path.clone());
    crm_record["renewal_status"] = json!("corrupted_state");
    fs::write(&crm_path, serde_json::to_string_pretty(&crm_record).expect("serialize")).expect("write");

    adapter.reset_workspace(seed_dir()).expect("reset should restore seed");
    let restored = read_json(crm_path);
    assert_eq!(restored["renewal_status"], json!("pending_review"));
}

#[test]
fn local_workspace_executes_real_crm_side_effects_and_compensation() {
    let runtime_dir = unique_runtime_dir("scenario");
    let adapter = LocalWorkspaceAdapter::new(&runtime_dir);
    adapter.reset_workspace(seed_dir()).expect("seed copy should succeed");

    let observe = adapter
        .execute_node(
            &sample_node("node_read_crm_record", "observe_sensitive_record", RiskBand::R1),
            &sample_action_spec("node_read_crm_record", json!({})),
            &sample_grant("node_read_crm_record"),
            ts("2026-04-10T09:02:00+08:00"),
        )
        .expect("observe should succeed");
    assert_eq!(observe.fact_candidates.len(), 1);
    assert!(runtime_dir.join("artifacts").join("node_read_crm_record_baseline.json").exists());

    let prepare = adapter
        .execute_node(
            &sample_node("node_prepare_patch", "prepare_crm_patch", RiskBand::R1),
            &sample_action_spec("node_prepare_patch", json!({})),
            &sample_grant("node_prepare_patch"),
            ts("2026-04-10T09:04:00+08:00"),
        )
        .expect("prepare should succeed");
    assert_eq!(prepare.artifact_refs_len(), 2);
    assert!(runtime_dir.join("artifacts").join("node_prepare_patch_patch.json").exists());
    assert!(runtime_dir.join("artifacts").join("node_prepare_patch_email_draft.json").exists());

    let operate = adapter
        .execute_node(
            &sample_node("node_write_crm", "operate_crm_update", RiskBand::R2),
            &sample_action_spec("node_write_crm", json!({"side_effect_class": "bounded_external_modify"})),
            &sample_grant("node_write_crm"),
            ts("2026-04-10T09:06:00+08:00"),
        )
        .expect("operate should succeed");
    let crm_after_write = read_json(runtime_dir.join("crm_record.json"));
    assert_eq!(crm_after_write["renewal_status"], json!("ready_to_contact"));
    let rollback_policy = operate.recovery.clone().expect("rollback should be armed");
    assert_eq!(rollback_policy["recovery_kind"], json!("rollback"));
    assert!(runtime_dir.join("artifacts").join("node_write_crm_rollback_plan.json").exists());

    let commit = adapter
        .execute_node(
            &sample_node("node_send_email", "commit_external_send", RiskBand::R3),
            &sample_action_spec(
                "node_send_email",
                json!({"side_effect_class": "irreversible_external_send", "compensation_policy_ref": "node_send_email_compensation_plan.json"}),
            ),
            &sample_grant("node_send_email"),
            ts("2026-04-10T09:08:00+08:00"),
        )
        .expect("commit should succeed");
    let crm_after_send = read_json(runtime_dir.join("crm_record.json"));
    let outbox_after_send = read_json(runtime_dir.join("outbox.json"));
    assert_eq!(crm_after_send["renewal_status"], json!("follow_up_sent"));
    assert_eq!(outbox_after_send.as_array().expect("outbox array").len(), 1);
    let compensation_policy = commit.recovery.clone().expect("compensation should be armed");
    assert_eq!(compensation_policy["recovery_kind"], json!("compensate"));
    assert!(runtime_dir.join("artifacts").join("node_send_email_compensation_plan.json").exists());

    let recovery = RecoveryRecord {
        recovery_id: "recovery_node_send_email".to_owned(),
        task_id: "task_replay_crm_followup_001".to_owned(),
        node_id: "node_send_email".to_owned(),
        action: "compensate".to_owned(),
        recorded_at: ts("2026-04-10T09:09:00+08:00"),
        policy_ref: "node_send_email_compensation_plan.json".to_owned(),
        status: RecoveryStatus::Armed,
        artifact_refs: Vec::new(),
        side_effect_summary: None,
    };

    let recovery_outcome = adapter
        .execute_recovery(&recovery, ts("2026-04-10T09:10:00+08:00"))
        .expect("compensation should succeed");
    let crm_after_compensation = read_json(runtime_dir.join("crm_record.json"));
    let outbox_after_compensation = read_json(runtime_dir.join("outbox.json"));
    assert_eq!(outbox_after_compensation.as_array().expect("outbox array").len(), 2);
    assert_eq!(
        outbox_after_compensation
            .as_array()
            .expect("outbox array")
            .last()
            .expect("correction item")["kind"],
        json!("correction_message")
    );
    assert!(crm_after_compensation.get("last_compensation_at").is_some());
    assert_eq!(recovery_outcome.artifact_refs.len(), 1);
    assert!(runtime_dir.join("artifacts").join("node_send_email_compensation_executed.json").exists());
}

trait OutcomeExt {
    fn artifact_refs_len(&self) -> usize;
}

impl OutcomeExt for device_agent_core::WorkspaceExecutionOutcome {
    fn artifact_refs_len(&self) -> usize {
        self.receipt.artifact_refs.len()
    }
}

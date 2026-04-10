use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use device_agent_core::{run_local_crm_scenario, run_local_crm_with_compensation, NodeState};
use serde_json::Value;

fn unique_runtime_dir(name: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time should be after unix epoch")
        .as_nanos();
    std::env::temp_dir()
        .join("device-agent-doc-rust-scenarios")
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
    let raw = std::fs::read_to_string(path).expect("json should exist");
    serde_json::from_str(&raw).expect("json should parse")
}

#[test]
fn local_crm_runner_matches_python_base_summary_and_workspace_effects() {
    let runtime_dir = unique_runtime_dir("base");
    let result = run_local_crm_scenario(seed_dir(), &runtime_dir).expect("scenario should succeed");

    assert_eq!(result.event_log.len(), 29);
    assert_eq!(
        result.state.task_states.get("task_replay_crm_followup_001"),
        Some(&NodeState::Completed)
    );
    assert_eq!(result.state.approvals.len(), 2);
    assert_eq!(result.state.recoveries.len(), 1);

    let crm_record = read_json(runtime_dir.join("crm_record.json"));
    let outbox = read_json(runtime_dir.join("outbox.json"));
    assert_eq!(crm_record["renewal_status"], Value::String("follow_up_sent".to_owned()));
    assert_eq!(outbox.as_array().expect("outbox array").len(), 1);
    assert!(runtime_dir.join("artifacts").join("node_send_email_compensation_plan.json").exists());
}

#[test]
fn local_crm_runner_executes_compensation_and_records_extra_event() {
    let runtime_dir = unique_runtime_dir("compensation");
    let result = run_local_crm_with_compensation(seed_dir(), &runtime_dir).expect("scenario should succeed");

    assert_eq!(result.event_log.len(), 30);
    assert_eq!(result.state.recoveries.len(), 2);
    assert!(
        result
            .state
            .recoveries
            .values()
            .any(|recovery| recovery.status == device_agent_core::RecoveryStatus::Executed)
    );

    let crm_record = read_json(runtime_dir.join("crm_record.json"));
    let outbox = read_json(runtime_dir.join("outbox.json"));
    assert_eq!(outbox.as_array().expect("outbox array").len(), 2);
    assert_eq!(
        outbox.as_array().expect("outbox array").last().expect("last message")["kind"],
        Value::String("correction_message".to_owned())
    );
    assert!(crm_record.get("last_compensation_at").is_some());
    assert!(runtime_dir.join("artifacts").join("node_send_email_compensation_executed.json").exists());
}

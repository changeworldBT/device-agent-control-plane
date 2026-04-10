use std::io::{Read, Write};
use std::net::TcpStream;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use device_agent_core::{
    run_http_crm_scenario, run_http_crm_with_compensation, MockHttpCrmServer, NodeState,
    RecoveryStatus,
};
use serde_json::json;

fn unique_runtime_dir(name: &str) -> PathBuf {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("system time should be after unix epoch")
        .as_nanos();
    std::env::temp_dir()
        .join("device-agent-doc-rust-http-scenarios")
        .join(format!("{name}-{}-{nonce}", std::process::id()))
}

fn seed_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("sandbox")
        .join("local-crm")
        .join("seed")
}

#[test]
fn mock_http_server_requires_grant_headers() {
    let server = MockHttpCrmServer::new(seed_dir()).expect("server should start");
    let authority = server
        .base_url()
        .strip_prefix("http://")
        .expect("mock server should use http");
    let mut stream = TcpStream::connect(authority).expect("server should accept connections");
    stream
        .write_all(
            format!("GET /crm/record HTTP/1.1\r\nHost: {authority}\r\nConnection: close\r\n\r\n")
                .as_bytes(),
        )
        .expect("request should write");
    let mut response = String::new();
    stream
        .read_to_string(&mut response)
        .expect("response should read");
    assert!(
        response.starts_with("HTTP/1.1 403"),
        "expected 403 response, got {response}"
    );
}

#[test]
fn http_crm_runner_updates_remote_state_and_artifacts() {
    let server = MockHttpCrmServer::new(seed_dir()).expect("server should start");
    let runtime_dir = unique_runtime_dir("base");
    let result =
        run_http_crm_scenario(server.base_url(), &runtime_dir).expect("scenario should succeed");
    let snapshot = server.snapshot().expect("snapshot should succeed");

    assert_eq!(result.event_log.len(), 29);
    assert_eq!(
        result.state.task_states.get("task_replay_crm_followup_001"),
        Some(&NodeState::Completed)
    );
    assert_eq!(result.state.approvals.len(), 2);
    assert_eq!(result.state.recoveries.len(), 1);
    assert_eq!(
        snapshot.crm_record["renewal_status"],
        json!("follow_up_sent")
    );
    assert_eq!(snapshot.outbox.as_array().expect("outbox array").len(), 1);
    assert!(runtime_dir
        .join("artifacts")
        .join("node_send_email_compensation_plan.json")
        .exists());
}

#[test]
fn http_crm_runner_executes_remote_compensation() {
    let server = MockHttpCrmServer::new(seed_dir()).expect("server should start");
    let runtime_dir = unique_runtime_dir("compensation");
    let result = run_http_crm_with_compensation(server.base_url(), &runtime_dir)
        .expect("scenario should succeed");
    let snapshot = server.snapshot().expect("snapshot should succeed");

    assert_eq!(result.event_log.len(), 30);
    assert_eq!(result.state.recoveries.len(), 2);
    assert!(result
        .state
        .recoveries
        .values()
        .any(|recovery| recovery.status == RecoveryStatus::Executed));
    assert_eq!(snapshot.outbox.as_array().expect("outbox array").len(), 2);
    assert_eq!(
        snapshot
            .outbox
            .as_array()
            .expect("outbox array")
            .last()
            .expect("last message")["kind"],
        json!("correction_message")
    );
    assert!(snapshot.crm_record.get("last_compensation_at").is_some());
    assert!(runtime_dir
        .join("artifacts")
        .join("node_send_email_compensation_executed.json")
        .exists());
}

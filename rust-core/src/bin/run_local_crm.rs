use std::env;
use std::path::PathBuf;

use device_agent_core::{run_local_crm_scenario, run_local_crm_with_compensation, FactStatus};
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut compensate = false;
    let args = env::args().skip(1).collect::<Vec<_>>();
    for arg in args {
        if arg == "--compensate" {
            compensate = true;
        }
    }

    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..");
    let seed_dir = root.join("sandbox").join("local-crm").join("seed");
    let runtime_dir = root.join("sandbox").join("local-crm").join(if compensate { "runtime-rust-compensation" } else { "runtime-rust" });

    let result = if compensate {
        run_local_crm_with_compensation(&seed_dir, &runtime_dir)?
    } else {
        run_local_crm_scenario(&seed_dir, &runtime_dir)?
    };

    let task_id = format!("task_{}", result.fixture.replay_id);
    let task_terminal = result
        .state
        .task_states
        .get(&task_id)
        .map(|state| serde_json::to_value(state).ok())
        .flatten()
        .and_then(|value| value.as_str().map(ToOwned::to_owned))
        .unwrap_or_else(|| "created".to_owned());
    let verified_facts = result
        .state
        .facts
        .iter()
        .filter(|(_, fact)| fact.status == FactStatus::Verified)
        .map(|(fact_id, _)| fact_id.clone())
        .collect::<Vec<_>>();
    let executed_recoveries = result
        .state
        .recoveries
        .values()
        .filter(|recovery| recovery.status == device_agent_core::RecoveryStatus::Executed)
        .count();

    let summary = if compensate {
        json!({
            "replay_id": result.fixture.replay_id,
            "events": result.event_log.len(),
            "task_terminal": task_terminal,
            "approvals": result.state.approvals.len(),
            "recoveries": result.state.recoveries.len(),
            "executed_recoveries": executed_recoveries,
            "verified_facts": verified_facts,
        })
    } else {
        json!({
            "replay_id": result.fixture.replay_id,
            "events": result.event_log.len(),
            "task_terminal": task_terminal,
            "approvals": result.state.approvals.len(),
            "recoveries": result.state.recoveries.len(),
            "verified_facts": verified_facts,
        })
    };

    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}

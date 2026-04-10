use std::fs;
use std::path::PathBuf;

use device_agent_core::{FactStatus, ReplayRunner};
use serde_json::json;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let flows_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("schemas")
        .join("examples")
        .join("flows");

    let mut flow_paths = fs::read_dir(&flows_dir)?
        .filter_map(|entry| entry.ok().map(|item| item.path()))
        .filter(|path| path.extension().and_then(|value| value.to_str()) == Some("json"))
        .collect::<Vec<_>>();
    flow_paths.sort();

    let mut summaries = Vec::new();
    for flow_path in flow_paths {
        let mut runner = ReplayRunner::from_path(&flow_path)?;
        let result = runner.run(None)?;
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

        summaries.push(json!({
            "replay_id": result.fixture.replay_id,
            "events": result.event_log.len(),
            "task_terminal": task_terminal,
            "verified_facts": verified_facts,
            "approvals": result.state.approvals.len(),
            "recoveries": result.state.recoveries.len(),
        }));
    }

    println!("{}", serde_json::to_string_pretty(&summaries)?);
    Ok(())
}

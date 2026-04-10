use std::path::PathBuf;

use device_agent_core::{load_model_config_json, AgentMode, ModelProviderConfig, ModelRunMode};

fn example_config() -> ModelProviderConfig {
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../config/model-providers.example.json");
    let raw = std::fs::read_to_string(path).expect("example config should be readable");
    load_model_config_json(&raw).expect("example config should be valid")
}

#[test]
fn model_config_routes_multi_agent_roles() {
    let config = example_config();

    let planner = config
        .resolve_route("planner", None, None)
        .expect("planner route should resolve");
    let classifier = config
        .resolve_route("classifier", None, None)
        .expect("classifier route should resolve");

    assert_eq!(planner.mode, ModelRunMode::Mock);
    assert_eq!(planner.agent_mode, AgentMode::MultiAgent);
    assert_eq!(planner.agent_id, "architect");
    assert_eq!(planner.provider_name, "primary_cloud");
    assert_eq!(classifier.agent_id, "router");
    assert_eq!(classifier.provider_name, "local_mock");
    assert_eq!(classifier.model.as_deref(), Some("mock-router-v1"));
}

#[test]
fn provider_override_switches_provider_without_rewriting_team() {
    let config = example_config();

    let route = config
        .resolve_route("planner", Some("local_mock"), None)
        .expect("provider override should resolve");

    assert_eq!(route.agent_id, "architect");
    assert_eq!(route.provider_name, "local_mock");
    assert_eq!(route.model.as_deref(), Some("mock-deterministic-v1"));
}

#[test]
fn agent_override_switches_team_member() {
    let config = example_config();

    let route = config
        .resolve_route("planner", None, Some("auditor"))
        .expect("agent override should resolve");

    assert_eq!(route.agent_id, "auditor");
    assert_eq!(route.provider_name, "local_mock");
    assert_eq!(route.model.as_deref(), Some("mock-verifier-v1"));
}

#[test]
fn single_agent_mode_uses_default_agent_for_all_roles() {
    let mut config = example_config();
    config.agents.mode = AgentMode::SingleAgent;

    let route = config
        .resolve_route("classifier", None, None)
        .expect("single agent route should resolve");

    assert_eq!(route.agent_mode, AgentMode::SingleAgent);
    assert_eq!(route.agent_id, "architect");
    assert_eq!(route.provider_name, "primary_cloud");
}

#[test]
fn active_provider_switch_affects_agents_without_provider_assignment() {
    let mut config = example_config();
    config.active_provider = Some("cheap_router".to_owned());
    config
        .agents
        .members
        .get_mut("architect")
        .expect("architect should exist")
        .provider = None;

    let route = config
        .resolve_route("planner", None, None)
        .expect("active provider route should resolve");

    assert_eq!(route.provider_name, "cheap_router");
}

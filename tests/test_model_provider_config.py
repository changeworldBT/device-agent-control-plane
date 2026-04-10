from __future__ import annotations

import unittest
from pathlib import Path

from model.provider_config import load_model_config, resolve_model_route, with_active_provider, with_agent_mode


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = ROOT / "config" / "model-providers.example.json"


class ModelProviderConfigTests(unittest.TestCase):
    def test_example_config_routes_multi_agent_roles(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)

        planner = resolve_model_route(config, "planner", env={})
        classifier = resolve_model_route(config, "classifier", env={})

        self.assertEqual(planner.agent_mode, "multi_agent")
        self.assertEqual(planner.agent_id, "architect")
        self.assertEqual(planner.provider_name, "primary_cloud")
        self.assertEqual(classifier.agent_id, "router")
        self.assertEqual(classifier.provider_name, "local_mock")
        self.assertEqual(classifier.model, "mock-router-v1")

    def test_provider_override_switches_provider_without_rewriting_team(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)

        route = resolve_model_route(
            config,
            "planner",
            env={"DEVICE_AGENT_MODEL_PROVIDER": "local_mock"},
        )

        self.assertEqual(route.agent_id, "architect")
        self.assertEqual(route.provider_name, "local_mock")
        self.assertEqual(route.model, "mock-deterministic-v1")

    def test_role_specific_agent_override_switches_one_team_member(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)

        route = resolve_model_route(
            config,
            "planner",
            env={"DEVICE_AGENT_AGENT_PLANNER": "auditor"},
        )

        self.assertEqual(route.agent_id, "auditor")
        self.assertEqual(route.provider_name, "local_mock")
        self.assertEqual(route.model, "mock-verifier-v1")

    def test_single_agent_mode_uses_default_agent_for_all_roles(self) -> None:
        config = with_agent_mode(load_model_config(EXAMPLE_CONFIG), "single_agent")

        route = resolve_model_route(config, "classifier", env={})

        self.assertEqual(route.agent_mode, "single_agent")
        self.assertEqual(route.agent_id, "architect")
        self.assertEqual(route.provider_name, "primary_cloud")

    def test_active_provider_switch_only_affects_agents_without_provider_assignment(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)
        config["agents"]["members"]["architect"].pop("provider")
        config = with_active_provider(config, "cheap_router")

        route = resolve_model_route(config, "planner", env={})

        self.assertEqual(route.provider_name, "cheap_router")

    def test_live_provider_reports_secret_presence_without_exposing_value(self) -> None:
        config = load_model_config(EXAMPLE_CONFIG)

        route = resolve_model_route(
            config,
            "planner",
            env={
                "DEVICE_AGENT_MODEL_MODE": "live",
                "DEVICE_AGENT_PRIMARY_BASE_URL": "https://provider.example/v1",
                "DEVICE_AGENT_PRIMARY_API_KEY": "secret-value",
                "DEVICE_AGENT_PLANNER_MODEL": "planner-model",
            },
        )

        redacted = route.as_redacted_dict()
        self.assertEqual(redacted["mode"], "live")
        self.assertEqual(redacted["base_url"], "https://provider.example/v1")
        self.assertTrue(redacted["api_key_configured"])
        self.assertNotIn("secret-value", str(redacted))


if __name__ == "__main__":
    unittest.main()

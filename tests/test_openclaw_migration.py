from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from compat.openclaw_migration import migrate_openclaw, parse_json5_subset, write_local_config


OPENCLAW_CONFIG = """
{
  // JSON5-style OpenClaw config subset.
  agents: {
    defaults: {
      workspace: '__WORKSPACE__',
      model: {
        primary: 'anthropic/claude-sonnet-4-6',
        fallbacks: ['openai/gpt-5.4'],
      },
      skills: ['shell', 'browser'],
    },
    list: [
      {
        id: 'main',
        default: true,
        name: 'Main Assistant',
        model: 'anthropic/claude-sonnet-4-6',
      },
      {
        id: 'router',
        name: 'Router',
        model: 'openai/gpt-5.4-mini',
        skills: ['classifier'],
      },
    ],
  },
}
"""


class OpenClawMigrationTests(unittest.TestCase):
    def test_json5_subset_parser_handles_comments_unquoted_keys_and_trailing_commas(self) -> None:
        parsed = parse_json5_subset("{ agents: { list: [{ id: 'main', }], }, }")

        self.assertEqual(parsed["agents"]["list"][0]["id"], "main")

    def test_migration_generates_candidate_only_provider_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / "AGENTS.md").write_text("# OpenClaw agent instructions\n", encoding="utf-8")
            config_path = root / "openclaw.json"
            config_path.write_text(OPENCLAW_CONFIG.replace("__WORKSPACE__", str(workspace).replace("\\", "\\\\")), encoding="utf-8")

            report = migrate_openclaw(config_path=config_path)

        generated = report["generated_config"]
        self.assertEqual(generated["agents"]["mode"], "multi_agent")
        self.assertEqual(generated["agents"]["default_agent"], "main")
        self.assertIn("openclaw_anthropic", generated["providers"])
        self.assertIn("openclaw_openai", generated["providers"])
        self.assertEqual(generated["agents"]["role_map"]["classifier"], "router")
        self.assertEqual(generated["agents"]["members"]["router"]["roles"], ["classifier"])
        self.assertEqual(report["external_handoff"]["capsule_or_resume_payload"]["trust_ceiling"], "candidate_only")
        self.assertTrue(any(path.endswith("AGENTS.md") for path in report["workspace_files_found"]))
        self.assertTrue(any("credentials" in path for path in report["skipped_secret_paths"]))

    def test_write_local_config_requires_force_for_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "model-providers.local.json"
            output.write_text("{}", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_local_config(
                    {
                        "version": 1,
                        "mode": "mock",
                        "default_provider": "local_mock",
                        "providers": {"local_mock": {"kind": "mock"}},
                        "agents": {
                            "mode": "single_agent",
                            "default_agent": "main",
                            "members": {"main": {"provider": "local_mock"}},
                        },
                    },
                    output_path=output,
                )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

import runtime_backend


class RuntimeBackendTests(unittest.TestCase):
    def test_auto_backend_falls_back_to_python_when_cargo_is_missing(self) -> None:
        with mock.patch("runtime_backend.resolve_cargo", side_effect=FileNotFoundError("missing cargo")):
            self.assertFalse(runtime_backend.rust_backend_available())
            self.assertEqual(runtime_backend.normalize_backend("auto"), "python")

    def test_configured_rust_target_reads_project_cargo_config(self) -> None:
        self.assertEqual(runtime_backend.configured_rust_target(), "x86_64-pc-windows-gnullvm")

    def test_configured_rust_target_prefers_env_override(self) -> None:
        with mock.patch.dict("os.environ", {"DEVICE_AGENT_RUST_TARGET": "x86_64-pc-windows-msvc"}, clear=False):
            self.assertEqual(runtime_backend.configured_rust_target(), "x86_64-pc-windows-msvc")

    def test_project_target_dir_stays_inside_the_repo(self) -> None:
        target_dir = runtime_backend.project_target_dir()

        self.assertEqual(target_dir, Path(__file__).resolve().parents[1] / "rust-core" / "target")
        self.assertIn("device-agent-doc", str(target_dir))
        self.assertNotIn(".device-agent-global", str(target_dir))


if __name__ == "__main__":
    unittest.main()

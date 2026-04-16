from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bootstrap_rust_env


class BootstrapRustEnvTests(unittest.TestCase):
    def test_required_rust_target_matches_project_configuration(self) -> None:
        self.assertEqual(bootstrap_rust_env.required_rust_target(), "x86_64-pc-windows-gnullvm")

    def test_resolve_rustup_prefers_cargo_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bin_dir = Path(temp_dir)
            cargo = bin_dir / "cargo.exe"
            rustup = bin_dir / "rustup.exe"
            cargo.write_text("", encoding="utf-8")
            rustup.write_text("", encoding="utf-8")

            self.assertEqual(bootstrap_rust_env.resolve_rustup(cargo), rustup)

    def test_installed_targets_parses_rustup_output(self) -> None:
        completed = mock.Mock(returncode=0, stdout="x86_64-pc-windows-gnullvm\nwasm32-unknown-unknown\n", stderr="")
        with mock.patch("bootstrap_rust_env.subprocess.run", return_value=completed):
            targets = bootstrap_rust_env.installed_targets(Path("rustup.exe"))

        self.assertEqual(targets, {"x86_64-pc-windows-gnullvm", "wasm32-unknown-unknown"})

    def test_target_is_usable_checks_reported_target_libdir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            target_libdir = Path(temp_dir)
            completed = mock.Mock(returncode=0, stdout=str(target_libdir), stderr="")
            with mock.patch("bootstrap_rust_env.subprocess.run", return_value=completed):
                self.assertTrue(bootstrap_rust_env.target_is_usable(Path("rustc.exe"), "x86_64-pc-windows-gnullvm"))


if __name__ == "__main__":
    unittest.main()

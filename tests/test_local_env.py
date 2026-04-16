from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from local_env import load_project_env, read_env_file, update_env_file


class LocalEnvTests(unittest.TestCase):
    def test_load_project_env_fills_missing_values_without_overriding_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "\n".join(
                    [
                        "DEVICE_AGENT_ENV_TEST_NEW=from-file",
                        "DEVICE_AGENT_ENV_TEST_EXISTING=from-file",
                        "DEVICE_AGENT_ENV_TEST_QUOTED=\"quoted value\"",
                    ]
                ),
                encoding="utf-8",
            )

            old_new = os.environ.pop("DEVICE_AGENT_ENV_TEST_NEW", None)
            old_existing = os.environ.get("DEVICE_AGENT_ENV_TEST_EXISTING")
            old_quoted = os.environ.pop("DEVICE_AGENT_ENV_TEST_QUOTED", None)
            os.environ["DEVICE_AGENT_ENV_TEST_EXISTING"] = "from-shell"
            try:
                loaded = load_project_env(env_path)

                self.assertEqual(os.environ["DEVICE_AGENT_ENV_TEST_NEW"], "from-file")
                self.assertEqual(os.environ["DEVICE_AGENT_ENV_TEST_EXISTING"], "from-shell")
                self.assertEqual(os.environ["DEVICE_AGENT_ENV_TEST_QUOTED"], "quoted value")
                self.assertEqual(loaded["DEVICE_AGENT_ENV_TEST_NEW"], "from-file")
                self.assertNotIn("DEVICE_AGENT_ENV_TEST_EXISTING", loaded)
            finally:
                for key in (
                    "DEVICE_AGENT_ENV_TEST_NEW",
                    "DEVICE_AGENT_ENV_TEST_EXISTING",
                    "DEVICE_AGENT_ENV_TEST_QUOTED",
                ):
                    os.environ.pop(key, None)
                if old_new is not None:
                    os.environ["DEVICE_AGENT_ENV_TEST_NEW"] = old_new
                if old_existing is not None:
                    os.environ["DEVICE_AGENT_ENV_TEST_EXISTING"] = old_existing
                if old_quoted is not None:
                    os.environ["DEVICE_AGENT_ENV_TEST_QUOTED"] = old_quoted

    def test_update_env_file_preserves_comments_and_updates_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("# local config\nEXISTING=old\n", encoding="utf-8")

            updated = update_env_file({"EXISTING": "new", "ADDED_KEY": "added"}, env_path)

            self.assertEqual(updated["EXISTING"], "new")
            self.assertEqual(updated["ADDED_KEY"], "added")
            self.assertEqual(read_env_file(env_path)["ADDED_KEY"], "added")
            self.assertIn("# local config", env_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from urllib import error, request

from scenarios.http_crm_runner import run_http_crm_scenario, run_http_crm_with_compensation
from scenarios.mock_http_crm_server import MockHttpCrmServer


ROOT = Path(__file__).resolve().parent.parent


class HttpCrmScenarioTests(unittest.TestCase):
    def _runtime_dir(self, name: str) -> Path:
        root = Path(tempfile.gettempdir()) / "device-agent-doc-http-tests"
        root.mkdir(parents=True, exist_ok=True)
        return root / name

    def test_mock_http_server_requires_grant_headers(self) -> None:
        seed_dir = ROOT / "sandbox" / "local-crm" / "seed"
        with MockHttpCrmServer(seed_dir=seed_dir) as server:
            req = request.Request(f"{server.base_url}/crm/record", method="GET")
            with self.assertRaises(error.HTTPError) as context:
                request.urlopen(req)
            self.assertEqual(context.exception.code, 403)

    def test_http_crm_scenario_updates_remote_state_and_artifacts(self) -> None:
        seed_dir = ROOT / "sandbox" / "local-crm" / "seed"
        runtime_dir = self._runtime_dir("base")
        with MockHttpCrmServer(seed_dir=seed_dir) as server:
            result = run_http_crm_scenario(base_url=server.base_url, runtime_dir=runtime_dir, reset_remote=server.reset)
            snapshot = server.snapshot()

        self.assertEqual(result.state.current_task_terminal(result.fixture.task_id), "completed")
        self.assertEqual(len(result.state.approvals), 2)
        self.assertEqual(len(result.state.recoveries), 1)
        self.assertEqual(snapshot["crm_record"]["renewal_status"], "follow_up_sent")
        self.assertEqual(len(snapshot["outbox"]), 1)
        self.assertTrue((runtime_dir / "artifacts" / "node_send_email_compensation_plan.json").exists())

    def test_http_crm_compensation_executes_remote_correction(self) -> None:
        seed_dir = ROOT / "sandbox" / "local-crm" / "seed"
        runtime_dir = self._runtime_dir("compensation")
        with MockHttpCrmServer(seed_dir=seed_dir) as server:
            result = run_http_crm_with_compensation(base_url=server.base_url, runtime_dir=runtime_dir, reset_remote=server.reset)
            snapshot = server.snapshot()

        self.assertEqual(result.state.current_task_terminal(result.fixture.task_id), "completed")
        self.assertTrue(any(item.get("status") == "executed" for item in result.state.recoveries.values()))
        self.assertEqual(len(snapshot["outbox"]), 2)
        self.assertEqual(snapshot["outbox"][-1]["kind"], "correction_message")
        self.assertIn("last_compensation_at", snapshot["crm_record"])
        self.assertTrue((runtime_dir / "artifacts" / "node_send_email_compensation_executed.json").exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scenarios.local_crm_runner import LocalCrmScenarioRunner, run_local_crm_with_compensation


ROOT = Path(__file__).resolve().parent.parent


class LocalCrmScenarioTests(unittest.TestCase):
    def _runtime_dir(self, name: str) -> Path:
        root = Path(tempfile.gettempdir()) / "device-agent-doc-tests"
        root.mkdir(parents=True, exist_ok=True)
        return root / name

    def test_local_crm_scenario_touches_real_workspace_state(self) -> None:
        runner = LocalCrmScenarioRunner(runtime_dir=self._runtime_dir("scenario-basic"))
        result = runner.run()

        self.assertEqual(result.state.current_task_terminal(result.fixture.task_id), "completed")
        self.assertEqual(len(result.state.approvals), 2)
        self.assertEqual(len(result.state.recoveries), 1)

        crm_record = json.loads((runner.runtime_dir / "crm_record.json").read_text(encoding="utf-8"))
        outbox = json.loads((runner.runtime_dir / "outbox.json").read_text(encoding="utf-8"))

        self.assertEqual(crm_record["renewal_status"], "follow_up_sent")
        self.assertEqual(len(outbox), 1)
        self.assertTrue((runner.runtime_dir / "artifacts" / "node_send_email_compensation_plan.json").exists())

    def test_local_crm_run_resets_workspace_from_seed(self) -> None:
        runner = LocalCrmScenarioRunner(runtime_dir=self._runtime_dir("scenario-reset"))
        runner.run()
        crm_path = runner.runtime_dir / "crm_record.json"
        modified = json.loads(crm_path.read_text(encoding="utf-8"))
        modified["renewal_status"] = "corrupted_state"
        crm_path.write_text(json.dumps(modified, indent=2, ensure_ascii=False), encoding="utf-8")

        runner.run()
        reset_state = json.loads(crm_path.read_text(encoding="utf-8"))
        self.assertEqual(reset_state["renewal_status"], "follow_up_sent")

    def test_local_crm_compensation_executes_real_correction_action(self) -> None:
        runtime_dir = self._runtime_dir("scenario-compensation")
        result = run_local_crm_with_compensation(runtime_dir=runtime_dir)
        crm_record = json.loads((runtime_dir / "crm_record.json").read_text(encoding="utf-8"))
        outbox = json.loads((runtime_dir / "outbox.json").read_text(encoding="utf-8"))

        self.assertEqual(result.state.current_task_terminal(result.fixture.task_id), "completed")
        self.assertTrue(any(item.get("status") == "executed" for item in result.state.recoveries.values()))
        self.assertEqual(len(outbox), 2)
        self.assertEqual(outbox[-1]["kind"], "correction_message")
        self.assertIn("last_compensation_at", crm_record)
        self.assertTrue((runtime_dir / "artifacts" / "node_send_email_compensation_executed.json").exists())


if __name__ == "__main__":
    unittest.main()

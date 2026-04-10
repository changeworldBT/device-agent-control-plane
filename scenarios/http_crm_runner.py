from __future__ import annotations

import json
import shutil
from datetime import timedelta
from pathlib import Path
from typing import Any, Callable

from execution.http.mock_crm_adapter import MockCrmHttpAdapter
from replay.loader import load_builtin_replay
from replay.runner import BASE_TIME, ReplayRunner, ReplayStep, ReplayResult


class HttpCrmScenarioRunner(ReplayRunner):
    def __init__(
        self,
        *,
        base_url: str,
        runtime_dir: Path | None = None,
        reset_remote: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(load_builtin_replay("crm-followup-flow.json"))
        root = Path(__file__).resolve().parent.parent
        self.runtime_dir = runtime_dir or (root / "sandbox" / "http-crm" / "runtime")
        self.reset_remote = reset_remote
        self.adapter = MockCrmHttpAdapter(base_url=base_url, artifact_dir=self.runtime_dir / "artifacts")

    def run(self, *, step_limit: int | None = None) -> ReplayResult:
        if self.runtime_dir.exists():
            shutil.rmtree(self.runtime_dir)
        (self.runtime_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        if self.reset_remote is not None:
            self.reset_remote()
        return super().run(step_limit=step_limit)

    def _build_receipt(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        occurred_at = self._time_for_step(step.step, token_index)
        action_spec = self._action_specs.get(step.node_id)
        if action_spec is None:
            action_spec = self._build_action_spec(step, token_index)
        grant = self.projector.state.grants[next(reversed(self.projector.state.grants))]
        node = self.projector.state.nodes[step.node_id]
        receipt, result = self.adapter.execute_node(
            node=node,
            action_spec=action_spec,
            grant=grant,
            occurred_at=occurred_at,
        )
        self._pending_facts = getattr(self, "_pending_facts", {})
        self._pending_recoveries = getattr(self, "_pending_recoveries", {})
        self._pending_facts[step.node_id] = result.fact_candidates
        self._pending_recoveries[step.node_id] = result.recovery
        return receipt

    def _build_candidate_facts(self, step: ReplayStep, token_index: int) -> list[dict[str, Any]]:
        del token_index
        pending = getattr(self, "_pending_facts", {})
        return list(pending.get(step.node_id, []))

    def _build_recovery(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        del token_index
        pending = getattr(self, "_pending_recoveries", {})
        recovery = pending.get(step.node_id)
        if recovery is None:
            return super()._build_recovery(step, token_index)
        occurred_at = self._time_for_step(step.step, 99)
        return {
            "recovery_id": f"recovery_{self.fixture.replay_id}_{step.node_id}_{step.step}",
            "task_id": self.fixture.task_id,
            "node_id": step.node_id,
            "action": recovery["recovery_kind"],
            "recorded_at": occurred_at.isoformat(),
            "policy_ref": recovery["policy_ref"],
            "status": "armed",
        }

    def execute_all_armed_recoveries(self) -> None:
        armed = [item for item in self.projector.state.recoveries.values() if item.get("status") == "armed"]
        if not armed:
            return
        grant = self.projector.state.grants[next(reversed(self.projector.state.grants))]
        for index, recovery in enumerate(armed, start=1):
            occurred_at = BASE_TIME + timedelta(minutes=20, seconds=index)
            result = self.adapter.execute_recovery(
                recovery=recovery,
                occurred_at=occurred_at,
                grant=grant,
            )
            payload = {
                "recovery_id": f"{recovery['recovery_id']}.executed",
                "task_id": recovery["task_id"],
                "node_id": recovery["node_id"],
                "action": recovery["action"],
                "recorded_at": occurred_at.isoformat(),
                "policy_ref": recovery["policy_ref"],
                "status": "executed",
                "artifact_refs": result.artifact_refs,
                "side_effect_summary": result.side_effect_summary,
            }
            self._emit_event(90 + index, "recovery.recorded", {"recovery": payload}, recovery["node_id"], f"recovery-executed-{index}")


def run_http_crm_scenario(*, base_url: str, runtime_dir: Path | None = None, reset_remote: Callable[[], None] | None = None) -> ReplayResult:
    return HttpCrmScenarioRunner(base_url=base_url, runtime_dir=runtime_dir, reset_remote=reset_remote).run()


def run_http_crm_with_compensation(
    *,
    base_url: str,
    runtime_dir: Path | None = None,
    reset_remote: Callable[[], None] | None = None,
) -> ReplayResult:
    runner = HttpCrmScenarioRunner(base_url=base_url, runtime_dir=runtime_dir, reset_remote=reset_remote)
    result = runner.run()
    runner.execute_all_armed_recoveries()
    return ReplayResult(
        fixture=result.fixture,
        event_log=runner.log,
        state=runner.projector.state,
        selection_history=result.selection_history,
    )


def summarize_http_result(result: ReplayResult) -> str:
    summary = {
        "replay_id": result.fixture.replay_id,
        "events": len(result.event_log),
        "task_terminal": result.state.current_task_terminal(result.fixture.task_id),
        "approvals": len(result.state.approvals),
        "recoveries": len(result.state.recoveries),
        "executed_recoveries": sum(1 for item in result.state.recoveries.values() if item.get("status") == "executed"),
        "verified_facts": [fact_id for fact_id, fact in sorted(result.state.facts.items()) if fact["status"] == "verified"],
    }
    return json.dumps(summary, indent=2, ensure_ascii=False)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from control.grants.guards import ensure_dispatch_allowed
from control.approvals.guards import ensure_approval_for_grant
from execution.local.dispatcher import build_action_spec, build_receipt
from replay.loader import ReplayFixture, ReplayStep, load_replay
from replay.schema_support import validate_against_schema
from runtime.events.log import EventLog
from runtime.projector.capsule import build_minimal_capsule
from runtime.projector.state import EventProjector, MaterializedState
from selector.v0.scoring import select_next_node
from verification.core.verifier import build_verification_result


BASE_TIME = datetime(2026, 4, 10, 9, 0, 0, tzinfo=timezone(timedelta(hours=8)))


@dataclass
class ReplayResult:
    fixture: ReplayFixture
    event_log: EventLog
    state: MaterializedState
    selection_history: list[dict[str, Any]] = field(default_factory=list)


class ReplayRunner:
    def __init__(self, fixture: ReplayFixture) -> None:
        self.fixture = fixture
        self.log = EventLog()
        self.projector = EventProjector()
        self.selection_history: list[dict[str, Any]] = []
        self._action_specs: dict[str, dict[str, Any]] = {}
        self._current_index = 0
        self._bootstrapped = False

    @classmethod
    def from_path(cls, path: Path) -> "ReplayRunner":
        return cls(load_replay(path))

    def run(self, *, step_limit: int | None = None) -> ReplayResult:
        self._bootstrap_if_needed()
        for step in self.fixture.timeline:
            if step_limit is not None and step.step > step_limit:
                break
            if step.command == "task.create":
                self._run_step(step)
                self._record_selection_snapshot(step)
            else:
                self._record_selection_snapshot(step)
                self._run_step(step)
        return ReplayResult(
            fixture=self.fixture,
            event_log=self.log,
            state=self.projector.state,
            selection_history=list(self.selection_history),
        )

    def rebuild_state(self) -> MaterializedState:
        rebuilt = EventProjector()
        return rebuilt.rebuild(self.log.as_list(), as_of=self.projector.state.last_event_at)

    def export_capsule(self, node_id: str) -> dict[str, Any]:
        task = self.projector.state.tasks[self.fixture.task_id]
        next_action = select_next_node(self.projector.state, task, self.projector.state.last_event_at or BASE_TIME)
        actions = []
        if next_action["node_id"] is not None:
            actions.append(next_action)
        return build_minimal_capsule(
            state=self.projector.state,
            task_id=self.fixture.task_id,
            node_id=node_id,
            candidate_next_actions=actions,
            generated_at=self.projector.state.last_event_at or BASE_TIME,
        )

    def _bootstrap_if_needed(self) -> None:
        if self._bootstrapped:
            return
        first_step = self.fixture.timeline[0] if self.fixture.timeline else None
        explicit_task_created = bool(first_step and "task.created" in first_step.events)
        if not explicit_task_created:
            self._emit_event(0, "task.created", self._build_task_created_payload(), self.fixture.root_node_id, "bootstrap")
        self._bootstrapped = True

    def _build_task_created_payload(self) -> dict[str, Any]:
        path = self.fixture.task_profile["task_path"]
        task = {
            "task_id": self.fixture.task_id,
            "objective": self.fixture.goal,
            "desired_delta": {"goal": self.fixture.goal},
            "evidence_of_done": {"proof_refs": self.fixture.terminal_expectation["proof"]},
            "task_type": path[-1] if path else "Observe",
            "risk_class": self.fixture.task_profile["default_risk_band"],
            "reversibility": {"mode": "bounded-or-none"},
            "attention_budget": self.fixture.task_profile["attention_budget_profile"],
            "constraints": {
                "source": "replay-fixture",
                "task_path": path,
            },
            "root_node_id": self.fixture.root_node_id,
            "principal_ref": "principal.user.primary",
            "resource_owner_ref": "owner.workspace.primary",
            "approver_ref": "principal.user.primary",
        }
        validate_against_schema(task, "task.schema.json")

        nodes = []
        for index, node in enumerate(self.fixture.nodes):
            payload = {
                "node_id": node.node_id,
                "task_id": self.fixture.task_id,
                "node_type": node.node_type,
                "objective": node.purpose,
                "desired_delta": {"purpose": node.purpose},
                "evidence_of_done": {"expected_terminal": node.expected_terminal},
                "risk_class": node.risk_band,
                "state": "created",
                "dependencies": [self.fixture.nodes[index - 1].node_id] if index > 0 else [],
                "required_capabilities": [f"structured.{node.node_type}"],
                "principal_ref": "principal.user.primary",
                "resource_owner_ref": "owner.workspace.primary",
                "grant_refs": [],
                "artifact_refs": [],
                "version": 1,
                "created_at": BASE_TIME.isoformat(),
                "updated_at": BASE_TIME.isoformat(),
            }
            validate_against_schema(payload, "task-node.schema.json")
            nodes.append(payload)
        return {"task": task, "nodes": nodes}

    def _record_selection_snapshot(self, step: ReplayStep) -> None:
        task = self.projector.state.tasks[self.fixture.task_id]
        selection = select_next_node(self.projector.state, task, self._time_for_step(step.step, 0))
        selection["before_step"] = step.step
        selection["expected_node"] = step.node_id
        self.selection_history.append(selection)

    def _run_step(self, step: ReplayStep) -> None:
        if step.command == "task.create":
            if self.fixture.task_id not in self.projector.state.tasks:
                self._emit_event(step.step, "task.created", self._build_task_created_payload(), step.node_id, "taskcreate")
            self._ensure_node_ready(step.step, step.node_id, explicit_transition_present=True)
        else:
            explicit_ready = any(token.startswith("node.state_changed(created->ready)") for token in step.events)
            self._ensure_node_ready(step.step, step.node_id, explicit_transition_present=explicit_ready)

        for token_index, token in enumerate(step.events, start=1):
            self._emit_token(step, token, token_index)

    def _ensure_node_ready(self, step_number: int, node_id: str, *, explicit_transition_present: bool) -> None:
        node = self.projector.state.nodes.get(node_id)
        if node is None or node["state"] != "created" or explicit_transition_present:
            return
        payload = {
            "task_id": self.fixture.task_id,
            "node_id": node_id,
            "from_state": "created",
            "to_state": "ready",
            "changed_at": self._time_for_step(step_number, 0).isoformat(),
        }
        self._emit_event(step_number, "node.state_changed", payload, node_id, "synthetic-ready")

    def _emit_token(self, step: ReplayStep, token: str, token_index: int) -> None:
        if token == "task.created":
            self._emit_event(step.step, token, self._build_task_created_payload(), step.node_id, f"{token_index}-task")
            return

        if token.startswith("node.state_changed("):
            transition = token.removeprefix("node.state_changed(").removesuffix(")")
            from_state, to_state = transition.split("->", maxsplit=1)
            payload = {
                "task_id": self.fixture.task_id,
                "node_id": step.node_id,
                "from_state": from_state,
                "to_state": to_state,
                "changed_at": self._time_for_step(step.step, token_index).isoformat(),
            }
            self._emit_event(step.step, "node.state_changed", payload, step.node_id, f"{token_index}-state")
            return

        if token == "grant.issued":
            self._emit_event(step.step, token, {"grant": self._build_grant(step, token_index)}, step.node_id, f"{token_index}-grant")
            return

        if token == "approval.recorded":
            self._ensure_node_awaiting_approval(step.step, step.node_id)
            self._emit_event(step.step, token, {"approval": self._build_approval(step, token_index)}, step.node_id, f"{token_index}-approval")
            self._restore_node_ready_after_approval(step.step, step.node_id)
            return

        if token == "action.dispatched":
            action_spec = self._build_action_spec(step, token_index)
            occurred_at = self._time_for_step(step.step, token_index)
            ensure_dispatch_allowed(self.projector.state.grants, self.fixture.task_id, step.node_id, occurred_at)
            payload = {
                "task_id": self.fixture.task_id,
                "node_id": step.node_id,
                "action_id": action_spec["action_id"],
                "required_capability": action_spec["required_capability"],
            }
            self._emit_event(step.step, token, payload, step.node_id, f"{token_index}-dispatch")
            return

        if token == "receipt.recorded":
            receipt = self._build_receipt(step, token_index)
            self._emit_event(step.step, token, {"receipt": receipt}, step.node_id, f"{token_index}-receipt")
            return

        if token == "verification.recorded":
            for fact in self._build_candidate_facts(step, token_index):
                self._emit_event(step.step, "fact.observed", {"fact": fact}, step.node_id, f"{token_index}-fact-{fact['fact_id']}")
            verification = self._build_verification(step, token_index)
            self._emit_event(step.step, token, {"verification": verification}, step.node_id, f"{token_index}-verify")
            return

        if token == "recovery.recorded":
            recovery = self._build_recovery(step, token_index)
            self._emit_event(step.step, token, {"recovery": recovery}, step.node_id, f"{token_index}-recovery")
            return

        raise ValueError(f"unsupported replay token: {token}")

    def _build_approval(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        occurred_at = self._time_for_step(step.step, token_index)
        node = self.projector.state.nodes[step.node_id]
        task = self.projector.state.tasks[self.fixture.task_id]
        selection = select_next_node(self.projector.state, task, occurred_at) if self.selection_history else None
        return {
            "approval_id": f"approval_{self.fixture.replay_id}_{step.node_id}_{step.step}",
            "task_id": self.fixture.task_id,
            "node_id": step.node_id,
            "approver_id": "principal.user.primary",
            "approved_at": occurred_at.isoformat(),
            "status": "approved",
            "risk_class": node["risk_class"],
            "approval_kind": "explicit",
            "selection_ref": selection["node_id"] if selection else None,
            "summary": step.notes or step.command,
        }

    def _ensure_node_awaiting_approval(self, step_number: int, node_id: str) -> None:
        node = self.projector.state.nodes[node_id]
        if node["state"] != "ready":
            return
        payload = {
            "task_id": self.fixture.task_id,
            "node_id": node_id,
            "from_state": "ready",
            "to_state": "awaiting_approval",
            "changed_at": self._time_for_step(step_number, 0).isoformat(),
        }
        self._emit_event(step_number, "node.state_changed", payload, node_id, "awaiting-approval")

    def _restore_node_ready_after_approval(self, step_number: int, node_id: str) -> None:
        node = self.projector.state.nodes[node_id]
        if node["state"] != "awaiting_approval":
            return
        payload = {
            "task_id": self.fixture.task_id,
            "node_id": node_id,
            "from_state": "awaiting_approval",
            "to_state": "ready",
            "changed_at": self._time_for_step(step_number, 1).isoformat(),
        }
        self._emit_event(step_number, "node.state_changed", payload, node_id, "approval-restored-ready")

    def _build_grant(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        occurred_at = self._time_for_step(step.step, token_index)
        node = self.projector.state.nodes[step.node_id]
        task = self.projector.state.tasks[self.fixture.task_id]
        ensure_approval_for_grant(self.projector.state.approvals, node=node, task=task)
        payload = {
            "grant_id": f"grant_{self.fixture.replay_id}_{step.node_id}_{step.step}",
            "task_id": self.fixture.task_id,
            "node_id": step.node_id,
            "who": "executor.local.structured",
            "what": node["required_capabilities"][0],
            "where": {"node_id": step.node_id},
            "when": {
                "not_before": occurred_at.isoformat(),
                "not_after": (occurred_at + timedelta(minutes=10)).isoformat(),
            },
            "budget": {"max_retries": 1, "max_minutes": 10},
            "why": step.command,
            "approval_ref": f"approval_{self.fixture.replay_id}_{step.node_id}",
            "postcondition_ref": f"postcondition_{self.fixture.replay_id}_{step.node_id}",
            "principal_ref": "principal.user.primary",
            "resource_owner_ref": "owner.workspace.primary",
            "approver_ref": "principal.user.primary",
            "status": "active",
            "issued_at": occurred_at.isoformat(),
            "expires_at": (occurred_at + timedelta(minutes=10)).isoformat(),
        }
        validate_against_schema(payload, "capability-grant.schema.json")
        return payload

    def _build_action_spec(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        action_id = f"action_{self.fixture.replay_id}_{step.node_id}_{step.step}"
        occurred_at = self._time_for_step(step.step, token_index)
        node = self.projector.state.nodes[step.node_id]
        action_spec = build_action_spec(task_id=self.fixture.task_id, node=node, action_id=action_id, occurred_at=occurred_at)
        if node["risk_class"] == "R3" or node["node_type"].startswith("commit_"):
            action_spec["compensation_policy_ref"] = f"compensate_{self.fixture.replay_id}_{step.node_id}"
            action_spec["side_effect_class"] = "irreversible_external_send"
        elif node["risk_class"] == "R2":
            action_spec["compensation_policy_ref"] = f"rollback_{self.fixture.replay_id}_{step.node_id}"
            action_spec["side_effect_class"] = "bounded_external_modify"
        validate_against_schema(action_spec, "action-spec.schema.json")
        self._action_specs[step.node_id] = action_spec
        return action_spec

    def _build_receipt(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        occurred_at = self._time_for_step(step.step, token_index)
        action_spec = self._action_specs.get(step.node_id)
        if action_spec is None:
            action_spec = self._build_action_spec(step, token_index)
        grant = ensure_dispatch_allowed(self.projector.state.grants, self.fixture.task_id, step.node_id, occurred_at)
        artifacts = [
            f"artifact_{step.node_id}_{step.step}_primary",
            f"artifact_{step.node_id}_{step.step}_support",
        ]
        return build_receipt(
            action_spec=action_spec,
            grant=grant,
            artifact_refs=artifacts,
            occurred_at=occurred_at,
            executor_id="executor.local.structured",
        )

    def _build_candidate_facts(self, step: ReplayStep, token_index: int) -> list[dict[str, Any]]:
        occurred_at = self._time_for_step(step.step, token_index)
        node = self._node_by_id(step.node_id)
        if node.node_type == "synthesize_facts":
            facts = []
            for variant in ("a", "b"):
                fact = {
                    "fact_id": f"fact_{step.node_id}_{variant}",
                    "fact_type": "derived",
                    "statement": f"Candidate vendor claim {variant} extracted for {step.node_id}",
                    "provenance": {"kind": "replay-extraction", "step": step.step},
                    "observed_at": occurred_at.isoformat(),
                    "valid_until": (occurred_at + timedelta(days=1)).isoformat(),
                    "attestation_level": "candidate_extraction",
                    "confidence": 0.6,
                    "scope": {"node_id": step.node_id},
                    "evidence_refs": [f"artifact_{step.node_id}_{step.step}_support"],
                    "status": "candidate",
                    "version": 1,
                    "conflict_set": ["conflict.vendor.claims"],
                }
                validate_against_schema(fact, "fact.schema.json")
                facts.append(fact)
            return facts

        if node.node_type == "observe_sensitive_record":
            fact = {
                "fact_id": f"fact_{step.node_id}_baseline",
                "fact_type": "observed",
                "statement": f"Baseline CRM snapshot captured for {step.node_id}",
                "provenance": {"kind": "replay-observation", "step": step.step},
                "observed_at": occurred_at.isoformat(),
                "valid_until": (occurred_at + timedelta(hours=2)).isoformat(),
                "attestation_level": "receipt_pending_verification",
                "confidence": 0.8,
                "scope": {"node_id": step.node_id},
                "evidence_refs": [f"artifact_{step.node_id}_{step.step}_primary"],
                "status": "candidate",
                "version": 1,
                "conflict_set": [],
            }
            validate_against_schema(fact, "fact.schema.json")
            return [fact]

        return []

    def _build_verification(self, step: ReplayStep, token_index: int) -> dict[str, object]:
        occurred_at = self._time_for_step(step.step, token_index)
        node = self._node_by_id(step.node_id)
        receipt_refs = list(self.projector.state.node_receipts.get(step.node_id, []))
        supporting_evidence: list[str] = list(receipt_refs)
        if receipt_refs:
            supporting_evidence.extend(self.projector.state.receipts[receipt_refs[-1]]["artifact_refs"])
        target_state = node.expected_terminal if not self._has_explicit_terminal_transition(step) else self.projector.state.nodes[step.node_id]["state"]
        fact_promotions = [f"fact_{step.node_id}_baseline"] if node.node_type == "observe_sensitive_record" else None
        return build_verification_result(
            task_id=self.fixture.task_id,
            node_id=step.node_id,
            receipt_refs=receipt_refs,
            supporting_evidence=supporting_evidence,
            occurred_at=occurred_at,
            verifier_id="verifier.replay.core",
            target_state=target_state,
            fact_promotions=fact_promotions,
            recommended_recovery_action=self.fixture.terminal_expectation.get("recovery_mode"),
        )

    def _build_recovery(self, step: ReplayStep, token_index: int) -> dict[str, Any]:
        occurred_at = self._time_for_step(step.step, token_index)
        action_spec = self._action_specs[step.node_id]
        return {
            "recovery_id": f"recovery_{self.fixture.replay_id}_{step.node_id}_{step.step}",
            "task_id": self.fixture.task_id,
            "node_id": step.node_id,
            "action": "compensate" if action_spec.get("side_effect_class") == "irreversible_external_send" else "rollback",
            "recorded_at": occurred_at.isoformat(),
            "policy_ref": action_spec.get("compensation_policy_ref"),
            "status": "armed",
        }

    def _has_explicit_terminal_transition(self, step: ReplayStep) -> bool:
        return any(token.startswith("node.state_changed(") and "->completed" in token for token in step.events)

    def _emit_event(self, step_number: int, event_type: str, payload: dict[str, Any], node_id: str, suffix: str) -> None:
        event = {
            "event_id": f"{self.fixture.replay_id}.{step_number}.{suffix}",
            "event_type": event_type,
            "actor_id": "replay.runner",
            "occurred_at": self._time_for_step(step_number, self._current_index + 1).isoformat(),
            "payload": payload,
            "task_id": self.fixture.task_id,
            "node_id": node_id,
            "trace_ref": self.fixture.replay_id,
        }
        if self._current_index > 0:
            event["causation_ref"] = self.log.as_list()[-1]["event_id"]
            event["correlation_ref"] = self.fixture.replay_id
        if self.log.append(event):
            self.projector.apply(event)
            self._current_index += 1

    def _time_for_step(self, step_number: int, offset: int) -> datetime:
        return BASE_TIME + timedelta(minutes=step_number * 2, seconds=offset)

    def _node_by_id(self, node_id: str):
        for node in self.fixture.nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)


def run_replay_file(path: Path, *, step_limit: int | None = None) -> ReplayResult:
    runner = ReplayRunner(load_replay(path))
    return runner.run(step_limit=step_limit)

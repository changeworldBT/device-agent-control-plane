from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from control.grants.guards import ensure_dispatch_allowed
from domain.facts.semantics import materialize_fact_status, parse_timestamp
from domain.tasks.guards import ensure_transition_allowed


@dataclass
class MaterializedState:
    tasks: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_states: dict[str, str] = field(default_factory=dict)
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    facts: dict[str, dict[str, Any]] = field(default_factory=dict)
    grants: dict[str, dict[str, Any]] = field(default_factory=dict)
    approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    verifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    recoveries: dict[str, dict[str, Any]] = field(default_factory=dict)
    artifacts: set[str] = field(default_factory=set)
    node_receipts: dict[str, list[str]] = field(default_factory=dict)
    node_verifications: dict[str, list[str]] = field(default_factory=dict)
    last_event_at: datetime | None = None

    def has_successful_verification(self, node_id: str) -> bool:
        verification_ids = self.node_verifications.get(node_id, [])
        for verification_id in reversed(verification_ids):
            if self.verifications[verification_id]["result"] == "verified_success":
                return True
        return False

    def current_task_terminal(self, task_id: str) -> str:
        return self.task_states.get(task_id, "created")


class EventProjector:
    def __init__(self) -> None:
        self.state = MaterializedState()

    def rebuild(self, events: list[dict[str, Any]], *, as_of: datetime | None = None) -> MaterializedState:
        self.state = MaterializedState()
        for event in events:
            self.apply(event)
        if as_of is not None:
            self._refresh_fact_statuses(as_of)
        return self.state

    def apply(self, event: dict[str, Any]) -> MaterializedState:
        event_type = event["event_type"]
        payload = event["payload"]
        occurred_at = parse_timestamp(event["occurred_at"])

        if event_type == "task.created":
            self._apply_task_created(payload)
        elif event_type == "node.state_changed":
            self._apply_node_state_change(payload)
        elif event_type == "grant.issued":
            self._apply_grant_issued(payload)
        elif event_type == "approval.recorded":
            self._apply_approval_recorded(payload)
        elif event_type == "action.dispatched":
            self._apply_action_dispatched(payload, occurred_at)
        elif event_type == "receipt.recorded":
            self._apply_receipt_recorded(payload, occurred_at)
        elif event_type == "verification.recorded":
            self._apply_verification_recorded(payload, occurred_at)
        elif event_type == "recovery.recorded":
            self._apply_recovery_recorded(payload)
        elif event_type == "fact.observed":
            self._apply_fact_observed(payload)
        else:
            raise ValueError(f"unsupported event type: {event_type}")

        self.state.last_event_at = occurred_at
        self._refresh_fact_statuses(occurred_at)
        self._recompute_task_states()
        return self.state

    def _apply_task_created(self, payload: dict[str, Any]) -> None:
        task = dict(payload["task"])
        task_id = task["task_id"]
        self.state.tasks[task_id] = task
        self.state.task_states[task_id] = "created"
        for node in payload["nodes"]:
            self.state.nodes[node["node_id"]] = dict(node)

    def _apply_node_state_change(self, payload: dict[str, Any]) -> None:
        node = self.state.nodes[payload["node_id"]]
        ensure_transition_allowed(
            node["state"],
            payload["to_state"],
            has_verification=self.state.has_successful_verification(node["node_id"]),
        )
        node["state"] = payload["to_state"]
        node["version"] += 1
        node["updated_at"] = payload["changed_at"]

    def _apply_grant_issued(self, payload: dict[str, Any]) -> None:
        grant = dict(payload["grant"])
        self.state.grants[grant["grant_id"]] = grant
        node = self.state.nodes[grant["node_id"]]
        node.setdefault("grant_refs", []).append(grant["grant_id"])

    def _apply_approval_recorded(self, payload: dict[str, Any]) -> None:
        approval = dict(payload["approval"])
        self.state.approvals[approval["approval_id"]] = approval

    def _apply_action_dispatched(self, payload: dict[str, Any], occurred_at: datetime) -> None:
        ensure_dispatch_allowed(self.state.grants, payload["task_id"], payload["node_id"], occurred_at)
        node = self.state.nodes[payload["node_id"]]
        ensure_transition_allowed(node["state"], "running", has_verification=False)
        node["state"] = "running"
        node["version"] += 1
        node["updated_at"] = occurred_at.isoformat()

    def _apply_receipt_recorded(self, payload: dict[str, Any], occurred_at: datetime) -> None:
        receipt = dict(payload["receipt"])
        self.state.receipts[receipt["receipt_id"]] = receipt
        self.state.node_receipts.setdefault(receipt["node_id"], []).append(receipt["receipt_id"])
        self.state.artifacts.update(receipt["artifact_refs"])
        node = self.state.nodes[receipt["node_id"]]
        ensure_transition_allowed(node["state"], "verifying", has_verification=False)
        node["state"] = "verifying"
        node["version"] += 1
        node["updated_at"] = occurred_at.isoformat()
        node.setdefault("artifact_refs", []).extend(receipt["artifact_refs"])

    def _apply_verification_recorded(self, payload: dict[str, Any], occurred_at: datetime) -> None:
        verification = dict(payload["verification"])
        self.state.verifications[verification["verification_id"]] = verification
        self.state.node_verifications.setdefault(verification["node_id"], []).append(verification["verification_id"])
        transition = verification["state_transition"]
        for fact_id in transition.get("fact_promotions", []):
            if fact_id in self.state.facts:
                self.state.facts[fact_id]["status"] = "verified"
                self.state.facts[fact_id]["verified_at"] = verification["verified_at"]
                self.state.facts[fact_id]["version"] += 1
        target_state = transition.get("to")
        if target_state:
            node = self.state.nodes[verification["node_id"]]
            ensure_transition_allowed(node["state"], target_state, has_verification=True)
            node["state"] = target_state
            node["version"] += 1
            node["updated_at"] = occurred_at.isoformat()

    def _apply_recovery_recorded(self, payload: dict[str, Any]) -> None:
        recovery = dict(payload["recovery"])
        self.state.recoveries[recovery["recovery_id"]] = recovery

    def _apply_fact_observed(self, payload: dict[str, Any]) -> None:
        fact = dict(payload["fact"])
        existing = self.state.facts.get(fact["fact_id"])
        if existing is not None and existing["version"] > fact["version"]:
            return
        self.state.facts[fact["fact_id"]] = fact

    def _refresh_fact_statuses(self, as_of: datetime) -> None:
        for fact in self.state.facts.values():
            fact["status"] = materialize_fact_status(fact, as_of)

    def _recompute_task_states(self) -> None:
        for task_id in self.state.tasks:
            task_nodes = [node for node in self.state.nodes.values() if node["task_id"] == task_id]
            if not task_nodes:
                self.state.task_states[task_id] = "created"
                continue
            node_states = {node["state"] for node in task_nodes}
            if node_states == {"completed"}:
                self.state.task_states[task_id] = "completed"
            elif "failed" in node_states:
                self.state.task_states[task_id] = "failed"
            elif "running" in node_states or "verifying" in node_states:
                self.state.task_states[task_id] = "running"
            elif "awaiting_approval" in node_states:
                self.state.task_states[task_id] = "awaiting_approval"
            elif "blocked" in node_states:
                self.state.task_states[task_id] = "blocked"
            elif "ready" in node_states:
                self.state.task_states[task_id] = "ready"
            else:
                self.state.task_states[task_id] = "created"

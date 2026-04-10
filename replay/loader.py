from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from replay.schema_support import EXAMPLE_DIR, load_json, validate_against_schema


@dataclass(frozen=True)
class ReplayStep:
    step: int
    node_id: str
    command: str
    events: tuple[str, ...]
    notes: str | None
    invariant_refs: tuple[str, ...]
    policy_refs: tuple[str, ...]


@dataclass(frozen=True)
class ReplayNode:
    node_id: str
    node_type: str
    purpose: str
    risk_band: str
    expected_terminal: str


@dataclass(frozen=True)
class ReplayFixture:
    replay_id: str
    title: str
    goal: str
    task_profile: dict[str, Any]
    nodes: tuple[ReplayNode, ...]
    timeline: tuple[ReplayStep, ...]
    invariants_exercised: tuple[str, ...]
    policy_surfaces: tuple[str, ...]
    terminal_expectation: dict[str, Any]

    @property
    def task_id(self) -> str:
        return f"task_{self.replay_id}"

    @property
    def root_node_id(self) -> str:
        return self.nodes[0].node_id


def _to_step(raw: dict[str, Any]) -> ReplayStep:
    return ReplayStep(
        step=raw["step"],
        node_id=raw["node_id"],
        command=raw["command"],
        events=tuple(raw["events"]),
        notes=raw.get("notes"),
        invariant_refs=tuple(raw.get("invariant_refs", [])),
        policy_refs=tuple(raw.get("policy_refs", [])),
    )


def _to_node(raw: dict[str, Any]) -> ReplayNode:
    return ReplayNode(
        node_id=raw["node_id"],
        node_type=raw["node_type"],
        purpose=raw["purpose"],
        risk_band=raw["risk_band"],
        expected_terminal=raw["expected_terminal"],
    )


def load_replay(path: Path) -> ReplayFixture:
    payload = load_json(path)
    validate_against_schema(payload, "task-replay.schema.json")
    timeline = sorted((_to_step(item) for item in payload["timeline"]), key=lambda step: step.step)
    nodes = tuple(_to_node(item) for item in payload["nodes"])
    return ReplayFixture(
        replay_id=payload["replay_id"],
        title=payload["title"],
        goal=payload["goal"],
        task_profile=payload["task_profile"],
        nodes=nodes,
        timeline=tuple(timeline),
        invariants_exercised=tuple(payload["invariants_exercised"]),
        policy_surfaces=tuple(payload["policy_surfaces"]),
        terminal_expectation=payload["terminal_expectation"],
    )


def load_builtin_replay(file_name: str) -> ReplayFixture:
    return load_replay(EXAMPLE_DIR / "flows" / file_name)

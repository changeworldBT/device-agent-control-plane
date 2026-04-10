from __future__ import annotations

from datetime import datetime
from typing import Any

from control.approvals.guards import approval_required, has_active_approval
from domain.tasks.guards import is_terminal


RISK_COST = {
    "R0": 0.0,
    "R1": 1.0,
    "R2": 3.0,
    "R3": 6.0,
}

ATTENTION_COST = {
    "R0": 0,
    "R1": 0,
    "R2": 1,
    "R3": 2,
}

SURFACE_COST = {
    "Observe": 0.0,
    "Synthesize": 0.5,
    "Prepare": 1.0,
    "Operate": 2.0,
    "Commit": 4.0,
    "Monitor": 1.0,
}


def _surface_from_node_type(node_type: str) -> str:
    if node_type.startswith("observe_"):
        return "Observe"
    if node_type.startswith("synthesize_"):
        return "Synthesize"
    if node_type.startswith("prepare_"):
        return "Prepare"
    if node_type.startswith("operate_"):
        return "Operate"
    if node_type.startswith("commit_"):
        return "Commit"
    return "Prepare"


def composite_risk_score(node: dict[str, Any], task: dict[str, Any], state: Any) -> tuple[float, dict[str, Any]]:
    action_surface = SURFACE_COST.get(_surface_from_node_type(node["node_type"]), 1.0)

    node_type = node["node_type"]
    target_sensitivity = 1.5 if any(token in node_type for token in ("sensitive", "crm", "commit")) else 0.5
    context_cost = 1.0 if task.get("attention_budget", {}).get("must_confirm_before_commit") else 0.0
    sequence_cost = 0.5 * sum(1 for peer in state.nodes.values() if peer["task_id"] == task["task_id"] and peer["state"] == "completed")
    base_cost = RISK_COST[node["risk_class"]]
    total = base_cost + action_surface + target_sensitivity + context_cost + sequence_cost
    return total, {
        "base_band_cost": base_cost,
        "action_surface_cost": action_surface,
        "target_sensitivity_cost": target_sensitivity,
        "context_cost": context_cost,
        "sequence_cost": sequence_cost,
    }


def _dependencies_satisfied(node: dict[str, Any], state: Any) -> bool:
    for dep in node.get("dependencies", []):
        dep_node = state.nodes[dep]
        if dep_node["state"] != "completed":
            return False
    return True


def _candidate_score(node: dict[str, Any], state: Any, max_interruptions: int) -> tuple[float, dict[str, Any]]:
    interruption_cost = ATTENTION_COST.get(node["risk_class"], 1)
    if interruption_cost > max_interruptions:
        raise ValueError("attention budget exceeded")

    task = state.tasks[node["task_id"]]
    composite_score, composite_parts = composite_risk_score(node, task, state)
    verified_facts = sum(1 for fact in state.facts.values() if fact["status"] == "verified")
    verification_bonus = min(verified_facts * 0.1, 0.5)
    freshness_bonus = 1.0
    dependency_penalty = 0.0 if _dependencies_satisfied(node, state) else 10.0
    ready_bonus = 0.5 if node["state"] == "ready" else 0.0
    approval_needed = approval_required(node=node, task=task, composite_risk_score=composite_score)
    approval_present = has_active_approval(state.approvals, task_id=task["task_id"], node_id=node["node_id"])
    if approval_needed and not approval_present:
        raise ValueError("approval required")

    score = 5.0 + ready_bonus + freshness_bonus + verification_bonus - composite_score - dependency_penalty
    return score, {
        "risk_cost": composite_score,
        "interruption_cost": interruption_cost,
        "freshness_bonus": freshness_bonus,
        "verification_bonus": verification_bonus,
        "dependency_penalty": dependency_penalty,
        "ready_bonus": ready_bonus,
        "approval_required": approval_needed,
        "approval_present": approval_present,
        "composite_risk": composite_parts,
    }


def select_next_node(state: Any, task: dict[str, Any], at_time: datetime) -> dict[str, Any]:
    del at_time
    max_interruptions = int(task["attention_budget"].get("max_interruptions", 0))
    candidates = []
    for node in state.nodes.values():
        if node["task_id"] != task["task_id"]:
            continue
        if is_terminal(node["state"]):
            continue
        if node["state"] not in {"created", "ready"}:
            continue
        if not _dependencies_satisfied(node, state):
            continue
        try:
            score, parts = _candidate_score(node, state, max_interruptions)
        except ValueError:
            continue
        candidates.append(
            {
                "node_id": node["node_id"],
                "score": score,
                "path_kind": "structured",
                "rationale": parts,
            }
        )

    if not candidates:
        return {
            "node_id": None,
            "path_kind": "ask",
            "rationale": {
                "reason": "no eligible candidate within attention budget and dependency constraints",
                "max_interruptions": max_interruptions,
            },
        }

    candidates.sort(key=lambda item: (-item["score"], item["node_id"]))
    chosen = candidates[0]
    chosen["max_interruptions"] = max_interruptions
    return chosen

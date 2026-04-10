from __future__ import annotations

from typing import Any


def approval_required(*, node: dict[str, Any], task: dict[str, Any], composite_risk_score: float | None = None) -> bool:
    if node["risk_class"] == "R3":
        return True
    if node["risk_class"] == "R2":
        return True
    if node["node_type"].startswith("commit_"):
        return True
    if task.get("attention_budget", {}).get("must_confirm_before_commit") and node["risk_class"] in {"R2", "R3"}:
        return True
    if composite_risk_score is not None and composite_risk_score >= 4.0:
        return True
    return False


def has_active_approval(approvals: dict[str, dict[str, Any]], *, task_id: str, node_id: str) -> bool:
    for approval in approvals.values():
        if approval["task_id"] != task_id or approval["node_id"] != node_id:
            continue
        if approval["status"] == "approved":
            return True
    return False


def ensure_approval_for_grant(
    approvals: dict[str, dict[str, Any]],
    *,
    node: dict[str, Any],
    task: dict[str, Any],
    composite_risk_score: float | None = None,
) -> None:
    if not approval_required(node=node, task=task, composite_risk_score=composite_risk_score):
        return
    if has_active_approval(approvals, task_id=task["task_id"], node_id=node["node_id"]):
        return
    raise ValueError(f"grant denied: approval required for task={task['task_id']} node={node['node_id']}")

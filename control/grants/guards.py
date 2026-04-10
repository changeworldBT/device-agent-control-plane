from __future__ import annotations

from datetime import datetime
from typing import Any

from domain.facts.semantics import parse_timestamp


def is_grant_active(grant: dict[str, Any], at_time: datetime) -> bool:
    if grant["status"] not in {"issued", "active"}:
        return False
    issued_at = parse_timestamp(grant["issued_at"])
    expires_at = parse_timestamp(grant["expires_at"])
    return issued_at <= at_time <= expires_at


def find_active_grant(grants: dict[str, dict[str, Any]], task_id: str, node_id: str, at_time: datetime) -> dict[str, Any] | None:
    matches = []
    for grant in grants.values():
        if grant["task_id"] != task_id or grant["node_id"] != node_id:
            continue
        if is_grant_active(grant, at_time):
            matches.append(grant)
    if not matches:
        return None
    matches.sort(key=lambda item: item["issued_at"], reverse=True)
    return matches[0]


def ensure_dispatch_allowed(grants: dict[str, dict[str, Any]], task_id: str, node_id: str, at_time: datetime) -> dict[str, Any]:
    grant = find_active_grant(grants, task_id, node_id, at_time)
    if grant is None:
        raise ValueError(f"dispatch denied: no active grant for task={task_id} node={node_id}")
    return grant

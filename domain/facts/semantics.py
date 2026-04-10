from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any


def parse_timestamp(raw: str) -> datetime:
    return datetime.fromisoformat(raw)


def effective_valid_until(fact: dict[str, Any]) -> datetime | None:
    if fact.get("valid_until"):
        return parse_timestamp(fact["valid_until"])
    ttl = fact.get("ttl")
    if ttl is None:
        return None
    return parse_timestamp(fact["observed_at"]) + timedelta(seconds=int(ttl))


def is_fact_expired(fact: dict[str, Any], as_of: datetime) -> bool:
    valid_until = effective_valid_until(fact)
    return valid_until is not None and as_of >= valid_until


def materialize_fact_status(fact: dict[str, Any], as_of: datetime) -> str:
    current = fact["status"]
    if current == "revoked":
        return current
    if is_fact_expired(fact, as_of):
        return "stale"
    return current

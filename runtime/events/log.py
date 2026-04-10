from __future__ import annotations

from typing import Any

from replay.schema_support import validate_against_schema


class EventLog:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._seen_event_ids: set[str] = set()

    def append(self, event: dict[str, Any]) -> bool:
        validate_against_schema(event, "event-envelope.schema.json")
        event_id = event["event_id"]
        if event_id in self._seen_event_ids:
            return False
        self._seen_event_ids.add(event_id)
        self._events.append(event)
        return True

    def extend(self, events: list[dict[str, Any]]) -> int:
        inserted = 0
        for event in events:
            if self.append(event):
                inserted += 1
        return inserted

    def as_list(self) -> list[dict[str, Any]]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

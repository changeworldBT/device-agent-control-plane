from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from model.provider_config import ModelRoute


ROOT = Path(__file__).resolve().parent.parent
CHAT_SESSION_DIR = ROOT / "runtime" / "chat_sessions"
SESSION_ID_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")
DEFAULT_SESSION_ID = "default"
MAX_SESSION_TURNS = 20


def normalize_session_id(session_id: object) -> str:
    rendered = SESSION_ID_PATTERN.sub("_", str(session_id or "").strip()).strip("_")
    return rendered or DEFAULT_SESSION_ID


def session_file_path(session_id: object, *, session_dir: Path = CHAT_SESSION_DIR) -> Path:
    return session_dir / f"{normalize_session_id(session_id)}.jsonl"


def load_chat_turns(
    session_id: object,
    *,
    session_dir: Path = CHAT_SESSION_DIR,
    limit: int = MAX_SESSION_TURNS,
) -> list[dict[str, Any]]:
    path = session_file_path(session_id, session_dir=session_dir)
    turns = _read_session_records(path)
    return turns[-limit:]


def append_chat_turn(
    session_id: object,
    *,
    route: ModelRoute,
    user_message: str,
    assistant_message: str,
    session_dir: Path = CHAT_SESSION_DIR,
) -> Path:
    path = session_file_path(session_id, session_dir=session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "session_id": normalize_session_id(session_id),
        "role": route.role,
        "mode": route.mode,
        "provider_kind": route.provider_kind,
        "route": _compact_route(route),
        "user": str(user_message),
        "assistant": str(assistant_message),
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False))
        handle.write("\n")
    return path


def chat_session_payload(
    session_id: object,
    *,
    session_dir: Path = CHAT_SESSION_DIR,
    limit: int = MAX_SESSION_TURNS,
) -> dict[str, Any]:
    normalized = normalize_session_id(session_id)
    turns = load_chat_turns(normalized, session_dir=session_dir, limit=limit)
    messages: list[dict[str, Any]] = []
    for turn in turns:
        user_message = str(turn.get("user") or "").strip()
        assistant_message = str(turn.get("assistant") or "").strip()
        timestamp = str(turn.get("timestamp") or "").strip() or None
        if user_message:
            messages.append({"sender": "user", "text": user_message, "timestamp": timestamp})
        if assistant_message:
            messages.append(
                {
                    "sender": "assistant",
                    "text": assistant_message,
                    "role": turn.get("role"),
                    "mode": turn.get("mode"),
                    "route": turn.get("route"),
                    "timestamp": timestamp,
                }
            )
    return {
        "session_id": normalized,
        "path": str(session_file_path(normalized, session_dir=session_dir)),
        "count": len(turns),
        "messages": messages,
    }


def list_chat_sessions(
    *,
    session_dir: Path = CHAT_SESSION_DIR,
) -> list[dict[str, Any]]:
    sessions: list[dict[str, Any]] = []
    for path in session_dir.glob("*.jsonl"):
        turns = _read_session_records(path)
        session_id = normalize_session_id(path.stem)
        last_turn = turns[-1] if turns else {}
        preview = str(last_turn.get("user") or last_turn.get("assistant") or "").strip()
        sessions.append(
            {
                "session_id": session_id,
                "path": str(path),
                "count": len(turns),
                "last_updated": str(last_turn.get("timestamp") or "").strip() or None,
                "provider_name": _route_value(last_turn, "provider_name"),
                "model": _route_value(last_turn, "model"),
                "preview": preview[:80] if preview else "",
            }
        )

    if not any(session["session_id"] == DEFAULT_SESSION_ID for session in sessions):
        sessions.append(
            {
                "session_id": DEFAULT_SESSION_ID,
                "path": str(session_file_path(DEFAULT_SESSION_ID, session_dir=session_dir)),
                "count": 0,
                "last_updated": None,
                "provider_name": None,
                "model": None,
                "preview": "",
            }
        )

    sessions.sort(
        key=lambda session: (
            str(session.get("last_updated") or ""),
            str(session["session_id"]),
        ),
        reverse=True,
    )
    sessions.sort(key=lambda session: session["session_id"] != DEFAULT_SESSION_ID)
    return sessions


def clear_chat_session(
    session_id: object,
    *,
    session_dir: Path = CHAT_SESSION_DIR,
) -> dict[str, Any]:
    normalized = normalize_session_id(session_id)
    path = session_file_path(normalized, session_dir=session_dir)
    removed = False
    if path.exists():
        path.unlink()
        removed = True
    return {
        "session_id": normalized,
        "path": str(path),
        "removed": removed,
    }


def _compact_route(route: ModelRoute) -> dict[str, Any]:
    return {
        "role": route.role,
        "agent_id": route.agent_id,
        "provider_name": route.provider_name,
        "provider_kind": route.provider_kind,
        "model": route.model,
        "mode": route.mode,
    }


def _read_session_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    turns: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            turns.append(payload)
    return turns


def _route_value(turn: Mapping[str, Any], key: str) -> str | None:
    route = turn.get("route")
    if not isinstance(route, Mapping):
        return None
    value = str(route.get(key) or "").strip()
    return value or None

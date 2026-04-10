from __future__ import annotations

import json
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class MockHttpCrmServer:
    def __init__(self, *, seed_dir: Path) -> None:
        self.seed_dir = seed_dir
        self._lock = threading.Lock()
        self._crm_record: dict[str, Any] = {}
        self._outbox: list[dict[str, Any]] = []
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.reset()

    @property
    def base_url(self) -> str:
        if self._httpd is None:
            raise RuntimeError("server not started")
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"

    def reset(self) -> None:
        with self._lock:
            self._crm_record = self._read_json(self.seed_dir / "crm_record.json")
            self._outbox = self._read_json(self.seed_dir / "outbox.json")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "crm_record": deepcopy(self._crm_record),
                "outbox": deepcopy(self._outbox),
            }

    def start(self) -> "MockHttpCrmServer":
        if self._httpd is not None:
            return self
        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._httpd.mock_owner = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="mock-http-crm", daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def __enter__(self) -> "MockHttpCrmServer":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _build_handler(self):
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if not self._authorized():
                    return
                if self.path == "/crm/record":
                    self._write_json(200, {"crm_record": owner.snapshot()["crm_record"]})
                    return
                if self.path == "/outbox":
                    self._write_json(200, {"outbox": owner.snapshot()["outbox"]})
                    return
                self._write_json(404, {"error": "not_found"})

            def do_PATCH(self) -> None:  # noqa: N802
                if not self._authorized():
                    return
                payload = self._read_json_body()
                if self.path == "/crm/status":
                    with owner._lock:
                        owner._crm_record["renewal_status"] = payload["renewal_status"]
                        owner._crm_record["history"].append(
                            {"at": payload["at"], "event": payload.get("event", "status updated")}
                        )
                        snapshot = deepcopy(owner._crm_record)
                    self._write_json(200, {"crm_record": snapshot})
                    return
                self._write_json(404, {"error": "not_found"})

            def do_POST(self) -> None:  # noqa: N802
                if not self._authorized():
                    return
                payload = self._read_json_body()
                if self.path == "/messages/send":
                    with owner._lock:
                        owner._outbox.append(payload)
                        owner._crm_record["renewal_status"] = "follow_up_sent"
                        owner._crm_record["last_follow_up_at"] = payload["sent_at"]
                        owner._crm_record["history"].append(
                            {"at": payload["sent_at"], "event": "follow-up email sent"}
                        )
                        response = {
                            "message": deepcopy(payload),
                            "crm_record": deepcopy(owner._crm_record),
                            "outbox_entries": len(owner._outbox),
                        }
                    self._write_json(200, response)
                    return
                if self.path == "/messages/correction":
                    with owner._lock:
                        owner._outbox.append(payload)
                        owner._crm_record["last_compensation_at"] = payload["sent_at"]
                        owner._crm_record["history"].append(
                            {"at": payload["sent_at"], "event": "compensation correction sent"}
                        )
                        response = {
                            "message": deepcopy(payload),
                            "crm_record": deepcopy(owner._crm_record),
                            "outbox_entries": len(owner._outbox),
                        }
                    self._write_json(200, response)
                    return
                if self.path == "/crm/restore-status":
                    with owner._lock:
                        owner._crm_record["renewal_status"] = payload["renewal_status"]
                        owner._crm_record["history"].append(
                            {"at": payload["restored_at"], "event": "status restored by compensation path"}
                        )
                        snapshot = deepcopy(owner._crm_record)
                    self._write_json(200, {"crm_record": snapshot})
                    return
                self._write_json(404, {"error": "not_found"})

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                return

            def _authorized(self) -> bool:
                grant_id = self.headers.get("X-Grant-Id")
                principal_ref = self.headers.get("X-Principal-Ref")
                if not grant_id or not principal_ref:
                    self._write_json(403, {"error": "missing_grant_context"})
                    return False
                return True

            def _read_json_body(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                return json.loads(raw.decode("utf-8"))

            def _write_json(self, status: int, payload: dict[str, Any]) -> None:
                raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        return Handler

    @staticmethod
    def _read_json(path: Path) -> Any:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

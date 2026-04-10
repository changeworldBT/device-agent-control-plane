from __future__ import annotations

import json
import mimetypes
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from compat.openclaw_migration import DEFAULT_OPENCLAW_CONFIG, DEFAULT_OPENCLAW_WORKSPACE, migrate_openclaw
from model.provider_config import resolve_model_route, validate_model_config


ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
EXAMPLE_CONFIG = ROOT / "config" / "model-providers.example.json"
LOCAL_CONFIG = ROOT / "config" / "model-providers.local.json"
ROLES = ("planner", "classifier", "summarizer", "verifier")


def active_config_path() -> Path:
    return LOCAL_CONFIG if LOCAL_CONFIG.exists() else EXAMPLE_CONFIG


def read_config() -> tuple[dict[str, Any], str, Path]:
    path = active_config_path()
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_model_config(config)
    source = "local" if path == LOCAL_CONFIG else "example"
    return config, source, path


def route_preview(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_model_config(config)
    return [resolve_model_route(config, role, env={}).as_redacted_dict() for role in ROLES]


def dashboard_payload() -> dict[str, Any]:
    config, source, path = read_config()
    return {
        "source": source,
        "path": str(path),
        "local_config_path": str(LOCAL_CONFIG),
        "config": config,
        "routes": route_preview(config),
    }


def save_local_config(config: Mapping[str, Any]) -> dict[str, Any]:
    validate_model_config(config)
    LOCAL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with LOCAL_CONFIG.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return dashboard_payload()


def make_handler() -> type[BaseHTTPRequestHandler]:
    class UiRequestHandler(BaseHTTPRequestHandler):
        server_version = "DeviceAgentUI/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/config":
                self._send_json(200, dashboard_payload())
                return
            if parsed.path == "/api/health":
                self._send_json(200, {"status": "ok"})
                return
            if parsed.path == "/api/openclaw/defaults":
                self._send_json(200, openclaw_defaults())
                return
            self._send_static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/config":
                self._handle_save_config()
                return
            if parsed.path == "/api/route-preview":
                try:
                    body = self._read_json_body()
                    config = body.get("config", body)
                    self._send_json(200, {"routes": route_preview(config)})
                except Exception as exc:
                    self._send_json(400, {"error": str(exc)})
                return
            if parsed.path == "/api/openclaw/preview":
                self._handle_openclaw_preview()
                return
            self._send_json(404, {"error": "not found"})

        def log_message(self, format: str, *args: object) -> None:
            return

        def _handle_save_config(self) -> None:
            try:
                body = self._read_json_body()
                config = body.get("config", body)
                self._send_json(200, save_local_config(config))
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _handle_openclaw_preview(self) -> None:
            try:
                body = self._read_json_body()
                config_path = Path(str(body.get("config_path") or DEFAULT_OPENCLAW_CONFIG)).expanduser()
                workspace_value = body.get("workspace_path")
                workspace_path = Path(str(workspace_value)).expanduser() if workspace_value else None
                report = migrate_openclaw(config_path=config_path, workspace_path=workspace_path)
                self._send_json(200, report)
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            if not raw:
                return {}
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_static(self, request_path: str) -> None:
            relative = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
            target = (UI_DIR / relative).resolve()
            ui_root = UI_DIR.resolve()
            try:
                target.relative_to(ui_root)
            except ValueError:
                self._send_json(404, {"error": "not found"})
                return
            if not target.is_file():
                self._send_json(404, {"error": "not found"})
                return

            mime_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
            data = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return UiRequestHandler


def openclaw_defaults() -> dict[str, str]:
    return {
        "config_path": str(DEFAULT_OPENCLAW_CONFIG),
        "workspace_path": str(DEFAULT_OPENCLAW_WORKSPACE),
    }


def serve_ui(*, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> int:
    address = (host, port)
    server = ThreadingHTTPServer(address, make_handler())
    url = f"http://{host}:{server.server_port}/"
    print(f"Device Agent UI: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDevice Agent UI stopped", flush=True)
    finally:
        server.server_close()
    return 0

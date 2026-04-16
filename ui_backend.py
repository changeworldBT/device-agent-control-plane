from __future__ import annotations

import json
import mimetypes
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from channels.bot_gateway import load_active_bot_config, list_channels, send_or_preview
from compat.openclaw_migration import DEFAULT_OPENCLAW_CONFIG, DEFAULT_OPENCLAW_WORKSPACE, migrate_openclaw
from local_env import DEFAULT_ENV_FILE, read_env_file, update_env_file
from model.chat_session import (
    DEFAULT_SESSION_ID,
    append_chat_turn,
    chat_session_payload,
    clear_chat_session,
    list_chat_sessions,
    load_chat_turns,
)
from model.live_client import ProviderRequestError, invoke_model_route
from model.provider_config import resolve_model_route, validate_model_config


ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
EXAMPLE_CONFIG = ROOT / "config" / "model-providers.example.json"
LOCAL_CONFIG = ROOT / "config" / "model-providers.local.json"
ROLES = ("planner", "classifier", "summarizer", "verifier")
RUNTIME_ENV_FIELDS = (
    ("DEVICE_AGENT_MODEL_MODE", "Model mode override"),
    ("DEVICE_AGENT_AGENT_MODE", "Agent mode override"),
    ("DEVICE_AGENT_MODEL_PROVIDER", "Provider override"),
    ("DEVICE_AGENT_AGENT", "Default agent override"),
    ("DEVICE_AGENT_AGENT_PLANNER", "Planner agent override"),
    ("DEVICE_AGENT_AGENT_CLASSIFIER", "Classifier agent override"),
    ("DEVICE_AGENT_AGENT_SUMMARIZER", "Summarizer agent override"),
    ("DEVICE_AGENT_AGENT_VERIFIER", "Verifier agent override"),
)
PROVIDER_ENV_FIELDS = (
    ("base_url_env", "Base URL"),
    ("api_key_env", "API key"),
    ("default_model_env", "Default model"),
)
AGENT_ENV_FIELDS = (("model_env", "Agent model"),)
BOT_ENV_FIELDS = (
    ("token_env", "Access token"),
    ("target_env", "Target"),
    ("webhook_url_env", "Webhook URL"),
    ("secret_env", "Secret"),
    ("phone_number_id_env", "Phone number ID"),
    ("api_version_env", "API version"),
    ("app_id_env", "App ID"),
)
ENV_CATEGORY_ORDER = {"runtime": 0, "provider": 1, "agent": 2, "channel": 3, "other": 4}
MODEL_LIST_TIMEOUT_SECONDS = 20


class ChatRequestError(ValueError):
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        super().__init__(str(self.payload.get("error") or "chat request failed"))


def active_config_path() -> Path:
    return LOCAL_CONFIG if LOCAL_CONFIG.exists() else EXAMPLE_CONFIG


def read_config() -> tuple[dict[str, Any], str, Path]:
    path = active_config_path()
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_model_config(config)
    source = "local" if path == LOCAL_CONFIG else "example"
    return config, source, path


def route_preview(config: Mapping[str, Any], *, env_values: Mapping[str, str] | None = None) -> list[dict[str, Any]]:
    validate_model_config(config)
    resolved_env = merged_env_values(env_values)
    return [resolve_model_route(config, role, env=resolved_env).as_redacted_dict() for role in ROLES]


def dashboard_payload() -> dict[str, Any]:
    config, source, path = read_config()
    return {
        "source": source,
        "path": str(path),
        "local_config_path": str(LOCAL_CONFIG),
        "config": config,
        "routes": route_preview(config),
    }


def bot_channels_payload() -> dict[str, Any]:
    config, source, path = load_active_bot_config()
    return {
        "source": source,
        "path": str(path),
        "config": config,
        "channels": list_channels(config),
    }


def fetch_provider_models(base_url: str, api_key: str | None = None) -> list[str]:
    endpoint = str(base_url or "").strip().rstrip("/")
    if not endpoint:
        raise ValueError("base_url is required")
    if not endpoint.startswith(("http://", "https://")):
        raise ValueError("base_url must start with http:// or https://")

    request = Request(
        f"{endpoint}/models",
        headers=_model_list_headers(api_key),
        method="GET",
    )
    with urlopen(request, timeout=MODEL_LIST_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = _extract_model_ids(payload)
    if not models:
        raise ValueError("model list response did not contain model ids")
    return models


def provider_models_payload(body: Mapping[str, Any]) -> dict[str, Any]:
    provider_id = str(body.get("provider_id") or "").strip()
    base_url = str(body.get("base_url") or "").strip()
    api_key = str(body.get("api_key") or "").strip()
    if provider_id and (not base_url or not api_key):
        provider = _provider_by_id(provider_id)
        env_values = dict(read_env_file(DEFAULT_ENV_FILE))
        base_url = base_url or _env_lookup(provider.get("base_url_env"), env_values)
        api_key = api_key or _env_lookup(provider.get("api_key_env"), env_values)

    models = fetch_provider_models(base_url, api_key)
    return {
        "provider_id": provider_id or None,
        "base_url": base_url,
        "count": len(models),
        "models": models,
    }


def chat_payload(body: Mapping[str, Any]) -> dict[str, Any]:
    role = str(body.get("role") or ROLES[0]).strip()
    message = str(body.get("message") or "").strip()
    session_id = str(body.get("session_id") or DEFAULT_SESSION_ID).strip() or DEFAULT_SESSION_ID
    if not message:
        raise ValueError("message is required")

    supplied_config = body.get("config")
    if supplied_config is None:
        config, _, _ = read_config()
    elif isinstance(supplied_config, Mapping):
        config = dict(supplied_config)
        validate_model_config(config)
    else:
        raise ValueError("config must be a JSON object")

    env_values = merged_env_values(body.get("env_values"))
    route = resolve_model_route(config, role, env=env_values)
    turns = load_chat_turns(session_id)
    try:
        result = invoke_model_route(route, user_message=message, history=turns, env=env_values)
    except ProviderRequestError as exc:
        raise ChatRequestError(
            {
                **exc.as_payload(),
                "session_id": session_id,
                "provider_name": route.provider_name,
                "agent_id": route.agent_id,
                "model": route.model,
                "route": route.as_redacted_dict(),
            }
        ) from exc
    session_path = append_chat_turn(session_id, route=route, user_message=message, assistant_message=result["reply"])
    return {
        "session_id": session_id,
        "session_path": str(session_path),
        "reply": result["reply"],
        "mode": result["mode"],
        "provider_kind": result["provider_kind"],
        "provider_name": route.provider_name,
        "agent_id": route.agent_id,
        "model": route.model,
        "usage": result["usage"],
        "finish_reason": result["finish_reason"],
        "route": route.as_redacted_dict(),
    }


def chat_sessions_payload() -> dict[str, Any]:
    return {"sessions": list_chat_sessions()}


def clear_chat_session_payload(body: Mapping[str, Any]) -> dict[str, Any]:
    session_id = str(body.get("session_id") or DEFAULT_SESSION_ID).strip() or DEFAULT_SESSION_ID
    result = clear_chat_session(session_id)
    result["sessions"] = list_chat_sessions()
    return result


def env_values_payload(
    *,
    model_config: Mapping[str, Any] | None = None,
    bot_config: Mapping[str, Any] | None = None,
    env_values: Mapping[str, str] | None = None,
    env_path: Path = DEFAULT_ENV_FILE,
) -> dict[str, Any]:
    if model_config is None:
        model_config, model_source, model_path = read_config()
    else:
        model_source, model_path = "provided", Path()
    if bot_config is None:
        bot_config, bot_source, bot_path = load_active_bot_config()
    else:
        bot_source, bot_path = "provided", Path()

    file_values = dict(read_env_file(env_path) if env_values is None else env_values)
    fields = _collect_env_fields(model_config, bot_config, file_values)
    return {
        "path": str(env_path),
        "model_source": model_source,
        "model_path": str(model_path) if str(model_path) else None,
        "bot_source": bot_source,
        "bot_path": str(bot_path) if str(bot_path) else None,
        "fields": fields,
    }


def save_env_values(values: Mapping[str, Any]) -> dict[str, Any]:
    updated = update_env_file(values, DEFAULT_ENV_FILE)
    for key, value in values.items():
        os.environ[str(key).strip()] = "" if value is None else str(value).strip()
    return env_values_payload(env_values=updated)


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
            if parsed.path == "/api/bot-channels":
                self._send_json(200, bot_channels_payload())
                return
            if parsed.path == "/api/env":
                self._send_json(200, env_values_payload())
                return
            if parsed.path == "/api/chat/session":
                session_id = parse_qs(parsed.query).get("session_id", [DEFAULT_SESSION_ID])[0]
                self._send_json(200, chat_session_payload(session_id))
                return
            if parsed.path == "/api/chat/sessions":
                self._send_json(200, chat_sessions_payload())
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
                    env_values = body.get("env_values")
                    self._send_json(200, {"routes": route_preview(config, env_values=env_values)})
                except Exception as exc:
                    self._send_json(400, {"error": str(exc)})
                return
            if parsed.path == "/api/openclaw/preview":
                self._handle_openclaw_preview()
                return
            if parsed.path == "/api/bot-channels/preview":
                self._handle_bot_channel_preview()
                return
            if parsed.path == "/api/providers/models":
                self._handle_provider_models()
                return
            if parsed.path == "/api/env":
                self._handle_save_env_values()
                return
            if parsed.path == "/api/chat":
                self._handle_chat()
                return
            if parsed.path == "/api/chat/session/clear":
                self._handle_clear_chat_session()
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

        def _handle_bot_channel_preview(self) -> None:
            try:
                body = self._read_json_body()
                config, _, _ = load_active_bot_config()
                result = send_or_preview(
                    config,
                    text=str(body.get("text") or "Device Agent test message"),
                    channel_name=str(body.get("channel") or config["default_channel"]),
                    live=False,
                )
                self._send_json(200, result)
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _handle_save_env_values(self) -> None:
            try:
                body = self._read_json_body()
                values = body.get("values", body)
                if not isinstance(values, Mapping):
                    raise ValueError("values must be a JSON object")
                self._send_json(200, save_env_values(values))
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _handle_provider_models(self) -> None:
            try:
                body = self._read_json_body()
                self._send_json(200, provider_models_payload(body))
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _handle_chat(self) -> None:
            try:
                body = self._read_json_body()
                self._send_json(200, chat_payload(body))
            except ChatRequestError as exc:
                self._send_json(400, exc.payload)
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def _handle_clear_chat_session(self) -> None:
            try:
                body = self._read_json_body()
                self._send_json(200, clear_chat_session_payload(body))
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


def _collect_env_fields(
    model_config: Mapping[str, Any],
    bot_config: Mapping[str, Any],
    env_values: Mapping[str, str],
) -> list[dict[str, Any]]:
    fields_by_key: dict[str, dict[str, Any]] = {}

    for key, setting in RUNTIME_ENV_FIELDS:
        _add_env_field(fields_by_key, category="runtime", owner="routing", setting=setting, key=key, env_values=env_values)

    for provider_name, provider in sorted(_mapping(model_config, "providers").items()):
        if not isinstance(provider, Mapping):
            continue
        for config_key, setting in PROVIDER_ENV_FIELDS:
            _add_env_field(
                fields_by_key,
                category="provider",
                owner=str(provider_name),
                setting=setting,
                key=provider.get(config_key),
                env_values=env_values,
                config_key=config_key,
            )

    agents = _mapping(model_config, "agents")
    members = agents.get("members", {})
    if isinstance(members, Mapping):
        for agent_name, agent in sorted(members.items()):
            if not isinstance(agent, Mapping):
                continue
            for config_key, setting in AGENT_ENV_FIELDS:
                _add_env_field(
                fields_by_key,
                    category="agent",
                    owner=f"agent:{agent_name}",
                    setting=setting,
                    key=agent.get(config_key),
                    env_values=env_values,
                    config_key=config_key,
                )

    channels = bot_config.get("channels", {})
    if isinstance(channels, Mapping):
        for channel_name, channel in sorted(channels.items()):
            if not isinstance(channel, Mapping):
                continue
            for config_key, setting in BOT_ENV_FIELDS:
                _add_env_field(
                fields_by_key,
                    category="channel",
                    owner=str(channel_name),
                    setting=setting,
                    key=channel.get(config_key),
                    env_values=env_values,
                    config_key=config_key,
                )

    for key in sorted(env_values):
        if key not in fields_by_key:
            _add_env_field(
                fields_by_key,
                category="other",
                owner=".env",
                setting="Unreferenced local value",
                key=key,
                env_values=env_values,
            )

    return sorted(
        fields_by_key.values(),
        key=lambda field: (ENV_CATEGORY_ORDER.get(str(field["category"]), 99), str(field["owner"]), str(field["key"])),
    )


def _add_env_field(
    fields_by_key: dict[str, dict[str, Any]],
    *,
    category: str,
    owner: str,
    setting: str,
    key: object,
    env_values: Mapping[str, str],
    config_key: str | None = None,
) -> None:
    if not key:
        return
    rendered_key = str(key).strip()
    if not rendered_key:
        return
    if rendered_key in fields_by_key:
        fields_by_key[rendered_key]["owners"].append(owner)
        return

    if rendered_key in env_values:
        value = env_values[rendered_key]
        source = "env_file"
    else:
        value = os.environ.get(rendered_key, "")
        source = "process" if rendered_key in os.environ else "unset"

    fields_by_key[rendered_key] = {
        "key": rendered_key,
        "category": category,
        "owner": owner,
        "owners": [owner],
        "setting": setting,
        "config_key": config_key,
        "value": value,
        "configured": bool(str(value).strip()),
        "source": source,
        "secret_like": _looks_secret(rendered_key),
    }


def _looks_secret(key: str) -> bool:
    upper = key.upper()
    return any(marker in upper for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD"))


def _provider_by_id(provider_id: str) -> Mapping[str, Any]:
    config, _, _ = read_config()
    providers = _mapping(config, "providers")
    if provider_id not in providers:
        raise ValueError(f"unknown provider: {provider_id}")
    provider = providers[provider_id]
    if not isinstance(provider, Mapping):
        raise ValueError(f"provider must be an object: {provider_id}")
    return provider


def _env_lookup(name: object, env_values: Mapping[str, str]) -> str:
    if not name:
        return ""
    key = str(name).strip()
    return str(env_values.get(key) or os.environ.get(key, "")).strip()


def merged_env_values(extra_values: object = None, *, env_path: Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    merged = dict(read_env_file(env_path))
    for key, value in os.environ.items():
        merged[str(key)] = str(value)
    if isinstance(extra_values, Mapping):
        for key, value in extra_values.items():
            name = str(key).strip()
            if not name:
                continue
            merged[name] = "" if value is None else str(value).strip()
    return merged


def _model_list_headers(api_key: str | None) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    key = str(api_key or "").strip()
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _extract_model_ids(payload: Any) -> list[str]:
    candidates: Any = payload
    if isinstance(payload, Mapping):
        candidates = payload.get("data", payload.get("models", []))
    if not isinstance(candidates, list):
        return []

    models: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        model_id = ""
        if isinstance(item, str):
            model_id = item.strip()
        elif isinstance(item, Mapping):
            model_id = str(item.get("id") or item.get("name") or "").strip()
        if model_id and model_id not in seen:
            seen.add(model_id)
            models.append(model_id)
    return models


def _mapping(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config.get(key, {})
    return value if isinstance(value, Mapping) else {}


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

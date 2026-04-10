from __future__ import annotations

import json
import os
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from channels.bot_config import load_bot_channel_config, validate_bot_channel_config


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CONFIG = ROOT / "config" / "bot-channels.example.json"
LOCAL_CONFIG = ROOT / "config" / "bot-channels.local.json"
GRAPH_VERSION_FALLBACK = "v24.0"


@dataclass(frozen=True)
class BotDispatch:
    channel: str
    kind: str
    mode: str
    enabled: bool
    method: str
    endpoint: str | None
    headers: Mapping[str, str]
    body: Mapping[str, Any]
    live_supported: bool
    notes: tuple[str, ...]
    redactions: tuple[str, ...] = ()

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "kind": self.kind,
            "mode": self.mode,
            "enabled": self.enabled,
            "method": self.method,
            "endpoint": _redact_value(self.endpoint, self.redactions),
            "headers": _redact_value(dict(self.headers), self.redactions),
            "body": _redact_value(dict(self.body), self.redactions),
            "live_supported": self.live_supported,
            "notes": list(self.notes),
        }


def active_bot_config_path() -> Path:
    return LOCAL_CONFIG if LOCAL_CONFIG.exists() else EXAMPLE_CONFIG


def load_active_bot_config() -> tuple[dict[str, Any], str, Path]:
    path = active_bot_config_path()
    config = load_bot_channel_config(path)
    source = "local" if path == LOCAL_CONFIG else "example"
    return config, source, path


def list_channels(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_bot_channel_config(config)
    channels = []
    for name, channel in sorted(config["channels"].items()):
        channels.append(
            {
                "name": name,
                "kind": channel["kind"],
                "enabled": bool(channel["enabled"]),
                "capabilities": list(channel.get("capabilities", [])),
            }
        )
    return channels


def build_dispatch(
    config: Mapping[str, Any],
    *,
    text: str,
    channel_name: str | None = None,
    env: Mapping[str, str] | None = None,
) -> BotDispatch:
    validate_bot_channel_config(config)
    env = os.environ if env is None else env
    channel_name = channel_name or str(config["default_channel"])
    channels = config["channels"]
    if channel_name not in channels:
        raise ValueError(f"unknown bot channel: {channel_name}")

    channel = channels[channel_name]
    kind = str(channel["kind"])
    if kind == "telegram":
        return _telegram_dispatch(config, channel_name, channel, text, env)
    if kind == "whatsapp_cloud":
        return _whatsapp_dispatch(config, channel_name, channel, text, env)
    if kind == "feishu_webhook":
        return _feishu_dispatch(config, channel_name, channel, text, env)
    if kind == "qq_official":
        return _qq_dispatch(config, channel_name, channel, text, env)
    if kind == "generic_webhook":
        return _generic_webhook_dispatch(config, channel_name, channel, text, env)
    raise ValueError(f"unsupported bot channel kind: {kind}")


def send_or_preview(
    config: Mapping[str, Any],
    *,
    text: str,
    channel_name: str | None = None,
    env: Mapping[str, str] | None = None,
    live: bool = False,
) -> dict[str, Any]:
    dispatch = build_dispatch(config, text=text, channel_name=channel_name, env=env)
    rendered = dispatch.as_redacted_dict()
    if not live:
        rendered["dry_run"] = True
        return rendered
    if dispatch.mode != "live":
        raise ValueError("live dispatch requires config mode=live")
    if not dispatch.enabled:
        raise ValueError(f"channel is disabled: {dispatch.channel}")
    if not dispatch.live_supported:
        raise NotImplementedError("; ".join(dispatch.notes))
    if not dispatch.endpoint:
        raise ValueError("live dispatch requires a concrete endpoint")
    if _has_unresolved_placeholder(dispatch.endpoint) or _has_unresolved_placeholder(dispatch.headers) or _has_unresolved_placeholder(dispatch.body):
        raise ValueError("live dispatch requires all referenced environment variables to be configured")

    data = json.dumps(dispatch.body, ensure_ascii=False).encode("utf-8")
    headers = {key: value for key, value in dispatch.headers.items() if value}
    request = Request(dispatch.endpoint, data=data, headers=headers, method=dispatch.method)
    with urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")
        return {
            **rendered,
            "dry_run": False,
            "status": response.status,
            "response": response_body,
        }


def _telegram_dispatch(config: Mapping[str, Any], name: str, channel: Mapping[str, Any], text: str, env: Mapping[str, str]) -> BotDispatch:
    token_env = channel.get("token_env")
    target_env = channel.get("target_env")
    token = _env(env, token_env)
    chat_id = _env(env, target_env)
    endpoint = f"https://api.telegram.org/bot{token}/sendMessage" if token else "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"
    return BotDispatch(
        channel=name,
        kind="telegram",
        mode=str(config["mode"]),
        enabled=bool(channel["enabled"]),
        method="POST",
        endpoint=endpoint,
        headers={"Content-Type": "application/json"},
        body={"chat_id": chat_id or f"${{{target_env}}}", "text": text},
        live_supported=True,
        notes=("Telegram Bot API sendMessage adapter.",),
        redactions=tuple(item for item in (token,) if item),
    )


def _whatsapp_dispatch(config: Mapping[str, Any], name: str, channel: Mapping[str, Any], text: str, env: Mapping[str, str]) -> BotDispatch:
    token_env = channel.get("token_env")
    phone_number_id_env = channel.get("phone_number_id_env")
    target_env = channel.get("target_env")
    version = _env(env, channel.get("api_version_env")) or GRAPH_VERSION_FALLBACK
    phone_number_id = _env(env, phone_number_id_env)
    target = _env(env, target_env)
    endpoint_id = phone_number_id or f"${{{phone_number_id_env}}}"
    token = _env(env, token_env)
    return BotDispatch(
        channel=name,
        kind="whatsapp_cloud",
        mode=str(config["mode"]),
        enabled=bool(channel["enabled"]),
        method="POST",
        endpoint=f"https://graph.facebook.com/{version}/{endpoint_id}/messages",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token or '${' + str(token_env) + '}'}"},
        body={
            "messaging_product": "whatsapp",
            "to": target or f"${{{target_env}}}",
            "type": "text",
            "text": {"body": text},
        },
        live_supported=True,
        notes=("WhatsApp Cloud API messages adapter.", "Set WHATSAPP_GRAPH_API_VERSION when Meta deprecates the fallback version."),
        redactions=tuple(item for item in (token,) if item),
    )


def _feishu_dispatch(config: Mapping[str, Any], name: str, channel: Mapping[str, Any], text: str, env: Mapping[str, str]) -> BotDispatch:
    webhook_url_env = channel.get("webhook_url_env")
    endpoint = _env(env, webhook_url_env) or f"${{{webhook_url_env}}}"
    secret = _env(env, channel.get("secret_env"))
    return BotDispatch(
        channel=name,
        kind="feishu_webhook",
        mode=str(config["mode"]),
        enabled=bool(channel["enabled"]),
        method="POST",
        endpoint=endpoint,
        headers={"Content-Type": "application/json"},
        body={"msg_type": "text", "content": {"text": text}},
        live_supported=secret is None,
        notes=(
            "Feishu/Lark custom bot webhook adapter.",
            "Signed Feishu webhooks are not sent live until request signing is implemented.",
        )
        if secret
        else ("Feishu/Lark custom bot webhook adapter.",),
        redactions=tuple(item for item in (_env(env, webhook_url_env),) if item),
    )


def _qq_dispatch(config: Mapping[str, Any], name: str, channel: Mapping[str, Any], text: str, env: Mapping[str, str]) -> BotDispatch:
    del env
    return BotDispatch(
        channel=name,
        kind="qq_official",
        mode=str(config["mode"]),
        enabled=bool(channel["enabled"]),
        method="SDK_OR_GATEWAY",
        endpoint=None,
        headers={},
        body={"target_kind": channel.get("target_kind", "guild_channel"), "content": text},
        live_supported=False,
        notes=(
            "QQ official bot uses official gateway/openapi flows and should be connected through a dedicated adapter.",
            "This dry-run route prevents treating QQ as a generic webhook.",
        ),
    )


def _generic_webhook_dispatch(config: Mapping[str, Any], name: str, channel: Mapping[str, Any], text: str, env: Mapping[str, str]) -> BotDispatch:
    webhook_url_env = channel.get("webhook_url_env")
    endpoint = _env(env, webhook_url_env) or f"${{{webhook_url_env}}}"
    return BotDispatch(
        channel=name,
        kind="generic_webhook",
        mode=str(config["mode"]),
        enabled=bool(channel["enabled"]),
        method="POST",
        endpoint=endpoint,
        headers={"Content-Type": "application/json"},
        body={"text": text},
        live_supported=True,
        notes=("Generic JSON webhook adapter.",),
        redactions=tuple(item for item in (_env(env, webhook_url_env),) if item),
    )


def _env(env: Mapping[str, str], name: object) -> str | None:
    if not name:
        return None
    value = env.get(str(name), "").strip()
    return value or None


def _redact_webhook(value: str) -> str:
    if value.startswith(("http://", "https://")):
        parts = urlsplit(value)
        return f"{parts.scheme}://{parts.netloc}/?redacted=1"
    return value


def _has_unresolved_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return "${" in value
    if isinstance(value, MappingABC):
        return any(_has_unresolved_placeholder(key) or _has_unresolved_placeholder(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_has_unresolved_placeholder(item) for item in value)
    return False


def _redact_value(value: Any, redactions: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        redacted = value
        for secret in redactions:
            if redacted == secret:
                redacted = _redact_webhook(redacted)
            else:
                redacted = redacted.replace(secret, "***")
        return redacted
    if isinstance(value, dict):
        return {key: _redact_value(item, redactions) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item, redactions) for item in value]
    return value

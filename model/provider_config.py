from __future__ import annotations

import copy
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from replay.schema_support import validate_against_schema


VALID_MODEL_MODES = {"off", "mock", "live"}
VALID_AGENT_MODES = {"single_agent", "multi_agent"}


@dataclass(frozen=True)
class ModelRoute:
    mode: str
    agent_mode: str
    role: str
    agent_id: str
    provider_name: str
    provider_kind: str
    model: str | None
    model_env: str | None
    base_url_env: str | None
    base_url: str | None
    api_key_env: str | None
    api_key_configured: bool
    capabilities: tuple[str, ...]
    system_contract: str | None

    def as_redacted_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "agent_mode": self.agent_mode,
            "role": self.role,
            "agent_id": self.agent_id,
            "provider_name": self.provider_name,
            "provider_kind": self.provider_kind,
            "model": self.model,
            "model_env": self.model_env,
            "base_url_env": self.base_url_env,
            "base_url": self.base_url,
            "api_key_env": self.api_key_env,
            "api_key_configured": self.api_key_configured,
            "capabilities": list(self.capabilities),
            "system_contract": self.system_contract,
        }


def load_model_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    validate_model_config(config)
    return config


def validate_model_config(config: Mapping[str, Any]) -> None:
    validate_against_schema(config, "model-config.schema.json")

    providers = _mapping(config, "providers")
    default_provider = _required_str(config, "default_provider")
    _require_member(providers, default_provider, "default_provider")

    active_provider = config.get("active_provider")
    if active_provider is not None:
        _require_member(providers, str(active_provider), "active_provider")

    agents = _mapping(config, "agents")
    members = _mapping(agents, "members")
    default_agent = agents.get("default_agent")
    if default_agent is not None:
        _require_member(members, str(default_agent), "default_agent")

    for agent_id, member in members.items():
        provider_name = _mapping_value(member, "provider")
        if provider_name is not None:
            _require_member(providers, provider_name, f"agent {agent_id} provider")

    role_map = agents.get("role_map", {})
    if not isinstance(role_map, Mapping):
        raise ValueError("agents.role_map must be an object")
    for role, agent_id in role_map.items():
        _require_member(members, str(agent_id), f"role {role} agent")


def with_active_provider(config: Mapping[str, Any], provider_name: str) -> dict[str, Any]:
    updated = copy.deepcopy(dict(config))
    _require_member(_mapping(updated, "providers"), provider_name, "active_provider")
    updated["active_provider"] = provider_name
    validate_model_config(updated)
    return updated


def with_agent_mode(config: Mapping[str, Any], agent_mode: str) -> dict[str, Any]:
    if agent_mode not in VALID_AGENT_MODES:
        raise ValueError(f"unsupported agent mode: {agent_mode}")
    updated = copy.deepcopy(dict(config))
    updated["agents"]["mode"] = agent_mode
    validate_model_config(updated)
    return updated


def resolve_model_route(
    config: Mapping[str, Any],
    role: str,
    *,
    provider_override: str | None = None,
    agent_override: str | None = None,
    env: Mapping[str, str] | None = None,
) -> ModelRoute:
    validate_model_config(config)
    env = os.environ if env is None else env
    providers = _mapping(config, "providers")
    agents = _mapping(config, "agents")
    members = _mapping(agents, "members")

    mode = _mode_override(env, "DEVICE_AGENT_MODEL_MODE", str(config["mode"]), VALID_MODEL_MODES)
    agent_mode = _mode_override(env, "DEVICE_AGENT_AGENT_MODE", str(agents["mode"]), VALID_AGENT_MODES)
    agent_id = _select_agent_id(agents, members, role, agent_mode, agent_override, env)
    member = _mapping(members, agent_id)
    provider_name = _select_provider_name(config, member, provider_override, env)
    provider = _mapping(providers, provider_name)

    agent_model_env = _mapping_value(member, "model_env")
    provider_model_env = _mapping_value(provider, "default_model_env")
    model_env = agent_model_env or provider_model_env
    model = (
        _env_value(env, agent_model_env)
        or _mapping_value(member, "model")
        or _env_value(env, provider_model_env)
        or _mapping_value(provider, "default_model")
    )

    base_url_env = _mapping_value(provider, "base_url_env")
    api_key_env = _mapping_value(provider, "api_key_env")
    return ModelRoute(
        mode=mode,
        agent_mode=agent_mode,
        role=role,
        agent_id=agent_id,
        provider_name=provider_name,
        provider_kind=str(provider["kind"]),
        model=model,
        model_env=model_env,
        base_url_env=base_url_env,
        base_url=_env_value(env, base_url_env),
        api_key_env=api_key_env,
        api_key_configured=bool(_env_value(env, api_key_env)),
        capabilities=tuple(str(item) for item in provider.get("capabilities", [])),
        system_contract=_mapping_value(member, "system_contract"),
    )


def _select_provider_name(
    config: Mapping[str, Any],
    member: Mapping[str, Any],
    provider_override: str | None,
    env: Mapping[str, str],
) -> str:
    providers = _mapping(config, "providers")
    provider_name = (
        _clean(provider_override)
        or _env_value(env, "DEVICE_AGENT_MODEL_PROVIDER")
        or _mapping_value(member, "provider")
        or _mapping_value(config, "active_provider")
        or str(config["default_provider"])
    )
    _require_member(providers, provider_name, "provider")
    return provider_name


def _select_agent_id(
    agents: Mapping[str, Any],
    members: Mapping[str, Any],
    role: str,
    agent_mode: str,
    agent_override: str | None,
    env: Mapping[str, str],
) -> str:
    role_env = f"DEVICE_AGENT_AGENT_{_env_suffix(role)}"
    selected = _clean(agent_override) or _env_value(env, role_env) or _env_value(env, "DEVICE_AGENT_AGENT")
    if not selected and agent_mode == "multi_agent":
        role_map = agents.get("role_map", {})
        if isinstance(role_map, Mapping):
            selected = _mapping_value(role_map, role)
    if not selected:
        selected = _mapping_value(agents, "default_agent")
    if not selected:
        selected = next(iter(members))
    _require_member(members, selected, "agent")
    return selected


def _mode_override(env: Mapping[str, str], name: str, configured: str, valid: set[str]) -> str:
    value = _env_value(env, name) or configured
    if value not in valid:
        raise ValueError(f"unsupported {name}: {value}")
    return value


def _mapping(config: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = config[key]
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _mapping_value(config: Mapping[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    return _clean(str(value))


def _required_str(config: Mapping[str, Any], key: str) -> str:
    value = _mapping_value(config, key)
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _require_member(collection: Mapping[str, Any], name: str, field: str) -> None:
    if name not in collection:
        raise ValueError(f"{field} references unknown entry: {name}")


def _env_value(env: Mapping[str, str], name: str | None) -> str | None:
    if not name:
        return None
    return _clean(env.get(name))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _env_suffix(role: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", role).strip("_").upper()

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from model.provider_config import validate_model_config


DEFAULT_OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
DEFAULT_OPENCLAW_WORKSPACE = Path.home() / ".openclaw" / "workspace"
DEFAULT_LOCAL_CONFIG = Path(__file__).resolve().parent.parent / "config" / "model-providers.local.json"

WORKSPACE_FILES = (
    "AGENTS.md",
    "SOUL.md",
    "USER.md",
    "IDENTITY.md",
    "TOOLS.md",
    "HEARTBEAT.md",
    "BOOT.md",
    "BOOTSTRAP.md",
    "MEMORY.md",
)

ROLE_BY_HINT = (
    ("classifier", "classifier"),
    ("router", "classifier"),
    ("summarizer", "summarizer"),
    ("summary", "summarizer"),
    ("analyst", "summarizer"),
    ("verifier", "verifier"),
    ("auditor", "verifier"),
)


@dataclass(frozen=True)
class OpenClawAgent:
    agent_id: str
    name: str
    model_ref: str | None
    workspace: str | None
    agent_dir: str | None
    skills: tuple[str, ...]
    is_default: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model_ref": self.model_ref,
            "workspace": self.workspace,
            "agent_dir": self.agent_dir,
            "skills": list(self.skills),
            "is_default": self.is_default,
        }


def load_openclaw_config(path: Path = DEFAULT_OPENCLAW_CONFIG) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    parsed = parse_json5_subset(raw)
    if not isinstance(parsed, dict):
        raise ValueError("OpenClaw config root must be an object")
    return parsed


def parse_json5_subset(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    normalized = _strip_json5_comments(raw)
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = re.sub(r"([{\[,]\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*:)", r'\1"\2"\3', normalized)
    normalized = _replace_simple_single_quoted_strings(normalized)
    return json.loads(normalized)


def migrate_openclaw(
    *,
    config_path: Path = DEFAULT_OPENCLAW_CONFIG,
    workspace_path: Path | None = None,
) -> dict[str, Any]:
    source_config = load_openclaw_config(config_path)
    workspace = workspace_path or infer_workspace(source_config) or DEFAULT_OPENCLAW_WORKSPACE
    agents = extract_openclaw_agents(source_config, workspace)
    model_refs = sorted({agent.model_ref for agent in agents if agent.model_ref})
    generated_config = build_device_agent_config(agents, model_refs)
    workspace_files = detect_workspace_files(workspace)

    report = {
        "source": {
            "format": "openclaw.json5-subset",
            "config_path": str(config_path),
            "workspace_path": str(workspace),
        },
        "imported_agents": [agent.as_dict() for agent in agents],
        "model_refs": model_refs,
        "workspace_files_found": [str(path) for path in workspace_files],
        "skipped_secret_paths": [
            str(config_path.parent / "credentials"),
            str(config_path.parent / "sessions"),
        ],
        "warnings": migration_warnings(agents, workspace_files),
        "generated_config": generated_config,
        "external_handoff": build_external_handoff(config_path, workspace, agents, workspace_files, generated_config),
    }
    validate_model_config(generated_config)
    return report


def write_local_config(config: Mapping[str, Any], *, output_path: Path | None = DEFAULT_LOCAL_CONFIG, force: bool = False) -> Path:
    validate_model_config(config)
    output_path = output_path or DEFAULT_LOCAL_CONFIG
    if output_path.exists() and not force:
        raise FileExistsError(f"{output_path} already exists; pass --force to overwrite")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return output_path


def infer_workspace(config: Mapping[str, Any]) -> Path | None:
    defaults = _agent_defaults(config)
    for key in ("workspace", "workspace_path", "workspaceDir"):
        value = _clean(defaults.get(key))
        if value:
            return Path(value).expanduser()
    return None


def extract_openclaw_agents(config: Mapping[str, Any], workspace: Path) -> list[OpenClawAgent]:
    defaults = _agent_defaults(config)
    default_model = first_model_ref(defaults.get("model"))
    default_skills = tuple(_string_list(defaults.get("skills")))
    raw_agents = _agent_list(config)
    agents: list[OpenClawAgent] = []

    if not raw_agents:
        raw_agents = [{"id": "openclaw-default", "name": "OpenClaw Default", "default": True}]

    for index, raw_agent in enumerate(raw_agents, start=1):
        if not isinstance(raw_agent, Mapping):
            continue
        agent_id = _slug(_clean(raw_agent.get("id")) or _clean(raw_agent.get("name")) or f"openclaw-agent-{index}")
        name = _clean(raw_agent.get("name")) or agent_id
        model_ref = first_model_ref(raw_agent.get("model")) or default_model
        agent_workspace = _clean(raw_agent.get("workspace")) or _clean(defaults.get("workspace")) or str(workspace)
        agent_dir = _clean(raw_agent.get("agentDir")) or _clean(raw_agent.get("agent_dir"))
        skills = tuple(_string_list(raw_agent.get("skills")) or default_skills)
        agents.append(
            OpenClawAgent(
                agent_id=agent_id,
                name=name,
                model_ref=model_ref,
                workspace=agent_workspace,
                agent_dir=agent_dir,
                skills=skills,
                is_default=bool(raw_agent.get("default")) or index == 1,
            )
        )
    return agents


def build_device_agent_config(agents: list[OpenClawAgent], model_refs: list[str]) -> dict[str, Any]:
    providers = build_providers(model_refs)
    provider_names = list(providers)
    default_provider = provider_names[0] if provider_names else "openclaw_import"
    if not providers:
        providers[default_provider] = {
            "kind": "openclaw_model_ref",
            "default_model": "openclaw/unset",
            "capabilities": ["planner", "classifier", "summarizer", "verifier"],
        }

    default_agent = next((agent.agent_id for agent in agents if agent.is_default), agents[0].agent_id)
    members = {}
    for agent in agents:
        provider_name = provider_name_for_model(agent.model_ref) if agent.model_ref else default_provider
        members[agent.agent_id] = {
            "provider": provider_name,
            "model": agent.model_ref or providers[provider_name]["default_model"],
            "roles": infer_roles(agent, is_default=agent.agent_id == default_agent),
            "system_contract": "Migrated from OpenClaw as candidate-only agent context; cannot create verified facts or host authority.",
        }

    role_map = {}
    for role in ("planner", "classifier", "summarizer", "verifier"):
        role_map[role] = next(
            (
                agent.agent_id
                for agent in agents
                if agent.agent_id != default_agent and role in members[agent.agent_id]["roles"]
            ),
            default_agent,
        )

    return {
        "version": 1,
        "mode": "mock",
        "default_provider": default_provider,
        "active_provider": default_provider,
        "providers": providers,
        "agents": {
            "mode": "multi_agent" if len(agents) > 1 else "single_agent",
            "default_agent": default_agent,
            "role_map": role_map,
            "members": members,
        },
    }


def build_providers(model_refs: list[str]) -> dict[str, dict[str, Any]]:
    providers: dict[str, dict[str, Any]] = {}
    for model_ref in model_refs:
        provider_name = provider_name_for_model(model_ref)
        providers.setdefault(
            provider_name,
            {
                "kind": "openclaw_model_ref",
                "default_model": model_ref,
                "capabilities": ["planner", "classifier", "summarizer", "verifier"],
            },
        )
    return providers


def provider_name_for_model(model_ref: str) -> str:
    provider = model_ref.split("/", 1)[0] if "/" in model_ref else "openclaw_import"
    return "openclaw_" + _slug(provider)


def first_model_ref(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, Mapping):
        for key in ("primary", "default", "model", "name", "id"):
            model_ref = first_model_ref(value.get(key))
            if model_ref:
                return model_ref
        fallback = value.get("fallbacks")
        if isinstance(fallback, list) and fallback:
            return first_model_ref(fallback[0])
    if isinstance(value, list) and value:
        return first_model_ref(value[0])
    return None


def detect_workspace_files(workspace: Path) -> list[Path]:
    if not workspace.exists():
        return []
    found = [workspace / name for name in WORKSPACE_FILES if (workspace / name).is_file()]
    memory_dir = workspace / "memory"
    if memory_dir.is_dir():
        found.extend(sorted(memory_dir.glob("*.md"))[:20])
    return found


def migration_warnings(agents: list[OpenClawAgent], workspace_files: list[Path]) -> list[str]:
    warnings = [
        "OpenClaw credentials and sessions are intentionally skipped; configure provider keys manually through environment variables.",
        "Imported OpenClaw state enters as candidate context only, not verified fact or completed task state.",
    ]
    if not workspace_files:
        warnings.append("No OpenClaw workspace instruction or memory files were found at the selected workspace path.")
    if any(agent.model_ref is None for agent in agents):
        warnings.append("At least one OpenClaw agent did not declare a model; generated config uses the default provider fallback.")
    return warnings


def build_external_handoff(
    config_path: Path,
    workspace: Path,
    agents: list[OpenClawAgent],
    workspace_files: list[Path],
    generated_config: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "agent_id": "openclaw.import",
        "task_or_node_ref": "migration.openclaw",
        "produced_artifacts": [str(path) for path in workspace_files],
        "candidate_facts": [
            f"OpenClaw config parsed from {config_path}",
            f"OpenClaw workspace selected as {workspace}",
            f"{len(agents)} OpenClaw agent(s) mapped into device-agent provider config",
        ],
        "used_evidence": [str(config_path), *[str(path) for path in workspace_files]],
        "assumptions": [
            "OpenClaw model refs are provider/model strings unless configured otherwise.",
            "OpenClaw workspace memories and identity files require human review before promotion.",
        ],
        "open_questions": [
            "Which migrated agent, if any, should become the long-term default planner?",
            "Which provider keys should be configured locally through environment variables?",
        ],
        "recommended_next_actions": [
            "Review generated_config before writing config/model-providers.local.json.",
            "Run the route preview in the local UI.",
            "Do not import OpenClaw sessions as verified memory without separate evidence checks.",
        ],
        "claimed_risk_changes": [],
        "capsule_or_resume_payload": {
            "generated_config": generated_config,
            "trust_ceiling": "candidate_only",
        },
    }


def _agent_defaults(config: Mapping[str, Any]) -> Mapping[str, Any]:
    agents = config.get("agents")
    if isinstance(agents, Mapping):
        defaults = agents.get("defaults", {})
        return defaults if isinstance(defaults, Mapping) else {}
    agent = config.get("agent")
    if isinstance(agent, Mapping):
        return agent
    return {}


def _agent_list(config: Mapping[str, Any]) -> list[Any]:
    agents = config.get("agents")
    if isinstance(agents, Mapping):
        raw = agents.get("list", [])
        return raw if isinstance(raw, list) else []
    raw_agents = config.get("agent")
    if isinstance(raw_agents, list):
        return raw_agents
    if isinstance(raw_agents, Mapping):
        return [raw_agents]
    return []


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = _clean(value)
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower()).strip("_") or "openclaw_agent"


def infer_roles(agent: OpenClawAgent, *, is_default: bool) -> list[str]:
    if is_default:
        return ["planner", "classifier", "summarizer", "verifier"]
    haystack = " ".join([agent.agent_id, agent.name, *agent.skills]).lower()
    for hint, role in ROLE_BY_HINT:
        if hint in haystack:
            return [role]
    return ["planner"]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _strip_json5_comments(raw: str) -> str:
    result = []
    in_string: str | None = None
    escaped = False
    index = 0
    while index < len(raw):
        char = raw[index]
        nxt = raw[index + 1] if index + 1 < len(raw) else ""
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            index += 1
            continue
        if char in ("'", '"'):
            in_string = char
            result.append(char)
            index += 1
            continue
        if char == "/" and nxt == "/":
            index += 2
            while index < len(raw) and raw[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and nxt == "*":
            index += 2
            while index + 1 < len(raw) and not (raw[index] == "*" and raw[index + 1] == "/"):
                index += 1
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _replace_simple_single_quoted_strings(raw: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = match.group(1)
        return json.dumps(value)

    return re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", replace, raw)

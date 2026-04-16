from __future__ import annotations

import json
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from model.provider_config import ModelRoute


LIVE_TIMEOUT_SECONDS = 60
MAX_HISTORY_TURNS = 12


class ProviderRequestError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        error_kind: str = "provider_request_failed",
        status_code: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_kind = error_kind
        self.status_code = status_code
        self.metadata = dict(metadata or {})

    def as_payload(self) -> dict[str, Any]:
        payload = {
            "error": str(self),
            "error_kind": self.error_kind,
        }
        if self.status_code is not None:
            payload["status_code"] = self.status_code
        payload.update(self.metadata)
        return payload


def invoke_model_route(
    route: ModelRoute,
    *,
    user_message: str,
    history: Sequence[Mapping[str, Any]],
    env: Mapping[str, str],
    timeout_seconds: int = LIVE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    prompt = str(user_message or "").strip()
    if not prompt:
        raise ValueError("message is required")

    if route.mode == "off":
        return {
            "reply": f"Model mode is off. Role `{route.role}` will not call a provider until you switch back to mock or live.",
            "mode": route.mode,
            "provider_kind": route.provider_kind,
            "usage": None,
            "finish_reason": "disabled",
        }

    if route.mode == "mock" or route.provider_kind == "mock":
        return {
            "reply": _mock_reply(route, prompt),
            "mode": route.mode,
            "provider_kind": route.provider_kind,
            "usage": None,
            "finish_reason": "mock",
        }

    if route.provider_kind != "openai_compatible":
        raise ValueError(f"unsupported live provider kind: {route.provider_kind}")

    base_url = str(route.base_url or "").strip()
    if not base_url:
        raise ValueError(f"missing base URL for provider {route.provider_name}")

    api_key = ""
    if route.api_key_env:
        api_key = str(env.get(route.api_key_env) or "").strip()
    if not api_key:
        raise ValueError(f"missing API key for provider {route.provider_name}")

    model = str(route.model or "").strip()
    if not model:
        raise ValueError(f"missing model for provider {route.provider_name}")

    messages = _build_messages(route, history, prompt)
    payload = _request_chat_completion(
        base_url=base_url,
        api_key=api_key,
        model_candidates=_candidate_model_ids(model),
        messages=messages,
        timeout_seconds=timeout_seconds,
    )

    reply = _extract_reply_text(payload)
    if not reply:
        raise ValueError("provider response did not contain assistant text")

    usage = payload.get("usage") if isinstance(payload, Mapping) else None
    finish_reason = _extract_finish_reason(payload)
    return {
        "reply": reply,
        "mode": route.mode,
        "provider_kind": route.provider_kind,
        "usage": usage if isinstance(usage, Mapping) else None,
        "finish_reason": finish_reason,
        "response_id": payload.get("id") if isinstance(payload, Mapping) else None,
    }


def _build_messages(
    route: ModelRoute,
    history: Sequence[Mapping[str, Any]],
    prompt: str,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if route.system_contract:
        messages.append({"role": "system", "content": route.system_contract})

    for turn in list(history)[-MAX_HISTORY_TURNS:]:
        user_message = str(turn.get("user") or "").strip()
        assistant_message = str(turn.get("assistant") or "").strip()
        if user_message:
            messages.append({"role": "user", "content": user_message})
        if assistant_message:
            messages.append({"role": "assistant", "content": assistant_message})

    messages.append({"role": "user", "content": prompt})
    return messages


def _extract_reply_text(payload: Any) -> str:
    if not isinstance(payload, Mapping):
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], Mapping) else None
    if not isinstance(message, Mapping):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    text_parts.append(stripped)
                continue
            if not isinstance(item, Mapping):
                continue
            text = str(item.get("text") or item.get("content") or "").strip()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts).strip()
    return ""


def _extract_finish_reason(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    if not isinstance(choices[0], Mapping):
        return None
    value = choices[0].get("finish_reason")
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _request_chat_completion(
    *,
    base_url: str,
    api_key: str,
    model_candidates: Sequence[str],
    messages: Sequence[Mapping[str, str]],
    timeout_seconds: int,
) -> dict[str, Any]:
    last_error: ValueError | None = None
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    configured_model = model_candidates[0] if model_candidates else ""
    for index, model in enumerate(model_candidates):
        request = Request(
            endpoint,
            data=json.dumps({"model": model, "messages": list(messages), "stream": False}).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if index + 1 < len(model_candidates) and _looks_like_unknown_model(detail):
                last_error = _model_rejection_error(
                    exc.code,
                    detail,
                    configured_model=configured_model,
                    tried_models=model_candidates[: index + 1],
                )
                continue
            if _looks_like_unknown_model(detail):
                raise _model_rejection_error(
                    exc.code,
                    detail,
                    configured_model=configured_model,
                    tried_models=model_candidates,
                ) from exc
            raise ProviderRequestError(
                _http_error_message(exc.code, detail),
                status_code=exc.code,
                metadata={"provider_message": _extract_error_text(detail)},
            ) from exc
        except URLError as exc:
            raise ProviderRequestError(f"provider request failed: {exc.reason}") from exc
    if last_error is not None:
        raise last_error
    raise ProviderRequestError("provider request failed before a response was received")


def _candidate_model_ids(model: str) -> list[str]:
    candidates = [model.strip()]
    if "/" in model:
        stripped = model.split("/", 1)[1].strip()
        if stripped and stripped not in candidates:
            candidates.append(stripped)
    return candidates


def _looks_like_unknown_model(detail: str) -> bool:
    lowered = detail.lower()
    return "unknown model" in lowered or "model_not_found" in lowered or "does not exist" in lowered


def _http_error_message(status_code: int, detail: str) -> str:
    text = _extract_error_text(detail)
    if text:
        return f"provider request failed ({status_code}): {text}"
    return f"provider request failed ({status_code})"


def _extract_error_text(detail: str) -> str | None:
    parsed = detail.strip()
    if not parsed:
        return None
    try:
        payload = json.loads(parsed)
    except json.JSONDecodeError:
        return parsed
    if not isinstance(payload, Mapping):
        return None
    message = payload.get("error")
    if isinstance(message, Mapping):
        text = str(message.get("message") or "").strip()
        return text or None
    if isinstance(message, str):
        text = message.strip()
        return text or None
    return None


def _model_rejection_error(
    status_code: int,
    detail: str,
    *,
    configured_model: str,
    tried_models: Sequence[str],
) -> ProviderRequestError:
    provider_message = _extract_error_text(detail)
    message = f"provider rejected configured model `{configured_model}`"
    if provider_message:
        message = f"{message} ({status_code}): {provider_message}"
    else:
        message = f"{message} ({status_code})"

    suggested_transport_model = next(
        (candidate for candidate in tried_models if candidate and candidate != configured_model),
        None,
    )
    metadata: dict[str, Any] = {
        "configured_model": configured_model,
        "tried_models": list(tried_models),
    }
    if provider_message:
        metadata["provider_message"] = provider_message
    if suggested_transport_model:
        metadata["suggested_transport_model"] = suggested_transport_model
    return ProviderRequestError(
        message,
        error_kind="provider_model_rejected",
        status_code=status_code,
        metadata=metadata,
    )


def _mock_reply(route: ModelRoute, prompt: str) -> str:
    return (
        f"Mock route `{route.role}` on `{route.provider_name}` captured your message locally. "
        f"No live provider call was made. Input: {prompt}"
    )

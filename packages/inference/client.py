"""OpenAI-compatible inference adapter.

FreeLLMAPI is the current inference gateway, but this adapter intentionally
depends only on the OpenAI-compatible HTTP contract. No provider credential is
stored in source code, logs, traces, or fixtures.

The adapter never writes model output to authoritative world state. Callers
must validate and provenance-tag model output before persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class InferenceError(RuntimeError):
    """Raised for configuration, transport, protocol, or provider failures."""


@dataclass(frozen=True)
class InferenceConfig:
    base_url: str
    api_key: str
    default_model: str = "gemini-3.6-flash"
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "InferenceConfig":
        base_url = os.environ.get("FREE_LLM_API_BASE_URL", "http://127.0.0.1:3001/v1").rstrip("/")
        api_key = os.environ.get("FREE_LLM_API_KEY", "")
        model = os.environ.get("GODS_EYE_INFERENCE_MODEL", "gemini-3.6-flash")
        try:
            timeout = float(os.environ.get("GODS_EYE_INFERENCE_TIMEOUT_SECONDS", "30"))
        except ValueError as exc:
            raise InferenceError("GODS_EYE_INFERENCE_TIMEOUT_SECONDS must be numeric") from exc

        config = cls(base_url, api_key, model, timeout)
        config.validate()
        return config

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise InferenceError("FREE_LLM_API_BASE_URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise InferenceError("FREE_LLM_API_BASE_URL must not contain URL credentials")
        if not self.api_key:
            raise InferenceError("FREE_LLM_API_KEY is required")
        if not self.default_model.strip():
            raise InferenceError("GODS_EYE_INFERENCE_MODEL must not be empty")
        if not 0.1 <= self.timeout_seconds <= 300:
            raise InferenceError("inference timeout must be between 0.1 and 300 seconds")


@dataclass(frozen=True)
class InferenceResult:
    request_id: str
    model: str
    text: str
    latency_ms: int
    usage: dict[str, Any]
    finish_reason: str | None
    provider_response_id: str | None

    @property
    def trusted(self) -> bool:
        """Model output is never authoritative merely because it was returned."""
        return False


Transport = Callable[[Request, float], Any]


class InferenceClient:
    def __init__(self, config: InferenceConfig, transport: Transport | None = None) -> None:
        config.validate()
        self.config = config
        self._transport = transport or self._default_transport

    @staticmethod
    def _default_transport(request: Request, timeout: float) -> Any:
        return urlopen(request, timeout=timeout)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> InferenceResult:
        self._validate_messages(messages)
        if temperature is not None and not 0 <= temperature <= 2:
            raise InferenceError("temperature must be between 0 and 2")
        if max_tokens is not None and max_tokens < 1:
            raise InferenceError("max_tokens must be positive")

        selected_model = model or self.config.default_model
        payload: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.config.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "gods-eye-world-intelligence/0.1",
            },
        )

        started = time.monotonic()
        try:
            response = self._transport(request, self.config.timeout_seconds)
            raw = response.read()
            status = getattr(response, "status", 200)
        except HTTPError as exc:
            detail = _safe_error_body(exc)
            raise InferenceError(f"inference provider returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise InferenceError(f"inference transport failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise InferenceError("inference request timed out") from exc
        except OSError as exc:
            raise InferenceError(f"inference transport failed: {exc}") from exc

        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        if status < 200 or status >= 300:
            raise InferenceError(f"inference provider returned HTTP {status}")

        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InferenceError("inference provider returned invalid JSON") from exc

        return _parse_response(document, selected_model, latency_ms)

    @staticmethod
    def _validate_messages(messages: list[dict[str, str]]) -> None:
        if not messages:
            raise InferenceError("at least one message is required")
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                raise InferenceError(f"message {index} must be an object")
            role = message.get("role")
            content = message.get("content")
            if role not in {"system", "user", "assistant", "tool"}:
                raise InferenceError(f"message {index} has unsupported role")
            if not isinstance(content, str) or not content.strip():
                raise InferenceError(f"message {index} content must be non-empty text")


def _parse_response(document: Any, requested_model: str, latency_ms: int) -> InferenceResult:
    if not isinstance(document, dict):
        raise InferenceError("inference provider response must be an object")

    choices = document.get("choices")
    if not isinstance(choices, list) or not choices:
        raise InferenceError("inference provider response has no choices")

    first = choices[0]
    if not isinstance(first, dict):
        raise InferenceError("inference provider returned an invalid choice")
    message = first.get("message")
    if not isinstance(message, dict):
        raise InferenceError("inference provider choice has no message")
    text = message.get("content")
    if not isinstance(text, str):
        raise InferenceError("inference provider returned non-text content")
    usage = document.get("usage")
    if not isinstance(usage, dict):
        usage = {}

    return InferenceResult(
        request_id=str(document.get("id") or ""),
        model=str(document.get("model") or requested_model),
        text=text,
        latency_ms=latency_ms,
        usage=usage,
        finish_reason=first.get("finish_reason"),
        provider_response_id=str(document["id"]) if document.get("id") else None,
    )


def _safe_error_body(exc: HTTPError) -> str:
    try:
        raw = exc.read(2048).decode("utf-8", errors="replace")
    except OSError:
        return "provider returned an error"
    # Provider error bodies are useful for debugging, but never echo request
    # headers or credentials. Keep the diagnostic bounded.
    return " ".join(raw.split())[:500] or "provider returned an error"

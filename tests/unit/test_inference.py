from __future__ import annotations

import json
from urllib.request import Request

import pytest

from packages.inference.client import InferenceClient, InferenceConfig, InferenceError
from packages.inference.policy import InferenceTask, select_model


class FakeResponse:
    status = 200

    def __init__(self, document: dict):
        self._body = json.dumps(document).encode("utf-8")

    def read(self):
        return self._body


def fake_transport(request: Request, timeout: float):
    assert request.full_url == "http://127.0.0.1:3001/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert timeout == 5
    return FakeResponse(
        {
            "id": "chatcmpl-test",
            "model": "gemini-3.6-flash",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "validated response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
        }
    )


def test_client_parses_openai_compatible_response_without_logging_secret():
    config = InferenceConfig(
        "http://127.0.0.1:3001/v1",
        "test-secret",
        "gemini-3.6-flash",
        5,
    )
    result = InferenceClient(config, fake_transport).complete(
        [{"role": "user", "content": "hello"}]
    )
    assert result.text == "validated response"
    assert result.model == "gemini-3.6-flash"
    assert result.usage["total_tokens"] == 15
    assert result.trusted is False


def test_client_rejects_missing_key():
    with pytest.raises(InferenceError, match="FREE_LLM_API_KEY"):
        InferenceConfig("http://127.0.0.1:3001/v1", "").validate()


def test_client_rejects_url_credentials():
    config = InferenceConfig("http://user:pass@127.0.0.1:3001/v1", "secret")
    with pytest.raises(InferenceError, match="credentials"):
        config.validate()


def test_client_rejects_empty_messages():
    config = InferenceConfig("http://127.0.0.1:3001/v1", "secret")
    with pytest.raises(InferenceError, match="at least one"):
        InferenceClient(config, fake_transport).complete([])


def test_policy_is_deterministic():
    assert select_model(InferenceTask.CLASSIFICATION) == "gemini-3.6-flash-lite"
    assert select_model(InferenceTask.INVESTIGATION) == "gemini-3.6-flash"
    assert select_model(InferenceTask.SYNTHESIS) == "gemini-3.7-flash"


def test_policy_override_is_explicit():
    assert select_model(InferenceTask.ANALYSIS, override="custom-model") == "custom-model"

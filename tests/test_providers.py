from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from modeling_agent.providers import OpenAICompatibleChatProvider, ProviderError


def make_provider() -> OpenAICompatibleChatProvider:
    return OpenAICompatibleChatProvider(
        base_url="https://provider.example.com/v1",
        api_key="test-only",
        model="test-model",
        timeout_seconds=1,
    )


def response(payload: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        request=httpx.Request("POST", "https://provider.example.com/v1/chat/completions"),
        json=payload,
    )


def test_compatible_provider_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    body = {
        "model": "returned-model",
        "choices": [{"message": {"content": json.dumps({"problem_summary": "ok"})}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 3},
    }

    async def fake_post(*args, **kwargs):
        return response(body)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    result = asyncio.run(make_provider().complete_json("problem"))
    assert result.data["problem_summary"] == "ok"
    assert result.model == "returned-model"
    assert result.prompt_tokens == 10


def test_compatible_provider_retries_invalid_json_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    async def fake_post(*args, **kwargs):
        nonlocal calls
        calls += 1
        return response(
            {
                "choices": [{"message": {"content": "not-json"}}],
                "usage": {},
            }
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    with pytest.raises(ProviderError, match="invalid response"):
        asyncio.run(make_provider().complete_json("problem"))
    assert calls == 2

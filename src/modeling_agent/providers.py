from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatResult:
    data: dict[str, Any]
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class ChatProvider(ABC):
    @abstractmethod
    async def complete_json(self, prompt: str) -> ChatResult: ...


class FakeChatProvider(ChatProvider):
    async def complete_json(self, prompt: str) -> ChatResult:
        marker = "PROBLEM_TEXT:\n"
        problem_text = prompt.split(marker, 1)[-1].split("\n\nKNOWLEDGE:", 1)[0].strip()
        summary = " ".join(problem_text.split())[:180]
        return ChatResult(
            data={
                "problem_summary": summary,
                "subproblems": ["识别核心目标与约束", "建立并验证候选模型"],
                "data_requirements": ["题目给定数据", "变量单位与缺失值说明"],
                "assumptions": ["输入数据口径一致", "未说明的外部条件在分析期内稳定"],
                "uncertainties": ["需要结合实际数据验证参数与模型假设"],
            },
            model="fake-deterministic",
            prompt_tokens=max(1, len(prompt) // 4),
            completion_tokens=80,
        )


class OpenAICompatibleChatProvider(ChatProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def complete_json(self, prompt: str) -> ChatResult:
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are a mathematical modeling analyst. Return one valid JSON object "
                    "with keys problem_summary, subproblems, data_requirements, assumptions, "
                    "and uncertainties. Never invent measured results or citations."
                ),
            },
            {"role": "user", "content": prompt},
        ]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                data = json.loads(content)
                usage = body.get("usage", {})
                return ChatResult(
                    data=data,
                    model=body.get("model", self.model),
                    prompt_tokens=int(usage.get("prompt_tokens", 0)),
                    completion_tokens=int(usage.get("completion_tokens", 0)),
                )
            except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt == 0:
                    messages.append(
                        {
                            "role": "user",
                            "content": "Repair the previous response and return only valid JSON.",
                        }
                    )
                    await asyncio.sleep(0.25)
        raise ProviderError("The chat provider returned an invalid response.") from last_error


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimension
            normalized = text.lower()
            tokens = normalized.split()
            tokens.extend(normalized[index : index + 2] for index in range(len(normalized) - 1))
            for token in tokens:
                token_number = int.from_bytes(token.encode("utf-8"), "little", signed=False)
                slot = token_number % self.dimension
                vector[slot] += 1.0
            norm = sum(value * value for value in vector) ** 0.5 or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        dimension: int = 1024,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts},
                )
            response.raise_for_status()
            ordered = sorted(response.json()["data"], key=lambda item: item["index"])
            vectors = [item["embedding"] for item in ordered]
            if vectors:
                self._dimension = len(vectors[0])
            return vectors
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise ProviderError("The embedding provider returned an invalid response.") from exc

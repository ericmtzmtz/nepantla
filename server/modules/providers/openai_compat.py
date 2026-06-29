# ruff: noqa: E501
import time
from collections.abc import AsyncGenerator

import httpx

from server.modules.providers.base import BaseProvider
from server.modules.providers.schemas import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    ModelInfo,
)


class GenericOpenAIProvider(BaseProvider):
    """Generic provider for any OpenAI-compatible API."""

    def __init__(self, platform: str, base_url: str, name: str = "",
                 timeout_ms: int = 30000, extra_headers: dict | None = None):
        self._platform = platform
        self._name = name or f"OpenAI Compatible ({platform})"
        self.base_url = base_url.rstrip("/")
        self.timeout_ms = timeout_ms
        self.extra_headers = extra_headers or {}

    @property
    def platform(self) -> str:
        return self._platform

    @property
    def supports_tools(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return self._name

    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """GET {base_url}/models, parse response into ModelInfo objects."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}", **self.extra_headers},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = data.get("data", [])
        result = []
        for m in models:
            mid = m.get("id", "")
            display = m.get("name") or m.get("id", "")
            vision = any(k in mid.lower() for k in ("vision", "gpt-4o", "gpt-4-turbo", "claude-3"))
            embed = "embed" in mid.lower()
            result.append(ModelInfo(
                id=mid,
                platform=self._platform,
                display_name=display,
                supports_vision=vision,
                supports_embeddings=embed,
            ))
        return result

    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **self.extra_headers}
        payload = {"model": model_id, "messages": [{"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)} for m in messages]}
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens
            if options.top_p is not None:
                payload["top_p"] = options.top_p
            if options.tools:
                payload["tools"] = options.tools
            if options.tool_choice:
                payload["tool_choice"] = options.tool_choice
            if options.parallel_tool_calls is not None:
                payload["parallel_tool_calls"] = options.parallel_tool_calls

        async with httpx.AsyncClient(timeout=self.timeout_ms / 1000) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{int(time.time())}"),
            created=data.get("created", int(time.time())),
            model=data.get("model", model_id),
            choices=data.get("choices", []),
            usage=data.get("usage"),
        )

    async def stream_chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> AsyncGenerator[ChatCompletionChunk]:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", **self.extra_headers}
        payload = {"model": model_id, "messages": [{"role": m.role, "content": m.content if isinstance(m.content, str) else str(m.content)} for m in messages], "stream": True}
        if options:
            if options.temperature is not None:
                payload["temperature"] = options.temperature
            if options.max_tokens is not None:
                payload["max_tokens"] = options.max_tokens
            if options.top_p is not None:
                payload["top_p"] = options.top_p
            if options.tools:
                payload["tools"] = options.tools
            if options.tool_choice:
                payload["tool_choice"] = options.tool_choice
            if options.parallel_tool_calls is not None:
                payload["parallel_tool_calls"] = options.parallel_tool_calls

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=headers, json=payload) as resp:
                resp.raise_for_status()
                buffer = ""
                async for chunk in resp.aiter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")
                    lines = buffer.split("\n")
                    buffer = lines.pop() if lines else ""
                    for line in lines:
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            return
                        try:
                            import json
                            chunk_data = json.loads(data_str)
                            yield ChatCompletionChunk(
                                id=chunk_data.get("id", f"chatcmpl-{int(time.time())}"),
                                created=chunk_data.get("created", int(time.time())),
                                model=chunk_data.get("model", model_id),
                                choices=chunk_data.get("choices", []),
                            )
                        except json.JSONDecodeError:
                            continue

    async def validate_key(self, api_key: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}", **self.extra_headers},
                )
                return resp.status_code < 500
        except Exception:
            return False

    async def probe_capabilities(self, api_key: str) -> set[str]:
        caps: set[str] = {"chat"}
        try:
            models = await self.list_models(api_key)
            for m in models:
                if m.supports_vision:
                    caps.add("vision")
                if m.supports_embeddings:
                    caps.add("embed")
        except Exception:
            pass
        return caps

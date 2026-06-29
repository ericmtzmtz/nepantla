"""Cloudflare Workers AI provider via OpenAI-compatible endpoint."""
import json
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


class CloudflareProvider(BaseProvider):
    platform = "cloudflare"
    name = "Cloudflare Workers AI"

    @staticmethod
    def _parse_key(api_key: str) -> tuple[str, str]:
        """Parse 'account_id:api_token' into (account_id, token)."""
        sep = api_key.find(":")
        if sep == -1:
            raise ValueError('Cloudflare key must be in format "account_id:api_token"')
        return api_key[:sep], api_key[sep + 1:]

    @staticmethod
    def _normalize_messages(messages: list[ChatMessage]) -> list[dict]:
        """Flatten content to string (Cloudflare rejects null/array content)."""
        result = []
        for m in messages:
            content = m.content
            if content is None:
                content = ""
            elif isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                content = " ".join(parts) if parts else ""
            result.append({"role": m.role, "content": content})
        return result

    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        account_id, token = self._parse_key(api_key)
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"

        payload = {
            "model": model_id,
            "messages": self._normalize_messages(messages),
        }
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if not resp.is_success:
                try:
                    err_data = resp.json()
                    err_msg = (
                        err_data.get("error", {}).get("message")
                        or (err_data.get("errors") or [{}])[0].get("message")
                        or resp.text
                    )
                except Exception:
                    err_msg = resp.text
                raise RuntimeError(f"Cloudflare API error {resp.status_code}: {err_msg}")

            data = resp.json()

        data["_routed_via"] = {"platform": "cloudflare", "model": model_id}
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
        account_id, token = self._parse_key(api_key)
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1/chat/completions"

        payload = {
            "model": model_id,
            "messages": self._normalize_messages(messages),
            "stream": True,
        }
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
            async with client.stream(
                "POST", url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                if not resp.is_success:
                    try:
                        err_data = await resp.aread()
                        err_body = json.loads(err_data) if err_data else {}
                        err_msg = (
                            err_body.get("error", {}).get("message")
                            or (err_body.get("errors") or [{}])[0].get("message")
                            or resp.text
                        )
                    except Exception:
                        err_msg = resp.text
                    raise RuntimeError(f"Cloudflare API error {resp.status_code}: {err_msg}")

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
        """Validate Cloudflare token. Transport errors don't disable — only 401/403 does."""
        try:
            _, token = self._parse_key(api_key)
        except ValueError:
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.cloudflare.com/client/v4/user/tokens/verify",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code in (401, 403):
                    return False
                if not resp.is_success:
                    return True  # unexpected error — don't disable
                data = resp.json()
                return (
                    data.get("success") is True
                    and data.get("result", {}).get("status") == "active"
                )
        except Exception:
            return True  # transport error — don't disable

    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """List models via Cloudflare AI models search endpoint."""
        try:
            account_id, token = self._parse_key(api_key)
        except ValueError:
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/models/search",
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = data.get("result", []) if isinstance(data, dict) else []
        result = []
        for m in models:
            mid = m.get("id", "") or m.get("name", "")
            display = m.get("name", mid)
            result.append(ModelInfo(
                id=mid,
                platform="cloudflare",
                display_name=display,
            ))
        return result

    async def probe_capabilities(self, api_key: str) -> set[str]:
        """Cloudflare: chat only."""
        return {"chat"}

    @property
    def supports_tools(self) -> bool:
        return True

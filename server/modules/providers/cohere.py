# ruff: noqa: E501
import json
import time
from collections.abc import AsyncGenerator
from typing import ClassVar

import httpx

from server.modules.embeddings.schemas import EmbeddingObject, EmbeddingOptions, EmbeddingResponse
from server.modules.providers.base import BaseProvider
from server.modules.providers.schemas import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    ModelInfo,
)


class CohereProvider(BaseProvider):
    platform: ClassVar[str] = "cohere"
    name: ClassVar[str] = "Cohere"
    BASE_URL = "https://api.cohere.com/v2"

    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        # Convert messages to Cohere format (role/message instead of role/content)
        cohere_messages = self._convert_messages_for_cohere(messages, options)
        payload = {"model": model_id, "messages": cohere_messages}
        
        # Add tools if present
        if options and options.tools:
            payload["tools"] = self._convert_tools_for_cohere(options.tools)
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/chat",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Convert Cohere response back to OpenAI format
        return self._convert_from_cohere_response(data)

    async def stream_chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> AsyncGenerator[ChatCompletionChunk]:
        # Convert messages to Cohere format
        cohere_messages = self._convert_messages_for_cohere(messages, options)
        payload = {"model": model_id, "messages": cohere_messages}
        
        # Add tools if present
        if options and options.tools:
            payload["tools"] = self._convert_tools_for_cohere(options.tools)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/chat",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            chunk_data = json.loads(line[6:].strip())
                            if not chunk_data.get("is_final", False):
                                # Convert Cohere chunk to OpenAI chunk
                                text = chunk_data.get("text", "")
                                tool_calls = chunk_data.get("tool_calls", [])
                                
                                if tool_calls:
                                    # Convert to OpenAI tool_calls format
                                    openai_tool_calls = []
                                    for tc in tool_calls:
                                        openai_tool_calls.append({
                                            "id": f"call_{len(openai_tool_calls)}",
                                            "type": "function",
                                            "function": {
                                                "name": tc.get("name", ""),
                                                "arguments": json.dumps(tc.get("parameter", {}))
                                            }
                                        })
                                    
                                    yield ChatCompletionChunk(
                                        id=f"chunk-{int(time.time()*1000)}",
                                        created=int(time.time()),
                                        model=model_id,
                                        choices=[{
                                            "index": 0,
                                            "delta": {
                                                "tool_calls": openai_tool_calls
                                            },
                                            "finish_reason": None
                                        }]
                                    )
                                elif text:
                                    yield ChatCompletionChunk(
                                        id=f"chunk-{int(time.time()*1000)}",
                                        created=int(time.time()),
                                        model=model_id,
                                        choices=[{
                                            "index": 0,
                                            "delta": {"content": text},
                                            "finish_reason": None
                                        }]
                                    )
                        except (json.JSONDecodeError, KeyError):
                            # Skip malformed chunks
                            continue
        # Send final chunk with finish_reason
        yield ChatCompletionChunk(
            id=f"chunk-final-{int(time.time()*1000)}",
            created=int(time.time()),
            model=model_id,
            choices=[{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        )

    async def validate_key(self, api_key: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.cohere.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """GET https://api.cohere.com/v1/models, parse response."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.cohere.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = data.get("models", []) if isinstance(data, dict) else []
        result = []
        for m in models:
            mid = m.get("name", "") or m.get("id", "")
            display = m.get("name", mid)
            embed = mid.lower().startswith("embed")
            result.append(ModelInfo(
                id=mid,
                platform="cohere",
                display_name=display,
                supports_embeddings=embed,
            ))
        return result

    async def embed(
        self, api_key: str, input_text: str | list[str],
        model: str, options: EmbeddingOptions | None = None
    ) -> EmbeddingResponse:
        opts = options or EmbeddingOptions(input=input_text, model=model)
        inputs = [input_text] if isinstance(input_text, str) else input_text
        payload: dict = {
            "model": model,
            "texts": inputs,
            "input_type": opts.input_type or "search_document",
            "embedding_types": ["float"],
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/embed",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        embeddings = data.get("embeddings", {}).get("float", data.get("embeddings", []))
        if isinstance(embeddings, dict):
            embeddings = embeddings.get("float", [])
        data_list = [
            EmbeddingObject(embedding=emb, index=i)
            for i, emb in enumerate(embeddings)
        ]
        return EmbeddingResponse(data=data_list, model=model)

    async def probe_capabilities(self, api_key: str) -> set[str]:
        """Cohere: chat and embed."""
        caps: set[str] = {"chat"}
        try:
            models = await self.list_models(api_key)
            for m in models:
                if m.supports_embeddings:
                    caps.add("embed")
                    break
        except Exception:
            pass
        return caps

    @property
    def supports_tools(self) -> bool:
        return True

    def _strip_media(self, messages: list[ChatMessage]) -> list[dict]:
        result = []
        for m in messages:
            if isinstance(m.content, str):
                result.append({"role": m.role, "content": m.content})
            elif isinstance(m.content, list):
                text = " ".join(b.get("text", "") for b in m.content if b.get("type") == "text")
                result.append({"role": m.role, "content": text or "[image omitted]"})
        return result

    def _convert_messages_for_cohere(self, messages: list[ChatMessage], options: CompletionOptions | None = None) -> list[dict]:
        """Convert OpenAI messages to Cohere format (role/message instead of role/content)."""
        cohere_messages = []
        for msg in messages:
            # Handle role: "tool" messages - convert to user message with tool result
            if msg.role == "tool":
                cohere_messages.append({
                    "role": "user",
                    "message": f"Tool result: {msg.content}"
                })
            elif isinstance(msg.content, str):
                cohere_messages.append({"role": msg.role, "message": msg.content})
            elif isinstance(msg.content, list):
                # Extract text parts for Cohere
                text_parts = []
                for block in msg.content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                text = " ".join(text_parts)
                cohere_messages.append({"role": msg.role, "message": text or "[non-text content]"})
        return cohere_messages

    def _convert_tools_for_cohere(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI tools to Cohere parameter_definitions format."""
        cohere_tools = []
        for tool in tools:
            func = tool.get("function", {})
            properties = func.get("parameters", {}).get("properties", {})
            required = func.get("parameters", {}).get("required", [])
            
            parameter_definitions = {}
            for prop_name, prop_schema in properties.items():
                param_def = {
                    "description": prop_schema.get("description", ""),
                    "type": self._map_json_schema_type_to_cohere(prop_schema.get("type", "string")),
                    "required": prop_name in required
                }
                parameter_definitions[prop_name] = param_def
            
            cohere_tools.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameter_definitions": parameter_definitions,
            })
        return cohere_tools

    def _map_json_schema_type_to_cohere(self, json_type: str) -> str:
        """Map JSON Schema types to Cohere types."""
        type_map = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "array": "list",
            "object": "dict"
        }
        return type_map.get(json_type, "str")

    def _convert_from_cohere_response(self, data: dict) -> ChatCompletionResponse:
        """Convert Cohere response to OpenAI ChatCompletionResponse."""
        text = data.get("text", "")
        tool_calls = data.get("tool_calls", [])
        
        choices = []
        if tool_calls:
            # Convert Cohere tool_calls to OpenAI format
            openai_tool_calls = []
            for i, tc in enumerate(tool_calls):
                openai_tool_calls.append({
                    "id": f"call_{i}",
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": json.dumps(tc.get("parameter", {}))
                    }
                })
            
            choices.append({
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,  # When tool_calls present, content is often null in OpenAI
                    "tool_calls": openai_tool_calls
                },
                "finish_reason": "tool_calls"
            })
        else:
            # Regular text response
            choices.append({
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text
                },
                "finish_reason": "stop"
            })
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model="cohere",  # Placeholder, actual model comes from request
            choices=choices,
            usage={}  # Cohere doesn't provide token counts in the same way
        )

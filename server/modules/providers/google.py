# ruff: noqa: E501
import json
import time
from collections.abc import AsyncGenerator
from typing import ClassVar

import httpx

from server.modules.embeddings.schemas import EmbeddingObject, EmbeddingOptions, EmbeddingResponse
from server.modules.providers.base import BaseProvider
from server.modules.providers.schemas import (
    AudioTranscriptionOptions,
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    ImageGenOptions,
    ImageGenResponse,
    ModelInfo,
    TextToSpeechOptions,
    TranscriptionResponse,
)


class GoogleProvider(BaseProvider):
    platform: ClassVar[str] = "google"
    name: ClassVar[str] = "Google Gemini"
    GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

    # ponytail: track tool names for role="tool" → functionResponse name matching
    _pending_tool_names: ClassVar[dict[str, str]] = {}  # tool_call_id → function name

    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """GET Gemini /models, parse response into ModelInfo objects."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.GEMINI_BASE}/models",
                    params={"key": api_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return []

        models = data.get("models", [])
        result = []
        for m in models:
            mid = m.get("name", "").replace("models/", "")
            display = m.get("displayName", mid)
            mid_lower = mid.lower()
            vision = True
            image_gen = "imagen" in mid_lower
            embed = "embed" in mid_lower
            result.append(ModelInfo(
                id=mid,
                platform="google",
                display_name=display,
                supports_vision=vision,
                supports_image_gen=image_gen,
                supports_audio_stt=True,
                supports_audio_tts=True,
                supports_embeddings=embed,
            ))
        return result

    async def probe_capabilities(self, api_key: str) -> set[str]:
        """Detect capabilities: chat always, vision always, probe imagen/TTS."""
        caps: set[str] = {"chat", "vision", "audio_stt"}

        async def probe(path: str) -> bool:
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    r = await c.get(
                        f"{self.GEMINI_BASE}{path}",
                        params={"key": api_key},
                    )
                    return r.status_code < 500
            except Exception:
                return False

        # ponytail: imagen2 always exists under Gemini, just probe
        try:
            models = await self.list_models(api_key)
            for m in models:
                if m.supports_image_gen:
                    caps.add("image_gen")
                    break
        except Exception:
            pass

        # Probe TTS endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as c:
                r = await c.post(
                    "https://texttospeech.googleapis.com/v1/text:synthesize",
                    params={"key": api_key},
                    json={"input": {"text": "hi"}, "voice": {"languageCode": "en-US", "name": "en-US-Standard-A"}, "audioConfig": {"audioEncoding": "LINEAR16"}},
                )
                if r.status_code < 500:
                    caps.add("audio_tts")
        except Exception:
            pass

        # Detect embed from model list
        try:
            models = await self.list_models(api_key)
            for m in models:
                if m.supports_embeddings:
                    caps.add("embed")
                    break
        except Exception:
            pass

        return caps

    async def embed(
        self, api_key: str, input_text: str | list[str],
        model: str, options: EmbeddingOptions | None = None
    ) -> EmbeddingResponse:
        inputs = [input_text] if isinstance(input_text, str) else input_text
        data_list = []
        for i, text in enumerate(inputs):
            payload = {
                "content": {"parts": [{"text": text}]},
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.GEMINI_BASE}/models/{model}:embedContent",
                    params={"key": api_key},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            embedding_data = data.get("embedding", data)
            values = embedding_data.get("values", [])
            data_list.append(EmbeddingObject(embedding=values, index=i))

        return EmbeddingResponse(data=data_list, model=model)

    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        gemini_messages = self._convert_messages(messages, options)
        payload: dict = {"contents": gemini_messages}
        if options and options.tools:
            payload["tools"] = self._convert_tools(options.tools)
            if options.tool_choice:
                payload["toolConfig"] = self._convert_tool_choice(options.tool_choice)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.GEMINI_BASE}/models/{model_id}:generateContent",
                params={"key": api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return self._to_openai_response(data, model_id)

    async def stream_chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> AsyncGenerator[ChatCompletionChunk]:
        gemini_messages = self._convert_messages(messages, options)
        payload: dict = {"contents": gemini_messages}
        if options and options.tools:
            payload["tools"] = self._convert_tools(options.tools)
            if options.tool_choice:
                payload["toolConfig"] = self._convert_tool_choice(options.tool_choice)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.GEMINI_BASE}/models/{model_id}:streamGenerateContent",
                params={"key": api_key, "alt": "sse"},
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:].strip()
                        if chunk_data:
                            parsed = json.loads(chunk_data)
                            yield self._to_openai_chunk(parsed, model_id)

    async def validate_key(self, api_key: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.GEMINI_BASE}/models",
                    params={"key": api_key},
                )
                return resp.status_code == 200
        except Exception:
            return False

    @property
    def supports_tools(self) -> bool:
        return True

    async def image_generation(
        self, api_key: str, prompt: str,
        options: ImageGenOptions | None = None
    ) -> ImageGenResponse:
        """Generate image via Google Imagen (Gemini generateContent)."""
        opts = options or ImageGenOptions()

        # Map OpenAI size to Gemini aspect ratio
        size_map = {
            "1024x1024": "1:1",
            "1792x1024": "7:4",
            "1024x1792": "4:7",
        }
        aspect_ratio = size_map.get(opts.size or "1024x1024", "1:1")

        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "aspectRatio": aspect_ratio,
                "sampleCount": opts.n or 1,
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.GEMINI_BASE}/models/imagen-3.0-generate-001:generateContent",
                params={"key": api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        # Translate Gemini response to OpenAI ImageGenResponse
        images = []
        candidates = data.get("candidates", [])
        for c in candidates:
            content = c.get("content", {})
            for part in content.get("parts", []):
                if "inlineData" in part:
                    b64 = part["inlineData"].get("data", "")
                    images.append({"b64_json": b64})
                elif "image" in part:
                    b64 = part["image"].get("imageBytes", "")
                    images.append({"b64_json": b64})

        return ImageGenResponse(
            created=int(time.time()),
            data=images if images else [{"b64_json": ""}],
        )

    async def audio_transcription(
        self, api_key: str, file: bytes, filename: str,
        options: AudioTranscriptionOptions | None = None
    ) -> TranscriptionResponse:
        """Transcribe audio via Gemini generateContent with audio inline_data."""
        import base64
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
        mime_map = {"mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4", "ogg": "audio/ogg", "flac": "audio/flac"}
        mime = mime_map.get(ext, "audio/wav")
        b64 = base64.b64encode(file).decode("utf-8")

        payload = {
            "contents": [{
                "role": "user",
                "parts": [
                    {"inlineData": {"mimeType": mime, "data": b64}},
                    {"text": "Transcribe the audio in this file."},
                ],
            }],
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.GEMINI_BASE}/models/gemini-2.0-flash:generateContent",
                params={"key": api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        text = ""
        for c in data.get("candidates", []):
            for part in c.get("content", {}).get("parts", []):
                text += part.get("text", "")
        return TranscriptionResponse(text=text)

    async def text_to_speech(
        self, api_key: str, input_text: str,
        options: TextToSpeechOptions | None = None
    ) -> AsyncGenerator[bytes]:
        """Stream TTS audio from Google Cloud Text-to-Speech API."""
        opts = options or TextToSpeechOptions()
        voice_map = {"alloy": "en-US-Standard-A", "echo": "en-US-Standard-B", "fable": "en-US-Standard-C",
                     "onyx": "en-US-Standard-D", "nova": "en-US-Standard-E", "shimmer": "en-US-Standard-F"}
        voice_name = voice_map.get(opts.voice or "alloy", "en-US-Standard-A")

        payload = {
            "input": {"text": input_text},
            "voice": {"languageCode": "en-US", "name": voice_name},
            "audioConfig": {"audioEncoding": "LINEAR16"},
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                params={"key": api_key},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            import base64
            audio_bytes = base64.b64decode(data.get("audioContent", ""))
            yield audio_bytes

    def _convert_messages(self, messages: list[ChatMessage], options: CompletionOptions | None = None) -> list[dict]:
        contents = []
        for msg in messages:
            if msg.role == "tool" and options and options.tools:
                # Convert role:tool to functionResponse for Gemini
                # Find the tool name from tool_call_id (need to map from assistant message)
                tool_name = "unknown"  # fallback
                # We'll store mapping when we see assistant message with tool_calls
                # For now, try to find it in the messages we're converting
                for m in messages:
                    if m.role == "assistant" and hasattr(m, 'tool_calls') and m.tool_calls:
                        # This is approximate - in real implementation we'd need to track
                        # tool_call_id to function name mapping across turns
                        # For MVP, we'll assume first tool in list
                        if m.tool_calls and len(m.tool_calls) > 0:
                            tool_name = m.tool_calls[0].get("function", {}).get("name", "unknown")
                            break
                parts = [{"functionResponse": {"name": tool_name, "response": {"result": msg.content}}}]
                contents.append({"role": "function", "parts": parts})
            elif isinstance(msg.content, str):
                parts = [{"text": msg.content}]
            elif isinstance(msg.content, list):
                parts = []
                for block in msg.content:
                    if block.get("type") == "text":
                        parts.append({"text": block["text"]})
                    elif block.get("type") == "image_url":
                        url = block["image_url"]["url"]
                        if url.startswith("data:"):
                            parts.append({"inlineData": {"mimeType": "image/png", "data": url.split(",")[1]}})
                        else:
                            parts.append({"text": f"[Image: {url}]"})
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": parts})
        return contents

    def _convert_tools(self, tools: list[dict]) -> dict:
        """Convert OpenAI tools to Gemini functionDeclarations format."""
        function_declarations = []
        for tool in tools:
            func = tool.get("function", {})
            function_declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return {"functionDeclarations": function_declarations}

    def _convert_tool_choice(self, tool_choice: str | dict) -> dict:
        """Convert OpenAI tool_choice to Gemini toolConfig."""
        config = {"functionCallingConfig": {}}
        if tool_choice == "auto":
            config["functionCallingConfig"]["mode"] = "AUTO"
        elif tool_choice == "none":
            config["functionCallingConfig"]["mode"] = "NONE"
        elif tool_choice == "required":
            config["functionCallingConfig"]["mode"] = "ANY"
        elif isinstance(tool_choice, dict):
            if tool_choice.get("type") == "function":
                name = tool_choice.get("function", {}).get("name")
                config["functionCallingConfig"]["mode"] = "ANY"
                if name:
                    config["functionCallingConfig"]["allowedFunctionNames"] = [name]
        return config

    def _to_openai_response(self, gemini_data: dict, model_id: str) -> ChatCompletionResponse:
        import uuid as uuid_module
        candidates = gemini_data.get("candidates", [])
        choices = []
        for i, c in enumerate(candidates):
            content = c.get("content", {})
            text = ""
            tool_calls_out = []
            finish_reason = c.get("finishReason", "stop")
            for part in content.get("parts", []):
                if "text" in part:
                    text += part["text"]
                elif "functionCall" in part:
                    fc = part["functionCall"]
                    args_str = json.dumps(fc.get("args", {})) if isinstance(fc.get("args"), dict) else str(fc.get("args", "{}"))
                    tool_calls_out.append({
                        "id": f"call_{uuid_module.uuid4().hex[:8]}",
                        "type": "function",
                        "function": {"name": fc.get("name", ""), "arguments": args_str},
                    })
                    finish_reason = "tool_calls"
            if tool_calls_out:
                choices.append({
                    "index": i,
                    "message": {"role": "assistant", "content": None, "tool_calls": tool_calls_out},
                    "finish_reason": finish_reason,
                })
            else:
                choices.append({
                    "index": i,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": finish_reason,
                })
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=model_id,
            choices=choices,
        )

    def _to_openai_chunk(self, gemini_data: dict, model_id: str) -> ChatCompletionChunk:
        import uuid as uuid_module
        candidates = gemini_data.get("candidates", [{"index": 0}])
        content = candidates[0].get("content", {})
        text = ""
        tool_calls_delta = None
        finish_reason = None
        for part in content.get("parts", []):
            if "text" in part:
                text += part["text"]
            elif "functionCall" in part:
                fc = part["functionCall"]
                args_str = json.dumps(fc.get("args", {})) if isinstance(fc.get("args"), dict) else str(fc.get("args", "{}"))
                tool_calls_delta = [{
                    "id": f"call_{uuid_module.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {"name": fc.get("name", ""), "arguments": args_str},
                }]
                finish_reason = "tool_calls"
        delta = {"content": text} if not tool_calls_delta else {"content": None, "tool_calls": tool_calls_delta}
        return ChatCompletionChunk(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=model_id,
            choices=[{"index": 0, "delta": delta, "finish_reason": finish_reason}],
        )

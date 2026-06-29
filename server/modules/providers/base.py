from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import ClassVar

import httpx

from server.modules.embeddings.schemas import EmbeddingOptions, EmbeddingResponse
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


class BaseProvider(ABC):
    platform: ClassVar[str]
    name: ClassVar[str]
    _capabilities: set[str] | None = None

    @abstractmethod
    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        ...

    @abstractmethod
    async def stream_chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> AsyncGenerator[ChatCompletionChunk]:
        ...

    @abstractmethod
    async def validate_key(self, api_key: str) -> bool:
        ...

    @abstractmethod
    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """Return available models from the provider."""

    async def embed(
        self, api_key: str, input_text: str | list[str],
        model: str, options: EmbeddingOptions | None = None
    ) -> EmbeddingResponse:
        raise NotImplementedError

    async def probe_capabilities(self, api_key: str) -> set[str]:
        """Detect supported capabilities by probing endpoints. Override for custom probing."""
        caps: set[str] = {"chat"}
        base = getattr(self, "base_url", None) or getattr(self, "BASE_URL", None)
        if not base:
            return caps
        base = base.rstrip("/")

        async def probe(path: str) -> bool:
            try:
                async with httpx.AsyncClient(timeout=5.0) as c:
                    r = await c.get(f"{base}{path}", headers={"Authorization": f"Bearer {api_key}"})
                    return r.status_code < 500
            except Exception:
                return False

        if await probe("/chat/completions"):
            caps.add("chat")
        # detect capabilities via model list
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

    def _set_capabilities(self, caps: set[str]) -> None:
        self._capabilities = caps

    @property
    def supports_vision(self) -> bool:
        return self._capabilities is not None and "vision" in self._capabilities

    @property
    def supports_image_gen(self) -> bool:
        return self._capabilities is not None and "image_gen" in self._capabilities

    @property
    def supports_tools(self) -> bool:
        return False

    @property
    def supports_audio_stt(self) -> bool:
        return self._capabilities is not None and "audio_stt" in self._capabilities

    @property
    def supports_audio_tts(self) -> bool:
        return self._capabilities is not None and "audio_tts" in self._capabilities

    @property
    def supports_embeddings(self) -> bool:
        return self._capabilities is not None and "embed" in self._capabilities

    async def image_generation(
        self, api_key: str, prompt: str,
        options: ImageGenOptions | None = None
    ) -> ImageGenResponse:
        raise NotImplementedError

    async def audio_transcription(
        self, api_key: str, file: bytes, filename: str,
        options: AudioTranscriptionOptions | None = None
    ) -> TranscriptionResponse:
        raise NotImplementedError

    async def text_to_speech(
        self, api_key: str, input_text: str,
        options: TextToSpeechOptions | None = None
    ) -> AsyncGenerator[bytes]:
        raise NotImplementedError
        if False:
            yield b""

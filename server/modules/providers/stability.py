"""Stability AI provider for Stable Diffusion image generation."""
# ruff: noqa: E501

import time
from collections.abc import AsyncGenerator
from typing import ClassVar

import httpx

from server.modules.providers.base import BaseProvider
from server.modules.providers.schemas import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    ImageGenOptions,
    ImageGenResponse,
    ModelInfo,
)


class StabilityAIProvider(BaseProvider):
    platform: ClassVar[str] = "stability"
    name: ClassVar[str] = "Stability AI"
    BASE_URL = "https://api.stability.ai/v2beta"

    def __init__(self):
        self._set_capabilities({"image_gen"})

    async def chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> ChatCompletionResponse:
        raise NotImplementedError("Stability AI does not support chat completion")

    async def stream_chat_completion(
        self, api_key: str, messages: list[ChatMessage],
        model_id: str, options: CompletionOptions | None = None
    ) -> AsyncGenerator[ChatCompletionChunk]:
        raise NotImplementedError("Stability AI does not support chat completion")
        if False:
            yield b""  # pragma: no cover

    async def validate_key(self, api_key: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.stability.ai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return resp.status_code < 500
        except Exception:
            return False

    async def list_models(self, api_key: str) -> list[ModelInfo]:
        """Stability AI image generation models."""
        return [
            ModelInfo(
                id="sd3.5-large",
                platform="stability",
                display_name="Stable Diffusion 3.5 Large",
                supports_image_gen=True,
            ),
            ModelInfo(
                id="sd3.5-medium",
                platform="stability",
                display_name="Stable Diffusion 3.5 Medium",
                supports_image_gen=True,
            ),
        ]

    async def probe_capabilities(self, api_key: str) -> set[str]:
        """Stability AI: image_gen only."""
        return {"image_gen"}

    async def image_generation(
        self, api_key: str, prompt: str,
        options: ImageGenOptions | None = None
    ) -> ImageGenResponse:
        """Generate image via Stability AI API."""
        opts = options or ImageGenOptions()

        # Map OpenAI size to Stability aspect ratio
        size_map = {
            "1024x1024": "1:1",
            "1792x1024": "16:9",
            "1024x1792": "9:16",
            "768x768": "1:1",
            "1152x896": "4:3",
        }
        aspect_ratio = size_map.get(opts.size or "1024x1024", "1:1")

        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": "png",
            "mode": "text-to-image",
            "model_id": opts.model or "sd3.5-large",
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/stable-image/generate/sd3",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
                json=payload,
            )

            if resp.status_code == 429:
                raise RuntimeError("Stability AI rate limit exceeded")
            if resp.status_code == 400:
                err = resp.json().get("message", resp.text)
                raise RuntimeError(f"Stability AI request error: {err}")

            resp.raise_for_status()
            data = resp.json()

        # Stability returns base64 image directly
        b64 = data.get("image", "")
        return ImageGenResponse(
            created=int(time.time()),
            data=[{"b64_json": b64}] if b64 else [],
        )

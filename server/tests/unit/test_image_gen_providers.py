"""Unit tests for image generation provider implementations."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.modules.providers.schemas import ImageGenResponse


class TestOpenAICompatImageGen:
    @pytest.mark.asyncio
    async def test_image_gen_returns_valid_response(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider("test-platform", "https://api.test.com/v1", "Test")

        mock_data = {
            "created": 1234567890,
            "data": [{"url": "https://example.com/image.png"}],
        }

        # httpx response: .json() and .raise_for_status() are sync
        mock_response = MagicMock(
            status_code=200,
            json=MagicMock(return_value=mock_data),
            raise_for_status=MagicMock(),
        )

        # The async client instance that httpx.AsyncClient() returns
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        # patch the class so httpx.AsyncClient() returns mock_instance
        with patch("httpx.AsyncClient", return_value=mock_instance):
            resp = await provider.image_generation("test-key", "a cat")
            assert isinstance(resp, ImageGenResponse)
            assert len(resp.data) == 1
            assert "url" in resp.data[0]


class TestGoogleImageGen:
    @pytest.mark.asyncio
    async def test_image_gen_returns_valid_response(self):
        from server.modules.providers.google import GoogleProvider
        provider = GoogleProvider()

        mock_gemini_response = {
            "candidates": [{
                "content": {
                    "parts": [{"inlineData": {"data": "base64imagestring", "mimeType": "image/png"}}]  # noqa: E501
                }
            }]
        }

        mock_response = MagicMock(
            status_code=200,
            json=MagicMock(return_value=mock_gemini_response),
            raise_for_status=MagicMock(),
        )
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            resp = await provider.image_generation("test-key", "a cat")
            assert isinstance(resp, ImageGenResponse)
            assert len(resp.data) == 1
            assert "b64_json" in resp.data[0]


class TestStabilityAIImageGen:
    @pytest.mark.asyncio
    async def test_image_gen_returns_valid_response(self):
        from server.modules.providers.stability import StabilityAIProvider
        provider = StabilityAIProvider()

        mock_stability_response = {
            "image": "base64imagestring",
        }

        mock_response = MagicMock(
            status_code=200,
            json=MagicMock(return_value=mock_stability_response),
            raise_for_status=MagicMock(),
        )
        mock_instance = AsyncMock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_instance):
            resp = await provider.image_generation("test-key", "a cat")
            assert isinstance(resp, ImageGenResponse)
            assert len(resp.data) == 1
            assert "b64_json" in resp.data[0]

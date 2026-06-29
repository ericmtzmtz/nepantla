"""Unit tests for vision support in chat providers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.modules.providers.schemas import ChatMessage


class TestOpenAICompatVision:
    @pytest.mark.asyncio
    async def test_supports_vision_from_capabilities(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        provider._set_capabilities({"chat", "vision"})
        assert provider.supports_vision is True

    @pytest.mark.asyncio
    async def test_image_url_passthrough(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        provider._set_capabilities({"chat", "vision"})
        msg = ChatMessage(role="user", content=[
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ=="}},
        ])
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {
                "id": "cmpl-test", "created": 123, "model": "test-model",
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": "A cat"},
                    "finish_reason": "stop",
                }],
            }
            mock_client.return_value.__aenter__.return_value = mock_instance
            await provider.chat_completion("test-key", [msg], "test-model")
        # Verify image_url block was passed through
        call_kwargs = mock_instance.post.call_args[1]
        sent_messages = call_kwargs["json"]["messages"]
        assert len(sent_messages) == 1
        assert sent_messages[0]["content"][1]["type"] == "image_url"
        assert sent_messages[0]["content"][1]["image_url"]["url"].startswith("data:")


class TestGoogleVision:
    @pytest.mark.asyncio
    async def test_supports_vision_from_capabilities(self):
        from server.modules.providers.google import GoogleProvider
        provider = GoogleProvider()
        provider._set_capabilities({"chat", "vision"})
        assert provider.supports_vision is True

    @pytest.mark.asyncio
    async def test_image_url_to_inlinedata(self):
        from server.modules.providers.google import GoogleProvider
        provider = GoogleProvider()
        msg = ChatMessage(role="user", content=[
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQ=="}},
        ])
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "A cat"}], "role": "model"}}]
            }
            mock_client.return_value.__aenter__.return_value = mock_instance
            await provider.chat_completion("test-key", [msg], "gemini-2.0-flash")
        # Verify image_url was converted to inlineData
        call_kwargs = mock_instance.post.call_args[1]
        sent_contents = call_kwargs["json"]["contents"]
        assert len(sent_contents) == 1
        parts = sent_contents[0]["parts"]
        assert len(parts) == 2
        assert parts[0] == {"text": "What's in this image?"}
        assert "inlineData" in parts[1]
        assert parts[1]["inlineData"]["mimeType"] == "image/png"
        assert parts[1]["inlineData"]["data"] == "/9j/4AAQ=="


class TestCohereVision:
    @pytest.mark.asyncio
    async def test_strips_image_blocks(self):
        from server.modules.providers.cohere import CohereProvider
        provider = CohereProvider()
        msg = ChatMessage(role="user", content=[
            {"type": "text", "text": "Hello"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}},
        ])
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {"text": "Hi there"}
            mock_client.return_value.__aenter__.return_value = mock_instance
            await provider.chat_completion("test-key", [msg], "command-r-plus")
        call_kwargs = mock_instance.post.call_args[1]
        sent = call_kwargs["json"]["messages"]
        assert sent[0]["content"] == "Hello"  # image stripped, only text kept


class TestCloudflareVision:
    @pytest.mark.asyncio
    async def test_strips_image_blocks(self):
        from server.modules.providers.cloudflare import CloudflareProvider
        provider = CloudflareProvider(account_id="test")
        msg = ChatMessage(role="user", content=[
            {"type": "text", "text": "Hello"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}},
        ])
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {
                "result": {"response": "Hi there"}
            }
            mock_client.return_value.__aenter__.return_value = mock_instance
            await provider.chat_completion(
                "test-key", [msg], "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
            )
        call_kwargs = mock_instance.post.call_args[1]
        sent = call_kwargs["json"]["messages"]
        assert sent[0]["content"] == "Hello"

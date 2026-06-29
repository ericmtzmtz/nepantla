"""Unit tests for embedding provider implementations."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.modules.embeddings.schemas import EmbeddingOptions


class TestOpenAICompatEmbed:
    @pytest.mark.asyncio
    async def test_embed_single_input(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [{"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0}],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 1, "total_tokens": 1},
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            opts = EmbeddingOptions(input="hello", model="text-embedding-3-small")
            resp = await provider.embed("fake-key", "hello", "text-embedding-3-small", opts)

        assert len(resp.data) == 1
        assert resp.data[0].embedding == [0.1, 0.2, 0.3]
        assert resp.model == "text-embedding-3-small"
        assert resp.usage.prompt_tokens == 1

    @pytest.mark.asyncio
    async def test_embed_batch_input(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"object": "embedding", "embedding": [0.1], "index": 0},
                {"object": "embedding", "embedding": [0.2], "index": 1},
            ],
            "model": "text-embedding-3-small",
            "usage": {"prompt_tokens": 2, "total_tokens": 2},
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            opts = EmbeddingOptions(input=["hello", "world"], model="text-embedding-3-small")
            resp = await provider.embed(
                "fake-key", ["hello", "world"], "text-embedding-3-small", opts)

        assert len(resp.data) == 2
        assert resp.data[0].embedding == [0.1]
        assert resp.data[1].embedding == [0.2]


class TestGoogleEmbed:
    @pytest.mark.asyncio
    async def test_embed_single_input(self):
        from server.modules.providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "embedding": {"values": [0.5, 0.6, 0.7]},
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            opts = EmbeddingOptions(input="hello", model="text-embedding-004")
            resp = await provider.embed("fake-key", "hello", "text-embedding-004", opts)

        assert len(resp.data) == 1
        assert resp.data[0].embedding == [0.5, 0.6, 0.7]


class TestCohereEmbed:
    @pytest.mark.asyncio
    async def test_embed_single_input(self):
        from server.modules.providers.cohere import CohereProvider

        provider = CohereProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "embeddings": {"float": [[0.1, 0.2]]},
            "model": "embed-english-v3.0",
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            opts = EmbeddingOptions(input="hello", model="embed-english-v3.0")
            resp = await provider.embed("fake-key", "hello", "embed-english-v3.0", opts)

        assert len(resp.data) == 1
        assert resp.data[0].embedding == [0.1, 0.2]

"""Unit tests for provisioning: list_models + probe + sync."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.modules.providers.schemas import ModelInfo


class TestOpenAICompatListModels:
    @pytest.mark.asyncio
    async def test_list_models_parses_response(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"id": "gpt-4o", "name": "GPT-4o"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            models = await provider.list_models("fake-key")

        assert len(models) == 2
        assert models[0].id == "gpt-4o"
        assert models[0].platform == "test"
        assert models[0].supports_vision is True  # "gpt-4o" contains vision keyword

    @pytest.mark.asyncio
    async def test_list_models_empty_on_error(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.get = AsyncMock(side_effect=Exception("connection error"))
            mock_client.return_value.__aenter__.return_value = instance
            models = await provider.list_models("fake-key")

        assert models == []

    @pytest.mark.asyncio
    async def test_probe_capabilities_detects_vision(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider

        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")

        async def fake_list_models(api_key):
            return [ModelInfo(id="gpt-4o", platform="test", supports_vision=True)]

        with patch.object(provider, "list_models", fake_list_models):
            with patch("httpx.AsyncClient") as mock_client:
                instance = MagicMock()
                # Return 200 for /models, 404 for everything else
                response_200 = MagicMock(status_code=200)
                response_200.raise_for_status = MagicMock()
                response_404 = MagicMock(status_code=404)
                instance.get = AsyncMock(return_value=response_404)
                instance.request = AsyncMock(return_value=response_404)
                mock_client.return_value.__aenter__.return_value = instance
                caps = await provider.probe_capabilities("fake-key")

        assert "chat" in caps
        assert "vision" in caps


class TestGoogleListModels:
    @pytest.mark.asyncio
    async def test_list_models_parses_response(self):
        from server.modules.providers.google import GoogleProvider

        provider = GoogleProvider()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "models/gemini-2.0-flash", "displayName": "Gemini 2.0 Flash"},
                {"name": "models/imagen-3.0-generate-001", "displayName": "Imagen 3"},
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = instance
            models = await provider.list_models("fake-key")

        assert len(models) == 2
        assert models[0].id == "gemini-2.0-flash"
        assert models[0].platform == "google"
        assert models[0].supports_vision is True
        assert models[1].supports_image_gen is True  # "imagen" in id

    @pytest.mark.asyncio
    async def test_list_models_empty_on_error(self):
        from server.modules.providers.google import GoogleProvider

        provider = GoogleProvider()
        with patch("httpx.AsyncClient") as mock_client:
            instance = MagicMock()
            instance.get = AsyncMock(side_effect=Exception("connection error"))
            mock_client.return_value.__aenter__.return_value = instance
            models = await provider.list_models("fake-key")

        assert models == []

    @pytest.mark.asyncio
    async def test_probe_capabilities_always_has_chat_vision(self):
        from server.modules.providers.google import GoogleProvider

        provider = GoogleProvider()
        # Mock list_models and the TTS probe
        with patch.object(provider, "list_models", return_value=[
            ModelInfo(id="gemini-2.0-flash", platform="google", supports_vision=True),
        ]):
            with patch("httpx.AsyncClient") as mock_client:
                instance = MagicMock()
                instance.get = AsyncMock(return_value=MagicMock(status_code=404))
                instance.post = AsyncMock(return_value=MagicMock(status_code=404))
                mock_client.return_value.__aenter__.return_value = instance
                caps = await provider.probe_capabilities("fake-key")

        assert "chat" in caps
        assert "vision" in caps
        assert "audio_stt" in caps


class TestProvisioningSyncAll:
    @pytest.mark.asyncio
    async def test_sync_all_dry_run_returns_changes(self):
        from server.modules.provisioning.services import ProvisioningService

        # Mock the DB and ProviderRegistry
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()

        # Create a fake ProviderCatalog-like object
        fake_catalog_entry = MagicMock()
        fake_catalog_entry.platform = "test"
        fake_catalog_entry.model_id = "old-model"
        fake_catalog_entry.display_name = "Old Model"
        fake_catalog_entry.supports_vision = False
        fake_catalog_entry.supports_image_gen = False
        fake_catalog_entry.supports_audio_stt = False
        fake_catalog_entry.supports_audio_tts = False

        # Mock the existing catalog query (empty for new model discovery)
        scalas = MagicMock()
        scalas.all.return_value = [fake_catalog_entry]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalas
        mock_db.execute.return_value = result_mock

        fake_provider = MagicMock()
        fake_provider._platform = "test"
        fake_provider.list_models = AsyncMock(return_value=[
            ModelInfo(
                id="new-model", platform="test",
                display_name="New Model", supports_vision=True,
            ),
        ])

        with patch("server.modules.providers.registry.ProviderRegistry") as mock_registry:
            mock_registry.all.return_value = [fake_provider]
            with patch("server.core.database.AsyncSessionLocal") as mock_session_cls:
                mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_db)
                mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                changes = await ProvisioningService.sync_all(dry_run=True)

        # Should discover "new-model" (INSERT) and "old-model" (DISABLE)
        actions = [c["action"] for c in changes]
        assert "INSERT" in actions
        assert "DISABLE" in actions
        # Find the INSERT change for new-model
        insert_changes = [c for c in changes if c["action"] == "INSERT"]
        assert any(c["model_id"] == "new-model" for c in insert_changes)

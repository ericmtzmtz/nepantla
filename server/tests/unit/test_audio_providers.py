"""Unit tests for audio (STT/TTS) support in providers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOpenAICompatAudio:
    @pytest.mark.asyncio
    async def test_supports_audio_stt_from_capabilities(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        provider._set_capabilities({"chat", "audio_stt", "audio_tts"})
        assert provider.supports_audio_stt is True
        assert provider.supports_audio_tts is True

    @pytest.mark.asyncio
    async def test_audio_transcription_mocked(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        from server.modules.providers.schemas import AudioTranscriptionOptions
        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        provider._set_capabilities({"chat", "audio_stt"})
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {"text": "Hello world"}
            mock_client.return_value.__aenter__.return_value = mock_instance

            resp = await provider.audio_transcription(
                "test-key", b"fake audio bytes", "test.wav",
                AudioTranscriptionOptions(),
            )
            assert resp.text == "Hello world"

        # Verify multipart POST was sent correctly
        call_args = mock_instance.post.call_args
        assert "/audio/transcriptions" in call_args[0][0]
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_text_to_speech_mocked(self):
        from server.modules.providers.openai_compat import OpenAICompatProvider
        from server.modules.providers.schemas import TextToSpeechOptions
        provider = OpenAICompatProvider("test", "https://api.test.com/v1", "Test")
        provider._set_capabilities({"chat", "audio_tts"})
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            # Mock streaming response
            mock_stream = MagicMock()
            mock_stream.__aenter__.return_value = mock_stream
            mock_stream.aiter_bytes.return_value.__aiter__.return_value = [b"audio data"]
            mock_stream.raise_for_status = lambda: None
            mock_instance.stream.return_value = mock_stream

            chunks = []
            async for chunk in provider.text_to_speech("test-key", "Hello", TextToSpeechOptions()):
                chunks.append(chunk)

            assert b"".join(chunks) == b"audio data"

        # Verify POST to /audio/speech
        call_args = mock_instance.stream.call_args
        assert "/audio/speech" in call_args[0][1]
        assert call_args[1]["json"]["input"] == "Hello"
        assert call_args[1]["json"]["model"] == "tts-1"


class TestGoogleAudio:
    @pytest.mark.asyncio
    async def test_supports_audio_flags(self):
        from server.modules.providers.google import GoogleProvider
        provider = GoogleProvider()
        provider._set_capabilities({"chat", "audio_stt", "audio_tts"})
        assert provider.supports_audio_stt is True
        assert provider.supports_audio_tts is True

    @pytest.mark.asyncio
    async def test_audio_transcription_mocked(self):
        from server.modules.providers.google import GoogleProvider
        from server.modules.providers.schemas import AudioTranscriptionOptions
        provider = GoogleProvider()
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {
                "candidates": [{"content": {"parts": [{"text": "Hello world"}], "role": "model"}}]
            }
            mock_client.return_value.__aenter__.return_value = mock_instance

            resp = await provider.audio_transcription(
                "test-key", b"fake audio", "test.mp3",
                AudioTranscriptionOptions(),
            )
            assert resp.text == "Hello world"

        # Verify Gemini generateContent was called
        call_args = mock_instance.post.call_args
        assert "generateContent" in call_args[0][0]
        contents = call_args[1]["json"]["contents"]
        assert len(contents) == 1
        parts = contents[0]["parts"]
        assert parts[0]["inlineData"]["mimeType"] == "audio/mpeg"
        assert "Transcribe" in parts[1]["text"]

    @pytest.mark.asyncio
    async def test_text_to_speech_mocked(self):
        from server.modules.providers.google import GoogleProvider
        from server.modules.providers.schemas import TextToSpeechOptions
        provider = GoogleProvider()
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                status_code=200, raise_for_status=lambda: None
            )
            mock_instance.post.return_value.json.return_value = {
                "audioContent": "bHlhbW9uIGFuZCB2aW9sZXQ="
            }
            mock_client.return_value.__aenter__.return_value = mock_instance

            chunks = []
            async for chunk in provider.text_to_speech("test-key", "Hello world", TextToSpeechOptions()):  # noqa: E501
                chunks.append(chunk)

            assert b"".join(chunks) == b"lyamon and violet"

        # Verify TTS API call
        call_args = mock_instance.post.call_args
        assert "texttospeech.googleapis.com" in call_args[0][0]
        assert call_args[1]["json"]["input"]["text"] == "Hello world"
        assert call_args[1]["json"]["voice"]["name"] == "en-US-Standard-A"
        assert call_args[1]["json"]["audioConfig"]["audioEncoding"] == "LINEAR16"

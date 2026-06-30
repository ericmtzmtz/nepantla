"""Unit tests for context-aware routing: _estimate_input_tokens."""

from server.modules.proxy.api import _estimate_input_tokens
from server.modules.providers.schemas import ChatMessage


class TestEstimateInputTokens:
    def test_empty_messages(self):
        """Empty message list should return 0."""
        assert _estimate_input_tokens([]) == 0

    def test_text_only(self):
        """Text only: tokens = len(text) // 4."""
        msgs = [ChatMessage(role="user", content="Hello world")]
        assert _estimate_input_tokens(msgs) == len("Hello world") // 4

    def test_multiple_text_messages(self):
        """Multiple messages should sum their token estimates."""
        msgs = [
            ChatMessage(role="user", content="Short"),
            ChatMessage(role="assistant", content="A bit longer message here"),
        ]
        expected = len("Short") // 4 + len("A bit longer message here") // 4
        assert _estimate_input_tokens(msgs) == expected

    def test_text_with_image(self):
        """Image blocks should add ~258 tokens each."""
        msgs = [ChatMessage(role="user", content=[
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,x"}},
        ])]
        expected = len("Describe this") // 4 + 258
        assert _estimate_input_tokens(msgs) == expected

    def test_multiple_images(self):
        """Multiple images, each estimated at 258 tokens."""
        msgs = [ChatMessage(role="user", content=[
            {"type": "text", "text": "Compare"},
            {"type": "image_url", "image_url": {"url": "data:img1"}},
            {"type": "image_url", "image_url": {"url": "data:img2"}},
        ])]
        expected = len("Compare") // 4 + 258 + 258
        assert _estimate_input_tokens(msgs) == expected

    def test_large_text(self):
        """Large text should scale linearly."""
        text = "A" * 4000  # ~1000 tokens at 4 chars/token
        msgs = [ChatMessage(role="user", content=text)]
        assert _estimate_input_tokens(msgs) == 1000

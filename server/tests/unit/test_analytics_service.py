"""Unit tests for AnalyticsService (buffer, aggregate, cleanup)."""
import pytest

from server.modules.analytics.services import AnalyticsService


class TestAnalyticsBuffer:
    @pytest.mark.asyncio
    async def test_record_request_buffers(self):
        AnalyticsService._buffer = __import__("asyncio").Queue()
        await AnalyticsService.record_request(
            None, "chat", "test_platform", "test_model", 1,
            "success", 10, 20,
        )
        assert AnalyticsService._buffer.qsize() == 1
        item = AnalyticsService._buffer.get_nowait()
        assert item["type"] == "chat"
        assert item["platform"] == "test_platform"
        assert item["model_id"] == "test_model"
        assert item["status"] == "success"

    @pytest.mark.asyncio
    async def test_record_request_with_error(self):
        AnalyticsService._buffer = __import__("asyncio").Queue()
        await AnalyticsService.record_request(
            None, "chat", "p", "m", None, "error", error="test_error",
        )
        item = AnalyticsService._buffer.get_nowait()
        assert item["status"] == "error"
        assert item["error"] == "test_error"
        assert item["key_id"] is None

# ruff: noqa: E501
import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.config import settings
from server.core.database import AsyncSessionLocal
from server.modules.analytics.models import Request


class AnalyticsService:
    _buffer: asyncio.Queue = asyncio.Queue()
    _worker_task: asyncio.Task | None = None

    @classmethod
    async def record_request(
        cls,
        db: AsyncSession,
        type: str,
        platform: str,
        model_id: str,
        key_id: uuid.UUID | None,
        status: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        error: str | None = None,
    ) -> None:
        """Buffer a request for batch insert."""
        await cls._buffer.put({
            "type": type, "platform": platform, "model_id": model_id,
            "key_id": key_id, "status": status,
            "input_tokens": input_tokens, "output_tokens": output_tokens,
            "latency_ms": latency_ms, "error": error,
        })

    @classmethod
    async def _buffer_worker(cls):
        """Flush buffer every N seconds or when it reaches N items."""
        batch: list[dict] = []
        last_flush = time.time()

        while True:
            try:
                item = await asyncio.wait_for(
                    cls._buffer.get(), timeout=settings.ANALYTICS_BUFFER_SECONDS
                )
                batch.append(item)
            except TimeoutError:
                pass

            elapsed = time.time() - last_flush
            if batch and (
                elapsed >= settings.ANALYTICS_BUFFER_SECONDS
                or len(batch) >= settings.ANALYTICS_BUFFER_MAX_ITEMS
            ):
                await cls._flush_batch(batch)
                batch.clear()
                last_flush = time.time()

    @classmethod
    async def _flush_batch(cls, batch: list[dict]) -> None:
        """Batch INSERT requests."""
        if not batch:
            return
        try:
            async with AsyncSessionLocal() as db:
                for item in batch:
                    db.add(Request(**item))
                await db.commit()
        except Exception as e:
            print(f"[Analytics] Flush error: {e}")

    @classmethod
    def start(cls):
        """Start the buffer worker."""
        if cls._worker_task is None:
            cls._worker_task = asyncio.create_task(cls._buffer_worker())

    @classmethod
    async def aggregate_hourly(cls) -> None:
        """Cron: aggregate requests into hourly_agg."""
        async with AsyncSessionLocal() as db:
            hour_ago = datetime.now(UTC) - timedelta(hours=1)
            hour_col = func.date_trunc("hour", Request.created_at)
            result = await db.execute(
                select(
                    hour_col.label("hour"),
                    Request.type,
                    Request.platform,
                    Request.model_id,
                    func.count().label("requests"),
                    func.sum(case((Request.status == "success", 1), else_=0)).label("success_count"),
                    func.sum(case((Request.status != "success", 1), else_=0)).label("failure_count"),
                    func.sum(Request.input_tokens).label("total_input_tokens"),
                    func.sum(Request.output_tokens).label("total_output_tokens"),
                    func.avg(Request.latency_ms).label("avg_latency"),
                )
                .where(Request.created_at >= hour_ago)
                .group_by(
                    hour_col,
                    Request.type, Request.platform, Request.model_id,
                )
            )
            rows = result.all()
            for row in rows:
                stmt = text("""
                    INSERT INTO hourly_agg (hour, type, platform, model_id, requests, success_count, failure_count, total_input_tokens, total_output_tokens, avg_latency_ms)
                    VALUES (:hour, :type, :platform, :model_id, :requests, :success_count, :failure_count, :total_input_tokens, :total_output_tokens, :avg_latency)
                    ON CONFLICT (hour, type, platform, model_id)
                    DO UPDATE SET
                        requests = hourly_agg.requests + :requests,
                        success_count = hourly_agg.success_count + :success_count,
                        failure_count = hourly_agg.failure_count + :failure_count,
                        total_input_tokens = hourly_agg.total_input_tokens + :total_input_tokens,
                        total_output_tokens = hourly_agg.total_output_tokens + :total_output_tokens,
                        avg_latency_ms = (hourly_agg.avg_latency_ms + :avg_latency) / 2
                """)
                await db.execute(stmt, {
                    "hour": row.hour, "type": row.type, "platform": row.platform,
                    "model_id": row.model_id, "requests": row.requests,
                    "success_count": row.success_count, "failure_count": row.failure_count,
                    "total_input_tokens": row.total_input_tokens or 0,
                    "total_output_tokens": row.total_output_tokens or 0,
                    "avg_latency": row.avg_latency or 0,
                })
            await db.commit()

    @classmethod
    async def cleanup_old_requests(cls) -> None:
        """Cron: delete requests older than retention days."""
        cutoff = datetime.now(UTC) - timedelta(days=settings.CLEANUP_RETENTION_DAYS)
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("DELETE FROM requests WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
            await db.commit()

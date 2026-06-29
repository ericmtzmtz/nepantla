from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.core.database import get_db
from server.modules.analytics.models import HourlyAgg, Request

router = APIRouter()


def _parse_range(range_str: str = "7d") -> timedelta:
    if range_str == "24h":
        return timedelta(hours=24)
    if range_str == "30d":
        return timedelta(days=30)
    return timedelta(days=7)


@router.get("/api/analytics/summary")
async def get_analytics_summary(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    result = await db.execute(
        select(
            func.count().label("total_requests"),
            func.sum(case((Request.status == "success", 1), else_=0)).label("success_count"),
            func.coalesce(func.sum(Request.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(Request.output_tokens), 0).label("total_output_tokens"),
            func.avg(Request.latency_ms).label("avg_latency_ms"),
        ).where(Request.created_at >= since)
    )
    row = result.one()
    total = row.total_requests or 0
    input_cost = (row.total_input_tokens / 1_000_000) * 3
    output_cost = (row.total_output_tokens / 1_000_000) * 15
    return {
        "totalRequests": total,
        "successRate": round((row.success_count / total) * 100, 1) if total else 0,
        "totalInputTokens": row.total_input_tokens,
        "totalOutputTokens": row.total_output_tokens,
        "avgLatencyMs": round(row.avg_latency_ms or 0),
        "estimatedCostSavings": round(input_cost + output_cost, 2),
    }


@router.get("/api/analytics/by-platform")
async def get_analytics_by_platform(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    result = await db.execute(
        select(
            Request.platform,
            func.count().label("requests"),
            func.sum(case((Request.status == "success", 1), else_=0)).label("success_count"),
            func.avg(Request.latency_ms).label("avg_latency_ms"),
            func.coalesce(func.sum(Request.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(Request.output_tokens), 0).label("total_output_tokens"),
        )
        .where(Request.created_at >= since)
        .group_by(Request.platform)
        .order_by(func.count().desc())
    )
    return [
        {
            "platform": r.platform,
            "requests": r.requests,
            "successRate": round((r.success_count / r.requests) * 100, 1) if r.requests else 0,
            "avgLatencyMs": round(r.avg_latency_ms or 0),
            "totalInputTokens": r.total_input_tokens,
            "totalOutputTokens": r.total_output_tokens,
        }
        for r in result.all()
    ]


@router.get("/api/analytics/timeline")
async def get_analytics_timeline(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    trunc = func.date_trunc("hour" if range == "24h" else "day", Request.created_at)
    result = await db.execute(
        select(
            trunc.label("timestamp"),
            func.count().label("requests"),
            func.sum(case((Request.status == "success", 1), else_=0)).label("success_count"),
            func.sum(case((Request.status == "error", 1), else_=0)).label("failure_count"),
        )
        .where(Request.created_at >= since)
        .group_by(trunc)
        .order_by(trunc)
    )
    return [
        {
            "timestamp": str(r.timestamp),
            "requests": r.requests,
            "successCount": r.success_count or 0,
            "failureCount": r.failure_count or 0,
        }
        for r in result.all()
    ]


@router.get("/api/analytics/by-model")
async def get_analytics_by_model(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    result = await db.execute(
        select(
            Request.platform,
            Request.model_id,
            func.count().label("requests"),
            func.sum(case((Request.status == "success", 1), else_=0)).label("success_count"),
            func.avg(Request.latency_ms).label("avg_latency_ms"),
            func.coalesce(func.sum(Request.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(Request.output_tokens), 0).label("total_output_tokens"),
        )
        .where(Request.created_at >= since)
        .group_by(Request.platform, Request.model_id)
        .order_by(func.count().desc())
    )
    return [
        {
            "platform": r.platform,
            "modelId": r.model_id,
            "displayName": r.model_id,
            "requests": r.requests,
            "successRate": round((r.success_count / r.requests) * 100, 1) if r.requests else 0,
            "avgLatencyMs": round(r.avg_latency_ms or 0),
            "totalInputTokens": r.total_input_tokens,
            "totalOutputTokens": r.total_output_tokens,
        }
        for r in result.all()
    ]


@router.get("/api/analytics/error-distribution")
async def get_error_distribution(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    """Error distribution with byCategory, byPlatform, and detailed breakdowns."""
    since = datetime.now(UTC) - _parse_range(range)
    cat_case = case(
        (Request.error.like("%429%"), "Rate Limited (429)"),
        (Request.error.like("%401%"), "Auth Error (401)"),
        (Request.error.like("%403%"), "Forbidden (403)"),
        (Request.error.like("%404%"), "Not Found (404)"),
        (Request.error.like("%timeout%"), "Timeout/Connection"),
        (Request.error.like("%500%"), "Server Error (500)"),
        (Request.error.like("%503%"), "Unavailable (503)"),
        else_="Other",
    )
    by_category = await db.execute(
        select(cat_case.label("category"), func.count().label("count"))
        .where(Request.created_at >= since, Request.status == "error", Request.error.isnot(None))
        .group_by(cat_case)
        .order_by(func.count().desc())
    )
    by_platform = await db.execute(
        select(Request.platform, func.count().label("count"))
        .where(Request.created_at >= since, Request.status == "error")
        .group_by(Request.platform)
        .order_by(func.count().desc())
    )
    detailed = await db.execute(
        select(
            Request.platform, Request.model_id, Request.error,
            cat_case.label("error_category"), func.count().label("count"),
        )
        .where(Request.created_at >= since, Request.status == "error", Request.error.isnot(None))
        .group_by(Request.platform, Request.model_id, Request.error, cat_case)
        .order_by(func.count().desc())
    )
    return {
        "byCategory": [{"category": r.category, "count": r.count} for r in by_category.all()],
        "byPlatform": [{"platform": r.platform, "count": r.count} for r in by_platform.all()],
        "detailed": [
            {
                "platform": r.platform, "model_id": r.model_id,
                "error": r.error, "error_category": r.error_category,
                "count": r.count,
            }
            for r in detailed.all()
        ],
    }


@router.get("/api/analytics/errors")
async def get_errors(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    result = await db.execute(
        select(
            Request.created_at,
            Request.platform,
            Request.model_id,
            Request.error,
            Request.latency_ms,
        )
        .where(Request.created_at >= since)
        .where(Request.status == "error")
        .where(Request.error.isnot(None))
        .order_by(Request.created_at.desc())
        .limit(50)
    )
    return [
        {
            "id": str(r.created_at),
            "platform": r.platform,
            "modelId": r.model_id,
            "error": r.error,
            "latencyMs": r.latency_ms,
            "createdAt": str(r.created_at),
        }
        for r in result.all()
    ]


@router.get("/api/analytics/providers")
async def get_providers(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(hours=hours)
    result = await db.execute(
        select(
            Request.platform,
            func.count().label("requests"),
            func.sum(case((Request.status == "error", 1), else_=0)).label("errors"),
            func.avg(Request.latency_ms).label("avg_latency"),
        )
        .where(Request.created_at >= since)
        .group_by(Request.platform)
        .order_by(func.count().desc())
    )
    return [
        {
            "platform": r.platform,
            "requests": r.requests,
            "errors": r.errors or 0,
            "avg_latency": float(r.avg_latency or 0),
        }
        for r in result.all()
    ]


@router.get("/api/analytics/usage")
async def get_usage(
    range: str = "7d",
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - _parse_range(range)
    trunc = func.date_trunc("hour" if range == "24h" else "day", HourlyAgg.hour)
    result = await db.execute(
        select(
            trunc.label("hour"),
            func.coalesce(func.sum(HourlyAgg.total_input_tokens + HourlyAgg.total_output_tokens), 0).label("tokens"),
        )
        .where(HourlyAgg.hour >= since)
        .group_by(trunc)
        .order_by(trunc)
    )
    return [{"hour": str(r.hour), "tokens": r.tokens} for r in result.all()]


@router.get("/api/analytics/dashboard")
async def get_dashboard(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(UTC) - timedelta(days=days)
    # aggregates across all rows
    agg = await db.execute(
        select(
            func.coalesce(func.sum(HourlyAgg.requests), 0).label("total_requests"),
            func.coalesce(func.sum(HourlyAgg.success_count), 0).label("total_success"),
            func.coalesce(func.sum(HourlyAgg.failure_count), 0).label("total_errors"),
        ).where(HourlyAgg.hour >= since)
    )
    row = agg.one()
    total = row.total_requests
    total_errors = row.total_errors

    # active providers
    prov = await db.execute(
        select(func.count(func.distinct(HourlyAgg.platform)))
        .where(HourlyAgg.hour >= since)
    )
    active_providers = prov.scalar() or 0

    # per-hour volume
    vol = await db.execute(
        select(
            HourlyAgg.hour,
            func.sum(HourlyAgg.requests).label("requests"),
        )
        .where(HourlyAgg.hour >= since)
        .group_by(HourlyAgg.hour)
        .order_by(HourlyAgg.hour)
    )
    request_volume = [{"hour": str(r.hour), "requests": r.requests} for r in vol.all()]

    return {
        "total_requests": total,
        "success_rate": (total - total_errors) / total if total else 1.0,
        "active_providers": active_providers,
        "error_count": total_errors,
        "request_volume": request_volume,
    }

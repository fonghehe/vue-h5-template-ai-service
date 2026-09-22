"""Operational endpoints: liveness and readiness probes."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from app import __version__
from app.core.security import RateLimiterDep, SettingsDep
from app.schemas.envelope import ApiResponse, HealthData

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


@router.get("/health", summary="Liveness probe")
async def health(request: Request, settings: SettingsDep) -> ApiResponse[HealthData]:
    """Report that the process is running.

    Never touches external dependencies: a database or Redis outage must not
    restart-loop the service, only remove it from the load balancer.
    """
    return ApiResponse(
        data=HealthData(
            service="ai",
            status="ok",
            env=settings.app_env,
            version=__version__,
            provider=settings.ai_provider,
            rate_limiter="redis" if settings.redis_url else "memory",
        ),
        requestId=getattr(request.state, "request_id", None),
    )


@router.get("/ready", summary="Readiness probe")
async def ready(request: Request, settings: SettingsDep, limiter: RateLimiterDep) -> JSONResponse:
    """Report whether the service can serve traffic right now."""

    async def probe(call: object) -> bool:
        try:
            async with asyncio.timeout(settings.readiness_timeout_seconds):
                return bool(await call())  # type: ignore[operator]
        except Exception:
            return False

    limiters_up, database_up = await asyncio.gather(probe(limiter.ping), probe(request.app.state.database.ping))
    dependencies_up = limiters_up and database_up
    payload: ApiResponse[HealthData] = ApiResponse(
        data=HealthData(
            service="ai",
            status="ready" if dependencies_up else "degraded",
            env=settings.app_env,
            version=__version__,
            provider=settings.ai_provider,
            rate_limiter=getattr(limiter, "name", "unknown"),
        ),
        requestId=getattr(request.state, "request_id", None),
    )
    # Required dependencies fail readiness without exposing connection details.
    status_code = 200 if dependencies_up else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))


@router.get("/metrics", include_in_schema=False)
async def metrics(settings: SettingsDep) -> Response:
    if not settings.metrics_enabled:
        return Response(status_code=404)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

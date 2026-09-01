"""Operational endpoints: liveness and readiness probes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

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
            rate_limiter=settings.redis_url.rsplit(":", 1)[0] if settings.redis_url else "memory",
        ),
        requestId=getattr(request.state, "request_id", None),
    )


@router.get("/ready", summary="Readiness probe")
async def ready(request: Request, settings: SettingsDep, limiter: RateLimiterDep) -> JSONResponse:
    """Report whether the service can serve traffic right now."""
    limiters_up = await limiter.ping()
    payload: ApiResponse[HealthData] = ApiResponse(
        data=HealthData(
            service="ai",
            status="ready" if limiters_up else "degraded",
            env=settings.app_env,
            version=__version__,
            provider=settings.ai_provider,
            rate_limiter=getattr(limiter, "name", "unknown"),
        ),
        requestId=getattr(request.state, "request_id", None),
    )
    # A degraded limiter is not fatal: the service fails open rather than
    # dropping chat, but orchestrators should still see it as unhealthy.
    status_code = 200 if limiters_up else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump(by_alias=True))

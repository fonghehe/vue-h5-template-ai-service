"""The JSON envelope shared with the business service and the frontend client."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiResponse[DataT](BaseModel):
    """Response envelope.

    Mirrors the contract enforced by `createApiClient` in `@vh5/api-client`:
    the frontend branches on `code == 0` and requires `data` to be present even
    for empty payloads, so it is never omitted.
    """

    model_config = ConfigDict(populate_by_name=True)

    code: int = Field(default=0, description="0 on success; a stable error code otherwise")
    message: str = Field(default="ok", description="Human readable, user-safe summary")
    data: DataT | None = None
    error: Any | None = Field(default=None, description="Structured, user-safe error detail")
    request_id: str | None = Field(default=None, alias="requestId")


class HealthData(BaseModel):
    """Payload of the health and readiness probes."""

    model_config = ConfigDict(populate_by_name=True)

    service: str
    status: str
    env: str
    version: str
    provider: str
    rate_limiter: str = Field(alias="rateLimiter")


class ErrorDetail(BaseModel):
    """Structured, user-safe error detail attached to a failed response."""

    code: int
    reason: str | None = None

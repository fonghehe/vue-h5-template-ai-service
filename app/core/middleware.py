"""Pure ASGI request context, body limits, headers and full-stream timing."""

from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_scope
from app.core.observability import HTTP_ACTIVE, HTTP_DURATION, HTTP_REQUESTS, span

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, max_request_bytes: int = 6_000_000) -> None:
        self.app, self.max_request_bytes = app, max_request_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming if _ID.fullmatch(incoming) else str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started, status_code, received = time.perf_counter(), 500, 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    raise HTTPException(413, "Request body is too large")
            return message

        async def contextual_send(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                headers["X-Content-Type-Options"] = "nosniff"
                headers["Referrer-Policy"] = "no-referrer"
            await send(message)

        HTTP_ACTIVE.inc()
        try:
            with (
                request_scope(requestId=request_id, method=scope["method"]),
                span("http.request", request_id=request_id),
            ):
                await self.app(scope, limited_receive, contextual_send)
        finally:
            duration = time.perf_counter() - started
            route = getattr(scope.get("route"), "path", "unmatched")
            if route.startswith("/") and not route.startswith("/api/") and scope["path"].startswith("/api/"):
                route = ("/api/v1" if scope["path"].startswith("/api/v1/") else "/api") + route
            HTTP_ACTIVE.dec()
            HTTP_REQUESTS.labels(method=scope["method"], route=route, status=str(status_code)).inc()
            HTTP_DURATION.labels(method=scope["method"], route=route).observe(duration)
            logger.info(
                "http request completed",
                extra={
                    "requestId": request_id,
                    "method": scope["method"],
                    "path": route,
                    "status": status_code,
                    "durationMs": round(duration * 1000, 2),
                },
            )

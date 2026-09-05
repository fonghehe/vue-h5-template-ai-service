"""Application factory and ASGI entrypoint."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import CODE_INTERNAL, CODE_VALIDATION, AppError
from app.core.logging import configure_logging
from app.core.observability import configure_tracing, span
from app.db.session import Database
from app.providers.factory import create_chat_provider, create_embedding_provider
from app.schemas.envelope import ApiResponse
from app.services.agent import AgentWorkflow
from app.services.context import ContextBuilder
from app.services.locks import ConversationLockManager, StreamQuota
from app.services.model_router import ModelRouter
from app.services.prompts import PromptRegistry
from app.services.rate_limit import build_rate_limiter
from app.tools.base import ToolRegistry
from app.tools.builtin import CalculatorTool, CurrentTimeTool, ProductSearchTool

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create and dispose of process-wide dependencies."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    if settings.otel_enabled:
        configure_tracing(settings.otel_service_name)

    app.state.settings = settings
    app.state.chat_provider = create_chat_provider(settings)
    app.state.embedding_provider = create_embedding_provider(settings)
    app.state.rate_limiter = build_rate_limiter(settings.redis_url)
    app.state.database = Database.create(settings.database_url)
    if settings.database_auto_create:
        await app.state.database.create_schema()
    app.state.model_router = ModelRouter(settings)
    app.state.prompt_registry = PromptRegistry()
    app.state.context_builder = ContextBuilder(
        app.state.chat_provider,
        app.state.model_router,
        app.state.prompt_registry,
        token_budget=settings.ai_context_token_budget,
    )
    app.state.conversation_locks = ConversationLockManager(settings.redis_url)
    app.state.stream_quota = StreamQuota(settings.redis_url)
    app.state.tool_registry = ToolRegistry(
        [
            CurrentTimeTool(),
            CalculatorTool(),
            ProductSearchTool(
                base_url=settings.business_service_url,
                service_token=settings.business_service_token,
                timeout=settings.business_service_timeout_seconds,
            ),
        ]
    )
    app.state.agent_workflow = AgentWorkflow(
        app.state.chat_provider,
        app.state.tool_registry,
        app.state.model_router,
        settings.agent_max_iterations,
    )

    logger.info(
        "ai service starting",
        extra={
            "version": __version__,
            "env": settings.app_env,
            "provider": settings.ai_provider,
            "authRequired": settings.ai_auth_required,
        },
    )

    try:
        yield
    finally:
        await app.state.rate_limiter.aclose()
        await app.state.stream_quota.aclose()
        await app.state.conversation_locks.aclose()
        await app.state.embedding_provider.aclose()
        await app.state.chat_provider.aclose()
        await app.state.database.aclose()
        logger.info("ai service stopped")


def create_app() -> FastAPI:
    """Build the ASGI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Streaming AI companion service for vue-h5-template. "
            "Exchanges a typed message list for a Server-Sent Events stream."
        ),
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    # Reject requests whose Host header is not ours before doing any work.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestContextMiddleware)

    _register_exception_handlers(app)
    app.include_router(api_router)
    return app


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a correlation id and emit one access log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            with span("http.request", method=request.method, path=request.url.path, request_id=request_id):
                response = await call_next(request)
        except Exception:
            # Unhandled errors are logged here so that even a crash before the
            # exception handlers run still leaves a trace with the request id.
            logger.exception(
                "unhandled error",
                extra={"requestId": request_id, "path": request.url.path},
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "http request",
            extra={
                "requestId": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "durationMs": duration_ms,
            },
        )
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    """Map exceptions onto the shared JSON envelope."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        payload = ApiResponse[None](
            code=exc.code,
            message=exc.message,
            data=None,
            error=exc.detail,
            requestId=getattr(request.state, "request_id", None),
        )
        # Log at warning for client faults, error for ours. The detail is sent
        # under a non-reserved key: `message` collides with LogRecord.message.
        if exc.status_code >= 500:
            logger.error("request failed", extra={"code": exc.code, "detail": exc.message})
        else:
            logger.warning("request rejected", extra={"code": exc.code, "detail": exc.message})
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Surface only the field names, never the submitted values, which may
        # contain credentials or personal data.
        fields = sorted({".".join(str(part) for part in error["loc"][1:]) for error in exc.errors()})
        payload = ApiResponse[None](
            code=CODE_VALIDATION,
            message="Invalid request payload",
            data=None,
            error={"fields": fields},
            requestId=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(by_alias=True),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled exception",
            extra={"requestId": getattr(request.state, "request_id", None)},
        )
        payload = ApiResponse[None](
            code=CODE_INTERNAL,
            message="Internal server error",
            data=None,
            error=None,
            requestId=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(by_alias=True),
        )


app = create_app()

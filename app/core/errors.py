"""Application errors and the handlers that turn them into responses.

Error codes match the numeric vocabulary used by the business service so that
frontend clients can share one error-handling branch across both backends.
"""

from __future__ import annotations

from typing import Any

# Stable application codes. 0 means success; 4xxx are caller-fixable and
# 5xxx indicate a server-side fault worth alerting on.
CODE_OK = 0
CODE_BAD_REQUEST = 4000
CODE_VALIDATION = 4001
CODE_UNAUTHORIZED = 4010
CODE_FORBIDDEN = 4030
CODE_NOT_FOUND = 4040
CODE_CONFLICT = 4090
CODE_RATE_LIMITED = 4290
CODE_INTERNAL = 5000
CODE_UNAVAILABLE = 5030


class AppError(Exception):
    """Base class for every error that reaches the client as a known code."""

    status_code: int = 400
    code: int = CODE_BAD_REQUEST
    default_message: str = "Request failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        status_code: int | None = None,
        detail: Any | None = None,
    ) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.detail = detail


class ValidationError(AppError):
    """Request body failed schema or business validation."""

    status_code = 422
    code = CODE_VALIDATION
    default_message = "Invalid request payload"


class AuthenticationError(AppError):
    """No credentials, or credentials that could not be verified."""

    status_code = 401
    code = CODE_UNAUTHORIZED
    default_message = "Authentication required"


class RateLimitError(AppError):
    """Caller exceeded its allowance for the current window."""

    status_code = 429
    code = CODE_RATE_LIMITED
    default_message = "Too many requests"


class ProviderError(AppError):
    """The upstream model provider failed or returned an unusable response."""

    status_code = 502
    code = CODE_UNAVAILABLE
    default_message = "AI provider unavailable"


class ProviderTimeoutError(ProviderError):
    """The upstream model provider did not respond in time."""

    default_message = "AI provider timed out"


class ConfigurationError(AppError):
    """The service is misconfigured for the requested operation."""

    status_code = 500
    code = CODE_INTERNAL
    default_message = "Service is misconfigured"

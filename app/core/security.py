"""Authentication and the request principal.

The service accepts the same access tokens minted by the Go business service,
so a user who logged in there is already authenticated here. Token handling is
deliberately strict: algorithm, issuer, audience and expiry are all enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from app.core.config import Settings, constant_time_compare, get_settings
from app.core.errors import AuthenticationError
from app.providers.base import ChatProvider
from app.services.rate_limit import RateLimiter

# `auto_error=False` lets us distinguish "no credentials" from "bad credentials"
# and decide based on AI_AUTH_REQUIRED instead of always rejecting.
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    """The identity a request runs as."""

    subject: str
    name: str
    role: str
    plan: str
    #: `user`, `service` or `anonymous`; also used as part of the quota key.
    kind: str = "user"


def get_settings_dep() -> Settings:
    """Expose settings as a FastAPI dependency."""
    return get_settings()


def get_chat_provider(request: Request) -> ChatProvider:
    """Return the provider created during startup."""
    return request.app.state.chat_provider  # type: ignore[no-any-return]


def get_rate_limiter(request: Request) -> RateLimiter:
    """Return the rate limiter created during startup."""
    return request.app.state.rate_limiter  # type: ignore[no-any-return]


def authenticate(
    settings: Annotated[Settings, Depends(get_settings_dep)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> Principal:
    """Resolve the caller's identity.

    Precedence: internal service token, then user JWT, then anonymous.
    Anonymous is only allowed when `AI_AUTH_REQUIRED` is false.
    """
    if credentials is None:
        if settings.ai_auth_required:
            raise AuthenticationError()
        return Principal(
            subject="anonymous",
            name="Anonymous",
            role="guest",
            plan="free",
            kind="anonymous",
        )

    token = credentials.credentials

    # The shared secret lets a gateway call us on behalf of its own users
    # without needing to mint per-user tokens.
    if settings.service_token and constant_time_compare(token, settings.service_token):
        return Principal(subject="service", name="Gateway", role="service", plan="internal", kind="service")

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except InvalidTokenError as exc:
        # The reason (expired vs bad signature) is deliberately not exposed.
        raise AuthenticationError("Invalid or expired token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthenticationError("Invalid token subject")

    return Principal(
        subject=subject,
        name=str(payload.get("name") or subject),
        role=str(payload.get("role") or "member"),
        plan=str(payload.get("plan") or "free"),
    )


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
ChatProviderDep = Annotated[ChatProvider, Depends(get_chat_provider)]
RateLimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
CurrentPrincipal = Annotated[Principal, Depends(authenticate)]

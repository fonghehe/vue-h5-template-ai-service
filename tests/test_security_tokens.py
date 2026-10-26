"""Go token purpose must be enforced independently of JWT header type."""

import jwt
import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_JWT_SECRET, auth_header, make_token


@pytest.mark.parametrize("purpose", ["refresh", "unknown", None])
def test_only_access_payload_type_is_accepted(client: TestClient, purpose: str | None) -> None:
    claims = jwt.decode(make_token(), options={"verify_signature": False})
    if purpose is None:
        claims.pop("typ")
    else:
        claims["typ"] = purpose
    token = jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")
    for path in ("/api/conversations", "/api/knowledge/documents", "/api/usage/me"):
        response = client.get(path, headers=auth_header(token))
        assert response.status_code == 401
        assert response.json()["message"] == "Invalid or expired token"
    response = client.post(
        "/api/ai/chat", headers=auth_header(token), json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert response.status_code == 401

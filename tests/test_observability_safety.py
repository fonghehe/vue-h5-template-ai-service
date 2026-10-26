"""Observability must not copy untrusted values into traces or label sets."""

import logging
import sys

import pytest
from app.core.logging import JsonFormatter, TextFormatter
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from pydantic import BaseModel, ValidationError


@pytest.mark.parametrize("formatter", [JsonFormatter(), TextFormatter()])
def test_exception_logs_omit_input_values_and_chained_exception_messages(formatter: logging.Formatter) -> None:
    class ToolInput(BaseModel):
        limit: int

    private_input = "private-document-and-credential-marker"
    try:
        try:
            ToolInput.model_validate({"limit": private_input})
        except ValidationError as exc:
            raise RuntimeError(private_input) from exc
    except RuntimeError:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, "tool execution failed", (), sys.exc_info())
    output = formatter.format(record)
    assert private_input not in output
    assert "RuntimeError" in output
    assert "test_exception_logs" in output  # Retain a diagnostic stack location.


def test_custom_http_methods_share_one_metric_label(client: TestClient) -> None:
    labels = {"method": "OTHER", "route": "/health", "status": "405"}
    before = REGISTRY.get_sample_value("http_requests_total", labels) or 0
    for method in ("CUSTOMONE", "CUSTOMTWO"):
        assert client.request(method, "/health").status_code == 405
        assert REGISTRY.get_sample_value("http_requests_total", {**labels, "method": method}) is None
    assert REGISTRY.get_sample_value("http_requests_total", labels) == before + 2

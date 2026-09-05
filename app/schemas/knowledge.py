"""Knowledge-base response contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    title: str
    source: str
    metadata_json: dict[str, Any] = Field(validation_alias="metadata_json", serialization_alias="metadata")
    created_at: datetime = Field(alias="createdAt")


class ProductRecommendation(BaseModel):
    products: list[dict[str, Any]]
    reason: str

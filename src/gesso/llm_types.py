"""Types for LLM painting-metadata queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PaintingQuerySnapshot:
    """Serializable record of one chat-completions-style request and raw assistant text."""

    provider: str
    model: str
    fields_queried: list[str]
    request_json: dict[str, Any]
    raw_response: str | None


@dataclass
class PaintingMetadataAnswer:
    data: dict
    snapshot: PaintingQuerySnapshot | None = None

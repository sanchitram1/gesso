"""Dispatch painting metadata queries to the configured LLM provider."""

from __future__ import annotations

from .kimi import query_kimi
from .llm_types import PaintingMetadataAnswer
from .model_spec import ResolvedModel
from .pp import query_perplexity


def query_painting_metadata(
    title: str,
    artist: str,
    fields: list[str] | None = None,
    *,
    resolved: ResolvedModel,
) -> PaintingMetadataAnswer:
    if resolved.provider == "perplexity":
        return query_perplexity(title, artist, fields, model=resolved.api_model)
    return query_kimi(title, artist, fields, model=resolved.api_model)

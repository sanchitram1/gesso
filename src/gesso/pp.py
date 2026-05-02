"""
Perplexity client wrapper for structured painting metadata queries.
Uses the official Perplexity SDK (perplexityai).
"""

import json
import os

from perplexity import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    Perplexity,
)

from .llm_types import PaintingMetadataAnswer, PaintingQuerySnapshot
from .painting_prompt import (
    TEMPLATE_TO_API_FIELD_MAP,  # noqa: F401 - re-export for tests
    build_painting_prompt,
    loads_assistant_json,
    map_response_to_result,
)


def get_client():
    """Initialize and return Perplexity client."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set in environment")
    return Perplexity(api_key=api_key)


def query_perplexity(
    title: str,
    artist: str,
    fields: list[str] | None = None,
    *,
    model: str = "sonar-pro",
) -> PaintingMetadataAnswer:
    """
    Query Perplexity for painting metadata using Chat Completions.

    Args:
        title: Painting title (always included)
        artist: Artist name (always included)
        fields: Optional list of template field names to query.
                If None, uses default fields: year, style, medium, museum, image, description
        model: Perplexity model id (e.g. sonar-pro).

    Returns parsed fields under ``data`` plus an optional ``snapshot`` of the request/response.
    """
    client = get_client()
    prompt, template_fields, template_to_api = build_painting_prompt(
        title, artist, fields
    )

    messages = [{"role": "user", "content": prompt}]
    request_json = {"model": model, "messages": messages}

    def _snap(raw: str | None) -> PaintingQuerySnapshot:
        return PaintingQuerySnapshot(
            provider="perplexity",
            model=model,
            fields_queried=list(template_fields),
            request_json=request_json,
            raw_response=raw,
        )

    content: str | None = None
    try:
        response = client.chat.completions.create(model=model, messages=messages)

        if not response.choices:
            return PaintingMetadataAnswer(data={}, snapshot=_snap(None))

        content = response.choices[0].message.content

        painting_data = loads_assistant_json(content)

        return PaintingMetadataAnswer(
            data=map_response_to_result(
                painting_data, title, artist, template_fields, template_to_api
            ),
            snapshot=_snap(content),
        )
    except json.JSONDecodeError as e:
        raw = content if content is not None else ""
        snippet = repr(raw[:400])
        print(
            f"[ERROR] Failed to parse JSON response for '{title}' by {artist}: {e} "
            f"(assistant content prefix {snippet})"
        )
        return PaintingMetadataAnswer(data={}, snapshot=_snap(content))
    except APIStatusError as exc:
        body_snippet = repr(exc.body)[:400] if exc.body is not None else "(no body)"
        print(
            f"[ERROR] Perplexity HTTP {exc.status_code} for '{title}' by {artist}: "
            f"{exc.message} — response body snippet: {body_snippet}"
        )
        raise
    except APIResponseValidationError as exc:
        body_snippet = repr(exc.body)[:400] if exc.body is not None else "(no body)"
        print(
            f"[ERROR] Perplexity HTTP {exc.status_code} (invalid response shape) for "
            f"'{title}' by {artist}: {exc.message} — body snippet: {body_snippet}"
        )
        raise
    except APIConnectionError as exc:
        print(
            f"[ERROR] Perplexity connection error for '{title}' by {artist}: {exc.message}"
        )
        raise
    except APIError as exc:
        print(f"[ERROR] Perplexity API error for '{title}' by {artist}: {exc.message}")
        raise
    except Exception as e:
        print(f"[ERROR] Perplexity query failed for '{title}' by {artist}: {e}")
        return PaintingMetadataAnswer(
            data={},
            snapshot=_snap(content),
        )

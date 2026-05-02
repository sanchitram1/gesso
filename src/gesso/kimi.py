"""Kimi (Moonshot) OpenAI-compatible client for painting metadata queries."""

from __future__ import annotations

import json
import os

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError

from .llm_types import PaintingMetadataAnswer, PaintingQuerySnapshot
from .painting_prompt import (
    build_painting_prompt,
    loads_assistant_json,
    map_response_to_result,
)

KIMI_BASE_URL = "https://api.moonshot.ai/v1"


def _api_key() -> str:
    key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY")
    if not key:
        raise ValueError(
            "Kimi API key not set: use MOONSHOT_API_KEY or KIMI_API_KEY in the environment"
        )
    return key


def query_kimi(
    title: str,
    artist: str,
    fields: list[str] | None = None,
    *,
    model: str = "kimi-k2.6",
) -> PaintingMetadataAnswer:
    """Query Kimi chat completions; returns the same shape as Perplexity."""
    client = OpenAI(api_key=_api_key(), base_url=KIMI_BASE_URL)
    prompt, template_fields, template_to_api = build_painting_prompt(
        title, artist, fields
    )

    messages = [{"role": "user", "content": prompt}]
    request_json = {"model": model, "messages": messages}

    def _snap(raw: str | None) -> PaintingQuerySnapshot:
        return PaintingQuerySnapshot(
            provider="kimi",
            model=model,
            fields_queried=list(template_fields),
            request_json=request_json,
            raw_response=raw,
        )

    content: str | None = None
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
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
    except RateLimitError as exc:
        print(
            f"[ERROR] Kimi rate limit for '{title}' by {artist}: {getattr(exc, 'message', exc)}"
        )
        raise
    except APIConnectionError as exc:
        print(
            f"[ERROR] Kimi connection error for '{title}' by {artist}: "
            f"{getattr(exc, 'message', exc)}"
        )
        raise
    except APITimeoutError as exc:
        print(
            f"[ERROR] Kimi timeout for '{title}' by {artist}: {getattr(exc, 'message', exc)}"
        )
        raise
    except APIError as exc:
        print(
            f"[ERROR] Kimi API error for '{title}' by {artist}: "
            f"{getattr(exc, 'message', exc)}"
        )
        raise
    except Exception as e:
        print(f"[ERROR] Kimi query failed for '{title}' by {artist}: {e}")
        return PaintingMetadataAnswer(
            data={},
            snapshot=_snap(content),
        )

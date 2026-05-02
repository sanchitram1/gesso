"""Shared painting-metadata prompt and JSON extraction for LLM backends."""

from __future__ import annotations

import json
import re

# Mapping from template field names to keys we ask the model to emit in JSON
TEMPLATE_TO_API_FIELD_MAP: dict[str, str] = {
    "image": "image_url",
}

_FIELD_DESCRIPTIONS: dict[str, str] = {
    "year": "(integer or empty string)",
    "style": '(single string, e.g., "Realism" or comma-separated if multiple)',
    "medium": '(single string, e.g., "Oil on Canvas")',
    "museum": '(single string, e.g., "Art Institute of Chicago")',
    "image_url": "(Wikimedia Commons URL preferred, or empty string)",
    "description": "(brief, 1-2 sentences, or empty string)",
}


def loads_assistant_json(content: str | None) -> dict:
    """
    Parse JSON from chat completion content. Models often wrap JSON in Markdown
    fences or add a short preamble; try several shapes before failing.
    """
    if content is None or not isinstance(content, str):
        raise json.JSONDecodeError("Assistant message missing or empty", "", 0)

    raw = content.strip()
    if not raw:
        raise json.JSONDecodeError("Empty assistant message", "", 0)

    attempts: list[str] = [raw]

    fence = re.search(
        r"```(?:json)?\s*\n(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE
    )
    if fence:
        attempts.append(fence.group(1).strip())

    lo, hi = raw.find("{"), raw.rfind("}")
    if lo != -1 and hi != -1 and hi > lo:
        attempts.append(raw[lo : hi + 1].strip())

    seen: set[str] = set()
    last_exc: json.JSONDecodeError | None = None
    for cand in attempts:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            data = json.loads(cand)
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue
        if not isinstance(data, dict):
            last_exc = json.JSONDecodeError("Expected a JSON object", cand, 0)
            continue
        return data

    if last_exc is None:
        raise json.JSONDecodeError("No parsable JSON object", raw, 0)
    raise last_exc


def build_painting_prompt(
    title: str,
    artist: str,
    fields: list[str] | None,
) -> tuple[str, list[str], dict[str, str]]:
    """
    Build the user prompt and template_field → API JSON key mapping.

    Returns (prompt_text, template_fields, template_to_api).
    """
    if fields is None:
        template_fields = ["year", "style", "medium", "museum", "image", "description"]
    else:
        template_fields = fields

    template_to_api: dict[str, str] = {}
    for template_field in template_fields:
        api_field = TEMPLATE_TO_API_FIELD_MAP.get(template_field, template_field)
        template_to_api[template_field] = api_field

    prompt_lines = [
        "Return a JSON object with the following fields for this painting:",
        f'- title: "{title}"',
        f'- artist: "{artist}"',
    ]

    for template_field in template_fields:
        api_field = template_to_api[template_field]
        description = _FIELD_DESCRIPTIONS.get(
            api_field, "(string value, or empty string if unknown)"
        )
        prompt_lines.append(f"- {api_field}: {description}")

    prompt_lines.append("\nReturn ONLY valid JSON, no other text.")
    prompt = "\n".join(prompt_lines)
    return prompt, template_fields, template_to_api


def map_response_to_result(
    painting_data: dict,
    title: str,
    artist: str,
    template_fields: list[str],
    template_to_api: dict[str, str],
) -> dict:
    result: dict = {"title": title, "artist": artist}
    for template_field in template_fields:
        api_field = template_to_api[template_field]
        if api_field in painting_data:
            result[template_field] = painting_data[api_field]
        else:
            result[template_field] = ""
    return result

"""
Perplexity client wrapper for structured painting metadata queries.
Uses the official Perplexity SDK (perplexityai).
"""

import json
import os

from perplexity import Perplexity

# Mapping from template field names to API field names
# Template field names that differ from what Perplexity API expects
TEMPLATE_TO_API_FIELD_MAP: dict[str, str] = {
    "image": "image_url",  # Template uses "image", API expects "image_url"
}


def get_client():
    """Initialize and return Perplexity client."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set in environment")
    return Perplexity(api_key=api_key)


def query_painting_metadata(
    title: str, artist: str, fields: list[str] | None = None
) -> dict:
    """
    Query Perplexity for painting metadata using Chat Completions.

    Args:
        title: Painting title (always included)
        artist: Artist name (always included)
        fields: Optional list of template field names to query.
                If None, uses default fields: year, style, medium, museum, image, description

    Returns JSON with template field names as keys (strings, not arrays).
    """
    client = get_client()

    # Default template fields if none specified
    if fields is None:
        template_fields = ["year", "style", "medium", "museum", "image", "description"]
    else:
        template_fields = fields

    # Map template field names to API field names
    # Create mapping: template_field -> api_field
    template_to_api = {}
    for template_field in template_fields:
        api_field = TEMPLATE_TO_API_FIELD_MAP.get(template_field, template_field)
        template_to_api[template_field] = api_field

    # Build prompt dynamically based on requested fields
    prompt_lines = ["Return a JSON object with the following fields for this painting:"]
    prompt_lines.append(f'- title: "{title}"')
    prompt_lines.append(f'- artist: "{artist}"')

    # Add field descriptions for additional fields (excluding title and artist)
    field_descriptions = {
        "year": "(integer or empty string)",
        "style": '(single string, e.g., "Realism" or comma-separated if multiple)',
        "medium": '(single string, e.g., "Oil on Canvas")',
        "museum": '(single string, e.g., "Art Institute of Chicago")',
        "image_url": "(Wikimedia Commons URL preferred, or empty string)",
        "description": "(brief, 1-2 sentences, or empty string)",
    }

    # Add requested fields with their descriptions (use API field names in prompt)
    for template_field in template_fields:
        api_field = template_to_api[template_field]
        description = field_descriptions.get(
            api_field, "(string value, or empty string if unknown)"
        )
        prompt_lines.append(f"- {api_field}: {description}")

    prompt_lines.append("\nReturn ONLY valid JSON, no other text.")
    prompt = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model="sonar-pro", messages=[{"role": "user", "content": prompt}]
        )

        # Extract content from response
        content = response.choices[0].message.content

        # Parse JSON from response (will have API field names)
        painting_data = json.loads(content)

        # Always include title and artist
        result = {"title": title, "artist": artist}

        # Map API field names back to template field names for consistency
        for template_field in template_fields:
            api_field = template_to_api[template_field]
            if api_field in painting_data:
                result[template_field] = painting_data[api_field]
            else:
                result[template_field] = ""

        return result
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON response for '{title}' by {artist}: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] Perplexity query failed for '{title}' by {artist}: {e}")
        return {}

"""
Perplexity client wrapper for structured painting metadata queries.
Uses the official Perplexity SDK (perplexityai).
"""

import json
import os

from perplexity import Perplexity


def get_client():
    """Initialize and return Perplexity client."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not set in environment")
    return Perplexity(api_key=api_key)


def query_painting_metadata(title: str, artist: str) -> dict:
    """
    Query Perplexity for painting metadata using Chat Completions.

    Returns JSON with fields as strings (not arrays):
    - title, artist, year, style, medium, museum, image_url, description
    """
    client = get_client()

    prompt = f"""Return a JSON object with the following fields for this painting:
- title: "{title}"
- artist: "{artist}"
- year: (integer or empty string)
- style: (single string, e.g., "Realism" or comma-separated if multiple)
- medium: (single string, e.g., "Oil on Canvas")
- museum: (single string, e.g., "Art Institute of Chicago")
- image_url: (Wikimedia Commons URL preferred, or empty string)
- description: (brief, 1-2 sentences, or empty string)

Return ONLY valid JSON, no other text."""

    try:
        response = client.chat.completions.create(
            model="sonar-pro", messages=[{"role": "user", "content": prompt}]
        )

        # Extract content from response
        content = response.choices[0].message.content

        # Parse JSON from response
        painting_data = json.loads(content)
        return painting_data
    except json.JSONDecodeError as e:
        print(f"[ERROR] Failed to parse JSON response for '{title}' by {artist}: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] Perplexity query failed for '{title}' by {artist}: {e}")
        return {}

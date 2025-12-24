#!/usr/bin/env pkgx uv run
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .pp import query_painting_metadata

# Load environment variables early so local .env is respected for the CLI.
load_dotenv()


def parse_input(filepath: str) -> list[dict]:
    """
    Parse input.txt and extract painting entries.
    Format: number: Title, Artist (Location is optional and ignored)
    """
    paintings = []
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Parse `number: Title, Artist`
                match = re.match(r"(\d+):\s*(.+)", line)
                if not match:
                    print(f"[WARN] Invalid input line: {line}")
                    continue

                number = int(match.group(1))
                rest = match.group(2)
                # Split only on the first two commas to get title and artist
                parts = [p.strip() for p in rest.split(",", 2)]

                if len(parts) < 2:
                    print(f"[WARN] Invalid format (need Title, Artist): {line}")
                    continue

                title = parts[0]
                artist = parts[1]
                # Ignore location (parts[2] if it exists)

                paintings.append(
                    {
                        "number": number,
                        "title": title,
                        "artist": artist,
                    }
                )
    except FileNotFoundError:
        print(f"[ERROR] Input file not found: {filepath}")

    return paintings


def get_cache_key(title: str, artist: str) -> str:
    """Generate cache key from title and artist."""
    key = f"{title}_{artist}"
    # Normalize: lowercase, replace spaces with underscores, remove special chars
    key = key.lower().replace(" ", "_")
    key = re.sub(r"[^a-z0-9_]", "", key)
    return f"{key}.json"


def load_from_cache(cache_dir: str, cache_key: str) -> dict | None:
    """Load painting data from cache if it exists."""
    cache_path = Path(cache_dir) / cache_key
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception as e:  # pragma: no cover - defensive logging
            print(f"[WARN] Failed to load cache {cache_key}: {e}")
    return None


def save_to_cache(cache_dir: str, cache_key: str, data: dict) -> None:
    """Save painting data to cache."""
    Path(cache_dir).mkdir(exist_ok=True)
    cache_path = Path(cache_dir) / cache_key
    try:
        with open(cache_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:  # pragma: no cover - defensive logging
        print(f"[WARN] Failed to save cache {cache_key}: {e}")


def post_process_fields(data: dict) -> dict:
    """
    Post-process painting data:
    - Convert string fields to lists
    - Wrap artist and museum names in [[...]] for Obsidian links
    - Handle empty/missing fields
    """
    processed = {}

    # Title (keep as-is)
    processed["title"] = data.get("title", "")

    # Artist (wrap in Obsidian link)
    artist = data.get("artist", "")
    processed["artist"] = f"[[{artist}]]" if artist else ""

    # Year (keep as-is, can be int or empty)
    year = data.get("year", "")
    processed["year"] = year if year and str(year).lower() != "unknown" else ""

    # Style (convert string to list, wrap in links)
    style_str = data.get("style", "")
    if style_str and str(style_str).lower() != "unknown":
        styles = [s.strip() for s in str(style_str).split(",")]
        processed["style"] = [f"[[{s}]]" for s in styles if s]
    else:
        processed["style"] = []

    # Medium (convert string to list, wrap in links)
    medium_str = data.get("medium", "")
    if medium_str and str(medium_str).lower() != "unknown":
        mediums = [m.strip() for m in str(medium_str).split(",")]
        processed["medium"] = [f"[[{m}]]" for m in mediums if m]
    else:
        processed["medium"] = []

    # Museum (convert string to list, wrap in links)
    museum_str = data.get("museum", "")
    if museum_str and str(museum_str).lower() != "unknown":
        museums = [m.strip() for m in str(museum_str).split(",")]
        processed["museum"] = [f"[[{m}]]" for m in museums if m]
    else:
        processed["museum"] = []

    # Image (use image_url from API response)
    image_url = data.get("image_url", "")
    processed["image"] = (
        image_url if image_url and str(image_url).lower() != "unknown" else ""
    )

    # Description
    processed["description"] = data.get("description", "")

    # Fixed fields
    processed["tags"] = ["paintings"]

    return processed


def render_markdown(template_path: str, painting_data: dict, today: str) -> str:
    """
    Render markdown from template with painting data.
    Replaces {{key}} placeholders and formats lists as YAML arrays.
    """
    try:
        with open(template_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[ERROR] Template not found: {template_path}")
        return ""

    # Helper to format YAML list with quoted wikilinks
    def format_yaml_list(items):
        if not items:
            return ""
        # Quote items if they contain wikilinks
        quoted_items = []
        for item in items:
            if "[[" in item and "]]" in item:
                quoted_items.append(f'  - "{item}"')
            else:
                quoted_items.append(f"  - {item}")
        return "\n".join(quoted_items)

    # Replace basic placeholders
    replacements = {
        "{{date}}": today,
        "{{title}}": painting_data.get("title", ""),
        "{{image}}": painting_data.get("image", ""),
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    # Handle artist field in YAML frontmatter
    artist = painting_data.get("artist", "")
    quoted_artist = f'"{artist}"' if artist else ""
    content = re.sub(
        r"(artist:)\s*$", r"\1 " + quoted_artist, content, flags=re.MULTILINE
    )

    # Handle year field in YAML frontmatter
    year = painting_data.get("year", "")
    year_str = str(year) if year else ""
    content = re.sub(r"(year:)\s*$", r"\1 " + year_str, content, flags=re.MULTILINE)

    # Handle list fields (style, medium, museum)
    # Note: tags are left as-is in template since they're hardcoded as ["paintings"]
    style_list = format_yaml_list(painting_data.get("style", []))
    medium_list = format_yaml_list(painting_data.get("medium", []))
    museum_list = format_yaml_list(painting_data.get("museum", []))

    # Replace list fields in YAML
    content = re.sub(
        r"(style:)\s*$",
        r"\1" + ("\n" + style_list if style_list else ""),
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r"(medium:)\s*$",
        r"\1" + ("\n" + medium_list if medium_list else ""),
        content,
        flags=re.MULTILINE,
    )

    content = re.sub(
        r"(museum:)\s*$",
        r"\1" + ("\n" + museum_list if museum_list else ""),
        content,
        flags=re.MULTILINE,
    )

    # Handle image field in YAML
    image = painting_data.get("image", "")
    content = re.sub(r"(image:)\s*$", r"\1 " + image, content, flags=re.MULTILINE)

    return content


def write_output(output_dir: str, filename: str, content: str) -> None:
    """Write markdown content to output file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / filename
    try:
        with open(output_path, "w") as f:
            f.write(content)
    except Exception as e:  # pragma: no cover - defensive logging
        print(f"[ERROR] Failed to write {filename}: {e}")


def require_api_key() -> str:
    """Ensure PERPLEXITY_API_KEY is available before running."""
    api_key: Optional[str] = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise SystemExit(
            "[ERROR] PERPLEXITY_API_KEY is not set. Export it or add it to your .env file."
        )
    return api_key


def main(
    input_file: str = "data/example-input.txt",
    output_dir: str = "outputs/",
    cache_dir: str = ".cache",
):
    """
    Main orchestration function.
    Parse input, query Perplexity (or load from cache), render, and write output.
    """
    require_api_key()

    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")

    # Template lives at the project root under data/, even when installed.
    project_root = Path(__file__).resolve().parents[2]
    template_path = project_root / "data" / "example-template.md"
    if not template_path.exists():
        raise SystemExit(f"[ERROR] Template not found at {template_path}")

    # Parse input
    paintings = parse_input(input_file)
    if not paintings:
        print("[WARN] No paintings found in input file")
        return

    print(f"\\nProcessing {len(paintings)} paintings...")

    cache_hits = 0
    api_queries = 0

    for painting in paintings:
        title = painting["title"]
        artist = painting["artist"]

        # Get cache key
        cache_key = get_cache_key(title, artist)

        # Try to load from cache
        painting_data = load_from_cache(cache_dir, cache_key)
        if painting_data:
            print(f"[CACHE] {title} by {artist}")
            cache_hits += 1
        else:
            # Query Perplexity using pp.py
            print(f"[QUERY] {title} by {artist}")
            painting_data = query_painting_metadata(title, artist)
            api_queries += 1

            # Save to cache
            if painting_data:
                save_to_cache(cache_dir, cache_key, painting_data)

        if not painting_data:
            print(f"[SKIP] Skipping due to query failure: {title}")
            continue

        # Post-process fields
        painting_data = post_process_fields(painting_data)

        # Render markdown
        markdown = render_markdown(str(template_path), painting_data, today)

        # Write output
        output_filename = f"{title}.md"
        write_output(output_dir, output_filename, markdown)
        print(f"[WRITE] {output_filename}")

    print(f"\\n✓ Processed {len(paintings)} paintings")
    print(f"  - {cache_hits} from cache")
    print(f"  - {api_queries} new API queries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Obsidian painting notes from input list"
    )
    parser.add_argument(
        "--input",
        default="data/input.txt",
        help="Input file path (default: data/input.txt)",
    )
    parser.add_argument(
        "--output", default="outputs/", help="Output directory (default: outputs/)"
    )
    parser.add_argument(
        "--cache", default=".cache", help="Cache directory (default: .cache)"
    )

    args = parser.parse_args()
    main(input_file=args.input, output_dir=args.output, cache_dir=args.cache)

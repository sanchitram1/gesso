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


def post_process_fields(data: dict, template_fields: list[str]) -> dict:
    """
    Post-process painting data dynamically based on template fields.
    - Convert string fields to lists for list-type fields
    - Wrap certain fields in [[...]] for Obsidian links
    - Handle empty/missing fields

    Args:
        data: Raw data from Perplexity API (with template field names)
        template_fields: List of field names from template that need processing
    """
    processed = {}

    # Title (keep as-is)
    processed["title"] = data.get("title", "")

    # Fields that should be converted to lists with wikilinks
    list_fields = {"style", "medium", "museum"}

    # Fields that should be wrapped in wikilinks (but not lists)
    wikilink_fields = {"artist"}

    # Process each template field
    for field in template_fields:
        value = data.get(field, "")

        if field in list_fields:
            # Convert comma-separated string to list with wikilinks
            if value and str(value).lower() != "unknown":
                items = [item.strip() for item in str(value).split(",") if item.strip()]
                processed[field] = [f"[[{item}]]" for item in items]
            else:
                processed[field] = []
        elif field in wikilink_fields:
            # Wrap single value in wikilinks
            processed[field] = f"[[{value}]]" if value else ""
        elif field == "image":
            # Handle image field (template uses "image", API returns it as "image")
            image_value = data.get("image", "")
            if image_value and str(image_value).lower() != "unknown":
                processed["image"] = image_value
            else:
                processed["image"] = ""
        elif field == "year":
            # Year: keep as-is, can be int or empty
            year = data.get("year", "")
            processed["year"] = year if year and str(year).lower() != "unknown" else ""
        elif field == "description":
            # Description: keep as-is (including "Unknown" if present)
            processed["description"] = data.get("description", "")
        else:
            # Other fields: keep as-is, but filter "Unknown"
            if value and str(value).lower() != "unknown":
                processed[field] = value
            else:
                processed[field] = ""

    # Handle artist separately (always process if present)
    if "artist" not in processed:
        artist = data.get("artist", "")
        processed["artist"] = f"[[{artist}]]" if artist else ""

    # Fixed fields
    processed["tags"] = ["paintings"]

    return processed


def render_markdown(
    template_path: str, painting_data: dict, today: str, template_fields: list[str]
) -> str:
    """
    Render markdown from template with painting data.
    Replaces {{key}} placeholders and formats lists as YAML arrays.

    Args:
        template_path: Path to template file
        painting_data: Processed painting data
        today: Today's date string
        template_fields: List of field names from template (to determine which are lists)
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

    # Fields that should be rendered as YAML lists
    list_fields = {"style", "medium", "museum"}

    # Handle artist field separately (always render if present, even though it's blacklisted)
    artist = painting_data.get("artist", "")
    if artist:
        quoted_artist = f'"{artist}"' if artist else ""
        content = re.sub(
            r"(artist:)\s*$", r"\1 " + quoted_artist, content, flags=re.MULTILINE
        )

    # Process each template field dynamically
    for field in template_fields:
        value = painting_data.get(field, "")

        if field in list_fields:
            # Render as YAML list
            list_str = format_yaml_list(value if isinstance(value, list) else [])
            content = re.sub(
                rf"({re.escape(field)}:)\s*$",
                r"\1" + ("\n" + list_str if list_str else ""),
                content,
                flags=re.MULTILINE,
            )
        elif field == "year":
            # Year field: convert to string
            year_str = str(value) if value else ""
            content = re.sub(
                rf"({re.escape(field)}:)\s*$",
                r"\1 " + year_str,
                content,
                flags=re.MULTILINE,
            )
        elif field == "image":
            # Image field: keep as-is
            image = value if isinstance(value, str) else ""
            content = re.sub(
                rf"({re.escape(field)}:)\s*$",
                r"\1 " + image,
                content,
                flags=re.MULTILINE,
            )
        else:
            # Other scalar fields: render as string value
            field_value = str(value) if value else ""
            # Quote if contains special characters or wikilinks
            if "[[" in field_value or "]]" in field_value:
                field_value = f'"{field_value}"'
            content = re.sub(
                rf"({re.escape(field)}:)\s*$",
                r"\1 " + field_value,
                content,
                flags=re.MULTILINE,
            )

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


def extract_template_fields(template_path: str) -> list[str]:
    """
    Extract YAML frontmatter field names from template file.

    All frontmatter fields except blacklisted ones will be queried from Perplexity.
    Blacklisted fields (user-defined, not from Perplexity): title, date, created,
    category, rating, seen, tags, artist.

    Returns list of field names that should be queried from Perplexity.
    """
    try:
        with open(template_path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        raise SystemExit(f"[ERROR] Template not found: {template_path}")

    # Extract YAML frontmatter (between --- delimiters)
    frontmatter_match = re.search(
        r"^---\s*\n(.*?)\n---", content, re.DOTALL | re.MULTILINE
    )
    if not frontmatter_match:
        raise SystemExit(
            f"[ERROR] Template {template_path} has no YAML frontmatter (missing --- delimiters)"
        )

    frontmatter = frontmatter_match.group(1)

    # Extract field names using regex pattern for "fieldname: value"
    field_pattern = r"^(\w+):\s*"
    fields = []
    for line in frontmatter.split("\n"):
        match = re.match(field_pattern, line)
        if match:
            field_name = match.group(1)
            fields.append(field_name)

    # Blacklist of fields that should NOT be queried from Perplexity
    blacklist = {
        "title",
        "date",
        "created",
        "category",
        "rating",
        "seen",
        "tags",
        "artist",
    }

    # Filter out blacklisted fields
    filtered_fields = [f for f in fields if f not in blacklist]

    if not filtered_fields:
        raise SystemExit(
            f"[ERROR] Template {template_path} has no fields to collect from Perplexity "
            "(all fields are blacklisted or empty)"
        )

    return filtered_fields


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
    template_file: str = "data/example-template.md",
):
    """
    Main orchestration function.
    Parse input, query Perplexity (or load from cache), render, and write output.
    """
    require_api_key()

    # Get today's date
    today = datetime.now().strftime("%Y-%m-%d")

    # Resolve template path (handle both relative and absolute paths)
    template_path = Path(template_file)
    if not template_path.is_absolute():
        # If relative, resolve relative to project root
        project_root = Path(__file__).resolve().parents[2]
        template_path = project_root / template_file
    else:
        template_path = Path(template_file)

    if not template_path.exists():
        raise SystemExit(f"[ERROR] Template not found at {template_path}")

    # Extract fields from template
    template_fields = extract_template_fields(str(template_path))
    print(f"[INFO] Collecting fields from Perplexity: {', '.join(template_fields)}")

    # Parse input
    paintings = parse_input(input_file)
    if not paintings:
        print("[WARN] No paintings found in input file")
        return

    print(f"\nProcessing {len(paintings)} paintings...")

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
            # Query Perplexity using pp.py with template fields
            print(f"[QUERY] {title} by {artist}")
            painting_data = query_painting_metadata(
                title, artist, fields=template_fields
            )
            api_queries += 1

            # Save to cache
            if painting_data:
                save_to_cache(cache_dir, cache_key, painting_data)

        if not painting_data:
            print(f"[SKIP] Skipping due to query failure: {title}")
            continue

        # Post-process fields
        painting_data = post_process_fields(painting_data, template_fields)

        # Render markdown
        markdown = render_markdown(
            str(template_path), painting_data, today, template_fields
        )

        # Write output
        output_filename = f"{title}.md"
        write_output(output_dir, output_filename, markdown)
        print(f"[WRITE] {output_filename}")

    print(f"\n✓ Processed {len(paintings)} paintings")
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
    parser.add_argument(
        "--template",
        default="data/example-template.md",
        help="Template file path (default: data/example-template.md)",
    )

    args = parser.parse_args()
    main(
        input_file=args.input,
        output_dir=args.output,
        cache_dir=args.cache,
        template_file=args.template,
    )

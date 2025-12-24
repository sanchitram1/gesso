# gesso

[![CI](https://github.com/sanchitram1/gesso/actions/workflows/ci.yml/badge.svg)
](https://github.com/sanchitram1/gesso/actions/workflows/ci.yml)
[![Coverage](https://coveralls.io/repos/github/sanchitram1/gesso/badge.svg?branch=main)
](https://coveralls.io/github/sanchitram1/gesso?branch=main)

Generate Obsidian-ready painting notes from a simple input list. The CLI reads
`PERPLEXITY_API_KEY` from your environment (or `.env`), enriches each row via
Perplexity, and writes markdown files from the bundled template.

## Pre-requisites

- [`uv`](https://astral.sh/uv) for dependency management

## Quickstart
- Install deps: `uv sync`
- Export `PERPLEXITY_API_KEY` (or add to `.env`)
- Run: `gesso --input data/input.txt --output outputs/`
  - Defaults: `--input data/input.txt --output outputs/ --cache .cache
    --template data/example-template.md`

## Input & Template
- Input lines: `number: Title, Artist`
- Template: Use `--template` to specify a custom template file (default:
`data/example-template.md`). Output files land in `outputs/{title}.md`.

### Template Field Extraction
The tool automatically extracts YAML frontmatter field names from your template
and queries Perplexity for those fields. This allows you to customize which
metadata fields you want to collect.

**Blacklisted fields** (user-defined, not from Perplexity): `title`, `date`,
`created`, `category`, `rating`, `seen`, `tags`, `artist`. These fields are
always excluded from Perplexity queries. Will probably need to modify this to make it configurable as well...oh well, feel free to drop a PR.

**Example template:**
```yaml
---
created: {{date}}
title: "{{title}}"
artist: 
year:           # ← Collected from Perplexity
style:          # ← Collected from Perplexity
medium:         # ← Collected from Perplexity
museum:         # ← Collected from Perplexity
image:          # ← Collected from Perplexity
rating:         # ← NOT collected (blacklisted)
tags:           # ← NOT collected (blacklisted)
  - paintings
---
```

The tool prints which fields it's collecting at startup:
```
[INFO] Collecting fields from Perplexity: year, style, medium, museum, image
```

**Field name mapping:** Template field names are mapped to API field names where
needed (e.g., `image` → `image_url`). Most fields use the same name in both
template and API.

- Cache: `.cache/{title_artist}.json` to avoid duplicate API calls.

> [!warning]
> If you change the template structure, you need to clear out the cache to ensure the
> code requeries everything. Otherwise, it'll just write an empty field

## Flow (per painting)
1. Extract fields from template YAML frontmatter (excluding blacklisted fields).
2. Parse input line into `{number, title, artist}`.
3. Check cache; otherwise query Perplexity for metadata (only the fields found
   in
template).
4. Post-process strings into Obsidian-friendly lists/links.
5. Render template placeholders and frontmatter with collected data.
6. Write markdown to the output directory.

## Module reference
- `parse_input(filepath)`: read lines into structured dicts; warns on invalid
rows.
- `extract_template_fields(template_path)`: extract YAML frontmatter field
  names,
filtering out blacklisted fields.
- `get_cache_key(title, artist)`: normalize to cache filename.
- `load_from_cache / save_to_cache`: JSON cache helpers under `.cache/`.
- `query_painting_metadata(title, artist, fields)`: Perplexity SDK wrapper using
`PERPLEXITY_API_KEY`; accepts optional list of fields to query dynamically.
- `post_process_fields(data, template_fields)`: convert comma-separated strings
to lists and wrap wikilinks; drop `"Unknown"` values (except for description).
- `render_markdown(template_path, painting_data, today, template_fields)`: fill
template placeholders and YAML lists dynamically based on template fields.
- `write_output(output_dir, filename, content)`: ensure dirs exist and persist
markdown.
- `main(...)`: CLI orchestrator; accepts `--input`, `--output`, `--cache`,
`--template` arguments.

## Usage Examples

```bash
# Use default template
gesso --input data/input.txt

# Use custom template
gesso --input data/input.txt --template my-template.md

# Specify all options
gesso --input paintings.txt --output notes/ --cache .cache/ --template templates/custom.md
```

## Error handling
- Missing env key: fails fast with a clear message.
- Template errors: fails if template file not found or has no fields to collect.
- Input parse errors: warn and skip lines.
- Perplexity failures: log error and skip that painting.
- Cache/IO issues: log warnings and continue to the next item.

## Development
- Python 3.13+, managed with `uv`.
- Style: `uv run ruff format --check .` and `uv run ruff check .`
- Tests: `uv run pytest -v --cov --cov-report=xml`
- CI mirrors these steps (`.github/workflows/ci.yml`).

## Contributing
- Keep README aligned with behavior; update TODOs when adding features.
- Add tests for new parsing, templating, or API edge cases.
- Run lint/format/tests before sending changes.

## Tasks

### lint

```bash
uv run ruff check . --fix --unsafe-fixes
uv run ruff format .
```

### test

```bash
pytest
```

### sync

```bash
uv sync
```
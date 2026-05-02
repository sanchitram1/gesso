# gesso

[![CI](https://github.com/sanchitram1/gesso/actions/workflows/ci.yml/badge.svg)
](https://github.com/sanchitram1/gesso/actions/workflows/ci.yml)
[![Coverage](https://coveralls.io/repos/github/sanchitram1/gesso/badge.svg?branch=main)
](https://coveralls.io/github/sanchitram1/gesso?branch=main)

Generate Obsidian-ready painting notes:

- **`gesso new`** — build notes from an input list (original workflow).
- **`gesso enrich`** — read an existing note, propose factual frontmatter updates
  from cached or live LLM metadata, and write a **proposal** Markdown file
  (vault note is untouched unless `--apply`).

Use **`--model`** to pick the backend (default **Perplexity**). Set the matching API
key in your environment or `.env`:

| Backend | Keys | Example `--model` |
|---------|------|-------------------|
| Perplexity | `PERPLEXITY_API_KEY` | `perplexity` (default), `perplexity:sonar-pro`, or `sonar-pro` |
| Kimi (Moonshot) | `MOONSHOT_API_KEY` or `KIMI_API_KEY` | `kimi`, `kimi:kimi-k2.6`, or `kimi-k2.6` |

For compatibility, `gesso --input …` (flags without a subcommand) is interpreted as
`gesso new --input …`.

## Pre-requisites

- [`uv`](https://astral.sh/uv) for dependency management

## Quickstart
- Install deps: `uv sync`
- Export `PERPLEXITY_API_KEY` (or add to `.env`). For Kimi, set `MOONSHOT_API_KEY` or `KIMI_API_KEY`.
- Generate notes:

```bash
gesso new --input data/input.txt --output outputs/
# Kimi: gesso new --model kimi --input data/input.txt --output outputs/
```

Defaults for `new`: `--input data/input.txt --output outputs/ --cache .cache`
`--template data/example-template.md`

Legacy shorthand (prepend `new` automatically):

```bash
gesso --input data/input.txt --output outputs/
```

## Enrich (`gesso enrich`)

Enrichment parses YAML frontmatter from an existing note, derives plaintext
**title** and **artist** from it, derives factual fields via
`extract_template_fields`, fills only **missing** values from `.cache/` first then
minimal LLM calls (`query_painting_metadata`).

**Personal / vault keys are never queried or overwritten** from the API in this pass:
`rating`, `seen`, `created`, `tags`, `category`, plus template blacklist entries
such as **`title`** and **`artist`** (your note wording wins).

Example:

```bash
gesso enrich \
  --note /path/to/Retrieve.md \
  --template '/path/to/Painting Template.md' \
  --attachments /path/to/Attachments \
  --cache .cache \
  --proposal-only
```

- Proposals land under **`--proposal-dir`** (default
  **`manifests/painting-enrichment`**) as `{note-stem}.enrich-proposal.md`.
- **`--proposal-only`** reaffirms vault-safe mode (proposals **always** written).
  **`--apply`** also rewrites the note frontmatter and keeps body text — explicit
  opt-in.
- **`--attachments`** appears in proposals for tooling; **`--download-image`** is
  reserved for a future enhancement (currently errors).

`PERPLEXITY_API_KEY` (or Kimi keys when using `--model kimi`) is required **only when** gaps remain after `.cache/` cannot satisfy them.

## Input & Template
- Input lines: `number: Title, Artist`
- Template: Use `--template` to specify a custom template file (default:
`data/example-template.md`). Output files land in `outputs/{title}.md`.

### Template Field Extraction
The tool automatically extracts YAML frontmatter field names from your template
and queries the configured model for those fields.
metadata fields you want to collect.

**Blacklisted fields** (user-defined, not from the API): `title`, `date`,
`created`, `category`, `rating`, `seen`, `tags`, `artist`. These fields are
always excluded from API queries.

**Example template:**
```yaml
---
created: {{date}}
title: "{{title}}"
artist: 
year:           # ← Collected from the LLM
style:          # ← Collected from the LLM
medium:         # ← Collected from the LLM
museum:         # ← Collected from the LLM
image:          # ← Collected from the LLM
rating:         # ← NOT collected (blacklisted)
tags:           # ← NOT collected (blacklisted)
  - paintings
---
```

The tool prints which fields it's collecting at startup:
```
[INFO] Collecting fields via perplexity (sonar-pro): year, style, medium, museum, image
```

**Field name mapping:** Template field names are mapped to API field names where
needed (e.g., `image` → `image_url`). Most fields use the same name in both
template and API.

- Cache: `.cache/{normalized_title_artist}.json` for Perplexity (legacy), or
  `.cache/{normalized}.kimi.json` when using `--model kimi`, to keep providers separate.

> [!warning]
> If you change the template structure, you need to clear out the cache to ensure the
> code requeries everything. Otherwise, it'll just write an empty field

## Flow (per painting — `new`)
1. Extract fields from template YAML frontmatter (excluding blacklisted fields).
2. Parse input line into `{number, title, artist}`.
3. Check cache; otherwise query the configured LLM for metadata (only the fields found
   in
template).
4. Post-process strings into Obsidian-friendly lists/links.
5. Render template placeholders and frontmatter with collected data.
6. Write markdown to the output directory.

## Flow (`enrich`)
1. Parse note frontmatter and body separately.
2. Infer plaintext title/artist from frontmatter values.
3. Determine missing factual fields from template extract + note values.
4. Pull values from `.cache/` first; optionally call the LLM for leftovers.
5. Post-process fetched keys only (`post_process_fields` with `fields_only`).
6. Write `*.enrich-proposal.md` under `--proposal-dir` (always). Optionally `--apply`.

## Module reference
- `parse_input(filepath)`: read lines into structured dicts; warns on invalid
rows.
- `extract_template_fields(template_path)`: extract YAML frontmatter field
  names,
filtering out blacklisted fields.
- `get_cache_key(title, artist, *, provider)`: normalize to cache filename (Perplexity keeps the legacy `.json` name).
- `load_from_cache / save_to_cache`: JSON cache helpers under `.cache/`.
- `query_painting_metadata(..., resolved=ResolvedModel)`: dispatches to Perplexity or Kimi (OpenAI-compatible).
- `post_process_fields(data, template_fields)`: convert comma-separated strings
to lists and wrap wikilinks; drop `"Unknown"` values (except for description).
- `render_markdown(template_path, painting_data, today, template_fields)`: fill
template placeholders and YAML lists dynamically based on template fields.
- `write_output(output_dir, filename, content)`: ensure dirs exist and persist
markdown.
- `run_new(...)`: programmatic entry for generating notes from inputs.
- `post_process_fields(data, template_fields, fields_only=...)`: factual string
cleanup; enrich passes `fields_only` so untouched note keys are not erased.
- `main(argv=None)`: setuptools console entry (`gesso` script); parses `argv` or `sys.argv`
- `run_enrich(...)` (`gesso.enrich`): programmatic enrich + proposal paths.
## Usage Examples

```bash
gesso new --input data/input.txt
gesso new --input data/input.txt --template my-template.md
gesso new --input paintings.txt --output notes/ --cache .cache/ --template templates/custom.md

# backward compatible
gesso --input data/input.txt

gesso enrich \
  --note ./Notes/Retrieve.md \
  --template "./Templates/Painting Template.md" \
  --attachments ./Attachments \
  --cache .cache \
  --model kimi \
  --proposal-dir manifests/painting-enrichment
```

## Error handling
- Missing env key: fails fast (`new` runs always validate; enrich only validates
when a live query is necessary).
- Template errors: fails if template file not found or has no fields to collect.
- Input parse errors: warn and skip lines.
- API failures: log error and skip that painting.
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
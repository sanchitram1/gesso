# Paintings Vault Automation

Generate Obsidian-ready painting notes from a simple input list. The CLI reads `PERPLEXITY_API_KEY` from your environment (or `.env`), enriches each row via Perplexity, and writes markdown files from the bundled template.

## Quickstart
- Install deps: `pkgx uv sync`
- Export `PERPLEXITY_API_KEY` (or add to `.env`)
- Run: `pkgx uv run imbue --input data/input.txt --output outputs/`
  - Defaults: `--input data/input.txt --output outputs/ --cache .cache`

## Input & Template
- Input lines: `number: Title, Artist` (optional `, Location` is ignored today).
- Default template: `data/painting-template.md`; output files land in `outputs/{title}.md`.
- Cache: `.cache/{title_artist}.json` to avoid duplicate API calls.
- Open TODO: make template path configurable (flag or env) so non-default templates work.

## Flow (per painting)
1. Parse input line into `{number, title, artist}`.
2. Check cache; otherwise query Perplexity for metadata.
3. Post-process strings into Obsidian-friendly lists/links.
4. Render template placeholders and frontmatter.
5. Write markdown to the output directory.

## Module reference
- `parse_input(filepath)`: read lines into structured dicts; warns on invalid rows.
- `get_cache_key(title, artist)`: normalize to cache filename.
- `load_from_cache / save_to_cache`: JSON cache helpers under `.cache/`.
- `query_painting_metadata(title, artist)`: Perplexity SDK wrapper using `PERPLEXITY_API_KEY`.
- `post_process_fields(data)`: convert comma-separated strings to lists and wrap wikilinks; drop `"Unknown"` values.
- `render_markdown(template_path, painting_data, today)`: fill template placeholders and YAML lists.
- `write_output(output_dir, filename, content)`: ensure dirs exist and persist markdown.
- `main(...)`: CLI orchestrator; invoked via `pkgx uv run imbue`.

## Error handling
- Missing env key: fails fast with a clear message.
- Input parse errors: warn and skip lines.
- Perplexity failures: log error and skip that painting.
- Cache/IO issues: log warnings and continue to the next item.

## Development
- Python 3.13+, managed with `uv`.
- Style: `pkgx uv run ruff format --check .` and `pkgx uv run ruff check .`
- Tests: `pkgx uv run pytest -v --cov --cov-report=xml`
- CI mirrors these steps (`.github/workflows/ci.yml`).

## Contributing
- Keep README aligned with behavior; update TODOs when adding features.
- Add tests for new parsing, templating, or API edge cases.
- Run lint/format/tests before sending changes.
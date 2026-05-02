# Paintings Vault Automation — Agent Notes

High-level guidance for agents. Full implementation details live in `README.md`.

## Overview
- CLI to turn `data/input.txt` rows into Obsidian markdown using **Perplexity** or **Kimi (Moonshot)** (`--model`). Keys: `PERPLEXITY_API_KEY`, or `MOONSHOT_API_KEY` / `KIMI_API_KEY` for Kimi.
- Uses the bundled template in `data/painting-template.md`; outputs go to `outputs/`.
- Cache sits under `.cache/` to avoid duplicate queries.

## Build & Test
- Install deps: `pkgx uv sync`
- Format check: `pkgx uv run ruff format --check .`
- Lint: `pkgx uv run ruff check .`
- Tests: `pkgx uv run pytest -v --cov --cov-report=xml`

## Code Style
- Python 3.13+, ruff for lint/format.
- Prefer `pkgx uv run ...` for all tooling.

## Testing Workflow
- Unit tests live in `tests/`; add fixtures for new parsing or templating behaviors.
- Avoid network in tests—mock Perplexity if needed; rely on cached payloads instead.

## Contribution Guidelines
- Update `README.md` when behavior changes; keep commands in sync with CI.
- Add/adjust TODOs when introducing feature ideas (e.g., template configurability).
- Run format, lint, and tests before submitting changes.

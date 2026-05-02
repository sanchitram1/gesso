"""
Enrich existing Obsidian painting notes by filling missing factual frontmatter fields.
Writes a Markdown proposal file by default (no in-place edits unless --apply).
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from . import main as main_mod
from .llm import query_painting_metadata
from .llm_types import PaintingQuerySnapshot
from .model_spec import ResolvedModel, resolve_model

# Frontmatter keys we never fetch from the API and never overwrite from enrichment.
ENRICH_PERSONAL_KEYS = frozenset(
    {"rating", "seen", "created", "tags", "category", "title", "artist", "date"}
)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)^---\s*\n?", re.DOTALL | re.MULTILINE)


def _markdown_fenced_block(body: str, info: str = "") -> str:
    """Fence ``body`` so inner triple-backticks cannot close the outer fence."""
    fence = "```"
    while fence in body:
        fence += "`"
    lang = f"{info}" if info else ""
    return f"{fence}{lang}\n{body.rstrip()}\n{fence}\n"


def strip_obsidian_plain(value: str) -> str:
    """Strip quotes and outer [[wikilinks]] for plaintext title/artist."""
    s = value.strip()
    while True:
        t = s.strip('"').strip("'")
        if t.startswith("[[") and t.endswith("]]"):
            s = t[2:-2].strip()
            continue
        return t


def plaintext_from_frontmatter(value: Any) -> str:
    """Coerce a frontmatter value to a single plaintext string for API queries."""
    if value is None:
        return ""
    if isinstance(value, list):
        if not value:
            return ""
        return plaintext_from_frontmatter(value[0])
    if not isinstance(value, str):
        return str(value).strip()
    return strip_obsidian_plain(value)


def parse_note_markdown(note_text: str) -> tuple[dict[str, Any], str]:
    """
    Split note into YAML frontmatter dict and body (remaining markdown after closing ---).
    """
    text = note_text.lstrip("\ufeff")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError("Note has no YAML frontmatter (expected leading --- block).")
    raw_yaml = m.group(1)
    body = text[m.end() :]
    loaded = yaml.safe_load(raw_yaml)
    if loaded is None:
        fm: dict[str, Any] = {}
    elif not isinstance(loaded, dict):
        raise ValueError("Frontmatter must parse to a YAML mapping (object).")
    else:
        fm = loaded
    return fm, body


def read_note(path: str | Path) -> tuple[dict[str, Any], str]:
    p = Path(path)
    with open(p, encoding="utf-8") as f:
        return parse_note_markdown(f.read())


def infer_title_artist(frontmatter: dict[str, Any]) -> tuple[str, str]:
    title = plaintext_from_frontmatter(frontmatter.get("title"))
    artist = plaintext_from_frontmatter(frontmatter.get("artist"))
    return title, artist


def is_missing_factual_value(value: Any) -> bool:
    """True if the field should be considered empty for enrichment purposes."""
    if value is None:
        return True
    if isinstance(value, list):
        if len(value) == 0:
            return True
        return all(is_missing_factual_value(v) for v in value)
    if isinstance(value, str):
        s = strip_obsidian_plain(value)
        if s == "":
            return True
        return s.lower() == "unknown"
    if isinstance(value, (int, float, bool)):
        return False
    s = str(value).strip()
    return s == "" or s.lower() == "unknown"


def raw_cache_value_usable(value: Any) -> bool:
    """Whether a cached API value counts as filling a missing field."""
    if value is None:
        return False
    if isinstance(value, str):
        s = value.strip()
        return s != "" and s.lower() != "unknown"
    return True


def missing_queryable_fields(
    frontmatter: dict[str, Any], template_fields: list[str]
) -> list[str]:
    """Template fields that are missing/empty in the note and are safe to query."""
    missing: list[str] = []
    for field in template_fields:
        if field in ENRICH_PERSONAL_KEYS:
            continue
        if is_missing_factual_value(frontmatter.get(field)):
            missing.append(field)
    return missing


def merge_cache_fragment(
    cache_dir: str, cache_key: str, fragment: dict[str, Any]
) -> None:
    """Merge API fragment into existing cache JSON (preserves other keys)."""
    existing = main_mod.load_from_cache(cache_dir, cache_key) or {}
    merged = {**existing, **fragment}
    main_mod.save_to_cache(cache_dir, cache_key, merged)


def fetch_metadata_for_missing(
    title: str,
    artist: str,
    missing_fields: list[str],
    cache_dir: str,
    *,
    resolved: ResolvedModel,
) -> tuple[dict[str, Any], bool, PaintingQuerySnapshot | None]:
    """
    Return raw field values (template names) for missing keys using cache and/or API.
    Second return value is True if a live API call was made.
    Third is request/response trace when an API call was made (including failed parses).
    """
    if not missing_fields:
        return {}, False, None

    cache_key = main_mod.get_cache_key(title, artist, provider=resolved.provider)
    cached = main_mod.load_from_cache(cache_dir, cache_key) or {}

    result: dict[str, Any] = {}
    still_missing: list[str] = []
    for field in missing_fields:
        if field in cached and raw_cache_value_usable(cached.get(field)):
            result[field] = cached[field]
        else:
            still_missing.append(field)

    if not still_missing:
        return result, False, None

    main_mod.require_llm_credentials(resolved)

    answer = query_painting_metadata(
        title, artist, fields=still_missing, resolved=resolved
    )
    api_data = answer.data
    snapshot = answer.snapshot

    if not api_data:
        return result, True, snapshot

    fragment: dict[str, Any] = {}
    for field in still_missing:
        if field in api_data and raw_cache_value_usable(api_data.get(field)):
            fragment[field] = api_data[field]
            result[field] = api_data[field]

    if fragment:
        merge_cache_fragment(cache_dir, cache_key, fragment)

    return result, True, snapshot


def build_proposed_frontmatter(
    current: dict[str, Any],
    template_fields: list[str],
    processed_by_field: dict[str, Any],
    missing_before: list[str],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """
    Merge post-processed factual values into a copy of current frontmatter.

    Returns (proposed, fields_changed, still_unresolved).
    """
    proposed = deepcopy(current)
    changed: list[str] = []
    still_unresolved: list[str] = []

    for field in missing_before:
        if field in ENRICH_PERSONAL_KEYS:
            continue
        new_val = processed_by_field.get(field)
        if not is_missing_factual_value(new_val):
            old_val = current.get(field)
            proposed[field] = new_val
            if old_val != new_val:
                changed.append(field)
        else:
            still_unresolved.append(field)

    return proposed, changed, still_unresolved


def dump_frontmatter_yaml(data: dict[str, Any]) -> str:
    return yaml.dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1000,
    ).rstrip()


def render_proposal_markdown(
    *,
    note_path: Path,
    template_path: Path,
    attachments_dir: Path | None,
    current_fm: dict[str, Any],
    proposed_fm: dict[str, Any],
    fields_changed: list[str],
    fields_still_empty: list[str],
    image_candidate: str,
    image_source: str,
    api_backend_label: str,
    used_api: bool,
    llm_snapshot: PaintingQuerySnapshot | None,
    cache_dir: str,
    template_fields: list[str],
) -> str:
    """Build the proposal document body (Markdown)."""
    lines: list[str] = [
        f"# Enrichment proposal: `{note_path.name}`",
        "",
        "## Source",
        f"- **Note:** `{note_path}`",
        f"- **Template:** `{template_path}`",
        f"- **Cache:** `{cache_dir}`",
    ]
    if attachments_dir is not None:
        lines.append(f"- **Attachments (reference):** `{attachments_dir}`")
    lines.extend(
        [
            "",
            "## Summary",
            f"- **Queryable template fields:** {', '.join(template_fields) or '(none)'}",
            f"- **API call:** {'yes' if used_api else 'no (cache / no missing fields)'} "
            f"({api_backend_label})",
            f"- **Fields updated in proposal:** {', '.join(fields_changed) or '(none)'}",
            f"- **Still empty / unresolved:** {', '.join(fields_still_empty) or '(none)'}",
            "",
            "## Fields changed",
        ]
    )
    if fields_changed:
        for f in fields_changed:
            lines.append(f"- `{f}`")
    else:
        lines.append("- _(no factual fields changed)_")

    lines.extend(
        [
            "",
            "## Unresolved / left unchanged",
            "These queryable fields were missing before and remain empty or unknown after fetch/cache:",
        ]
    )
    if fields_still_empty:
        for f in fields_still_empty:
            lines.append(f"- `{f}`")
    else:
        lines.append("- _(none)_")

    if llm_snapshot is not None:
        req_json = json.dumps(llm_snapshot.request_json, indent=2, ensure_ascii=False)
        raw = (
            llm_snapshot.raw_response
            if llm_snapshot.raw_response is not None
            else "_(empty)_"
        )
        lines.extend(
            [
                "",
                "## LLM request",
                f"- **Provider:** `{llm_snapshot.provider}`",
                f"- **Model:** `{llm_snapshot.model}`",
                f"- **Template fields queried:** "
                f"{', '.join(llm_snapshot.fields_queried) or '(none)'}",
                "",
            ]
        )
        lines.append(_markdown_fenced_block(req_json, "json"))
        lines.extend(
            [
                "",
                "## LLM response (raw)",
            ]
        )
        lines.append(_markdown_fenced_block(raw, "text"))

    lines.extend(
        [
            "",
            "## Image candidate",
            f"- **URL / value:** {image_candidate or '_(none)_'}",
            f"- **Source:** {image_source}",
            "",
            "## Current frontmatter",
            "```yaml",
            dump_frontmatter_yaml(current_fm),
            "```",
            "",
            "## Proposed frontmatter",
            "```yaml",
            dump_frontmatter_yaml(proposed_fm),
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def write_full_note(path: Path, frontmatter: dict[str, Any], body: str) -> None:
    """Write note with YAML frontmatter and preserved body."""
    fm_block = dump_frontmatter_yaml(frontmatter)
    content = f"---\n{fm_block}\n---\n{body}"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def run_enrich(
    *,
    note_path: str | Path,
    template_path: str | Path,
    cache_dir: str = ".cache",
    attachments_dir: str | Path | None = None,
    proposal_dir: str | Path = "manifests/painting-enrichment",
    apply: bool = False,
    model: str = "perplexity",
) -> Path:
    """
    Enrich a single note; write proposal under proposal_dir. If apply=True, also
    overwrite the note with proposed frontmatter (body unchanged).
    Returns path to the proposal file.
    """
    note_p = Path(note_path).expanduser().resolve()
    template_p = Path(template_path).expanduser().resolve()
    if not note_p.is_file():
        raise SystemExit(f"[ERROR] Note not found: {note_p}")
    if not template_p.is_file():
        raise SystemExit(f"[ERROR] Template not found: {template_p}")

    resolved = resolve_model(model)
    api_backend_label = f"{resolved.provider} / {resolved.api_model}"

    current_fm, body = read_note(note_p)
    title, artist = infer_title_artist(current_fm)
    if not title or not artist:
        raise SystemExit(
            "[ERROR] Could not infer title and artist from note frontmatter "
            "(need non-empty title and artist)."
        )

    template_fields = main_mod.extract_template_fields(str(template_p))
    missing_before = missing_queryable_fields(current_fm, template_fields)

    used_api = False
    llm_snapshot: PaintingQuerySnapshot | None = None
    new_raw: dict[str, Any] = {}
    if missing_before:
        new_raw, used_api, llm_snapshot = fetch_metadata_for_missing(
            title, artist, missing_before, cache_dir, resolved=resolved
        )

    merged_raw = {"title": title, "artist": artist}
    merged_raw.update(
        {k: v for k, v in new_raw.items() if k not in {"title", "artist"}}
    )
    fetched_field_names = [k for k in new_raw if k not in {"title", "artist"}]

    processed = main_mod.post_process_fields(
        merged_raw,
        template_fields,
        fields_only=fetched_field_names if fetched_field_names else [],
    )

    proposed_fm, fields_changed, still_empty = build_proposed_frontmatter(
        current_fm, template_fields, processed, missing_before
    )

    image_candidate = str(processed.get("image") or new_raw.get("image") or "").strip()
    if used_api:
        image_source = (
            f"{api_backend_label} — responses are merged into the JSON cache bucket"
        )
    elif image_candidate:
        image_source = (
            "Resolved entirely from `.cache/` on this session (no live query)"
        )
    else:
        image_source = "No image candidate was produced while filling gaps"

    att_p = Path(attachments_dir).expanduser().resolve() if attachments_dir else None
    prop_base = Path(proposal_dir).expanduser().resolve()
    prop_base.mkdir(parents=True, exist_ok=True)
    proposal_file = prop_base / f"{note_p.stem}.enrich-proposal.md"

    md = render_proposal_markdown(
        note_path=note_p,
        template_path=template_p,
        attachments_dir=att_p,
        current_fm=current_fm,
        proposed_fm=proposed_fm,
        fields_changed=sorted(fields_changed),
        fields_still_empty=sorted(still_empty),
        image_candidate=image_candidate,
        image_source=image_source,
        api_backend_label=api_backend_label,
        used_api=used_api,
        llm_snapshot=llm_snapshot,
        cache_dir=cache_dir,
        template_fields=template_fields,
    )
    with open(proposal_file, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[WRITE] Proposal: {proposal_file}")

    if apply:
        write_full_note(note_p, proposed_fm, body)
        print(f"[APPLY] Updated note: {note_p}")

    return proposal_file

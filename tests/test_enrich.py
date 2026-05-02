import json
from pathlib import Path

import pytest
import yaml

from gesso import main as cli_main
from gesso.llm_types import PaintingMetadataAnswer, PaintingQuerySnapshot
from gesso.enrich import (
    build_proposed_frontmatter,
    infer_title_artist,
    missing_queryable_fields,
    parse_note_markdown,
    render_proposal_markdown,
)
from gesso.main import post_process_fields


def test_parse_note_markdown_splits_body():
    fm, body = parse_note_markdown(
        """---
title: "Winter"
artist: '[[Ada X]]'
year:
---
Intro

More.
"""
    )
    assert fm["title"] == "Winter"
    assert body.startswith("Intro\n")


def test_infer_title_artist_strips_links_and_quotes():
    title, artist = infer_title_artist(
        {"title": '[["Sunflowers"]]', "artist": "[[Vincent]]"}
    )
    assert title == "Sunflowers"
    assert artist == "Vincent"


def test_missing_queryable_fields_lists_only_empty_templates():
    template_fields = ["year", "style", "image"]
    fm = yaml.safe_load(
        """
title: Idle
artist: Someone
year: 1900
style:
image:
"""
    )
    assert missing_queryable_fields(fm, template_fields) == ["style", "image"]


class TestProposalRender:
    def test_sections_present(self):
        md = render_proposal_markdown(
            note_path=Path("/tmp/Retrieve.md"),
            template_path=Path("/tmp/template.md"),
            attachments_dir=None,
            current_fm={"title": "A"},
            proposed_fm={"title": "A", "year": 1},
            fields_changed=["year"],
            fields_still_empty=["style"],
            image_candidate="https://example.com/img.jpg",
            image_source="test",
            api_backend_label="perplexity / sonar-pro",
            used_api=True,
            llm_snapshot=None,
            cache_dir=".cache",
            template_fields=["year"],
        )
        assert "Current frontmatter" in md and "Proposed frontmatter" in md
        assert "`year`" in md and "`style`" in md
        assert "https://example.com/img.jpg" in md

    def test_includes_llm_request_and_response_when_snapshot_set(self):
        snap = PaintingQuerySnapshot(
            provider="perplexity",
            model="sonar-pro",
            fields_queried=["year", "style"],
            request_json={
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": "prompt text"}],
            },
            raw_response='{"year": 1900}',
        )
        md = render_proposal_markdown(
            note_path=Path("/tmp/n.md"),
            template_path=Path("/tmp/t.md"),
            attachments_dir=None,
            current_fm={"title": "A"},
            proposed_fm={"title": "A"},
            fields_changed=[],
            fields_still_empty=[],
            image_candidate="",
            image_source="src",
            api_backend_label="perplexity / sonar-pro",
            used_api=True,
            llm_snapshot=snap,
            cache_dir=".cache",
            template_fields=["year"],
        )
        assert "## LLM request" in md
        assert "## LLM response (raw)" in md
        assert "prompt text" in md
        assert '"year": 1900' in md


def test_build_proposed_updates_only_nonempty():
    processed = {"year": 1900}
    curr = {"title": "T", "artist": "A", "year": ""}
    proposed, changed, unresolved = build_proposed_frontmatter(
        curr,
        ["year", "style"],
        processed,
        missing_before=["year", "style"],
    )
    assert proposed["year"] == 1900
    assert "year" in changed
    assert "style" in unresolved


def test_post_process_fields_only_scoped_fields():
    data = {"title": "T", "artist": "Jean", "museum": "Louvre"}
    tpl = ["museum", "style"]
    scoped = post_process_fields(data, tpl, fields_only=["museum"])
    assert scoped["museum"] == ["[[Louvre]]"]
    assert "style" not in scoped


def test_run_enrich_cache_hit_writes_proposal(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    template = Path("tpl.md")
    template.write_text(
        """---
title:
artist:
year:
---

# hello
"""
    )

    cache_dir = Path(".cache")
    cache_dir.mkdir()
    ck = cli_main.get_cache_key("Sea", "Waves")
    (cache_dir / ck).write_text(json.dumps({"year": 1812}))

    note = Path("note.md")
    note.write_text(
        """---
title: Sea
artist: Waves
year:
---

body
"""
    )

    from gesso import enrich as enrich_module

    called = []

    def fake(title, artist, fields, **kwargs):
        called.append((title, artist, fields))
        return PaintingMetadataAnswer(data={})

    monkeypatch.setattr(enrich_module, "query_painting_metadata", fake)

    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)

    proposal_dir = Path("manifests/out")
    from gesso.enrich import run_enrich

    out = run_enrich(
        note_path=note,
        template_path=template,
        cache_dir=str(cache_dir),
        proposal_dir=proposal_dir,
    )

    assert called == [], "cached fields should suppress Perplexity"
    prop = proposal_dir / "note.enrich-proposal.md"
    assert prop.resolve() == out
    text = prop.read_text(encoding="utf-8")
    assert "Current frontmatter" in text
    assert "## Fields changed" in text


def _patch_run_new(monkeypatch):
    invoked = []

    def fake(**kwargs):
        invoked.append(kwargs)

    monkeypatch.setattr(cli_main, "run_new", fake)
    return invoked


def test_main_prepends_new_for_flag_only_argv(monkeypatch):
    invoked = _patch_run_new(monkeypatch)
    cli_main.main(["--cache", ".cache"])
    assert invoked and invoked[0]["cache_dir"] == ".cache"


def test_main_explicit_new_subcommand(monkeypatch):
    invoked = _patch_run_new(monkeypatch)
    cli_main.main(["new", "--cache", ".cache"])
    assert invoked and invoked[0]["cache_dir"] == ".cache"


@pytest.mark.skipif(
    not Path("/Users/sanch/Obsidian/collections/Notes/Retrieve.md").exists(),
    reason="Local Obsidian note not present on this runner",
)
def test_enrich_retrieve_integration(tmp_path, monkeypatch):
    """Smoke test against a real vault file when mounted; never applies."""
    monkeypatch.chdir(tmp_path)
    note = Path("/Users/sanch/Obsidian/collections/Notes/Retrieve.md")
    tpl = Path("/Users/sanch/Obsidian/collections/Templates/Painting Template.md")
    att = Path("/Users/sanch/Obsidian/collections/Attachments")

    monkeypatch.setenv("PERPLEXITY_API_KEY", "test-key")

    from gesso import enrich as enrich_mod

    def fake(title, artist, fields, **kwargs):
        return PaintingMetadataAnswer(
            data={
                **{f: (f"filled-{f}" if f != "year" else 1800) for f in fields},
            },
        )

    monkeypatch.setattr(enrich_mod, "query_painting_metadata", fake)

    from gesso.enrich import run_enrich

    if not tpl.is_file():
        pytest.fail("Painting Template missing in expected location")

    out = run_enrich(
        note_path=note,
        template_path=tpl,
        cache_dir=".cache-retrieve-test",
        attachments_dir=att if att.exists() else None,
        proposal_dir=tmp_path / "proposals",
    )
    assert out.is_file()
    assert "## Proposed frontmatter" in out.read_text(encoding="utf-8")


def test_main_enrich_subcommand_invokes_run_enrich(monkeypatch, tmp_path):
    invoked = []

    def fake(**kwargs):
        invoked.append(kwargs)

    note = tmp_path / "n.md"
    note.write_text(
        """---
title: T
artist: A
year:
---
"""
    )
    tpl = tmp_path / "t.md"
    tpl.write_text(
        """---
title:
artist:
year:
style:
---
"""
    )

    monkeypatch.setattr("gesso.enrich.run_enrich", fake)
    cli_main.main(
        [
            "enrich",
            "--note",
            str(note),
            "--template",
            str(tpl),
            "--cache",
            str(tmp_path / "c"),
            "--proposal-dir",
            str(tmp_path / "p"),
        ]
    )
    assert invoked and Path(invoked[0]["note_path"]) == note.resolve()

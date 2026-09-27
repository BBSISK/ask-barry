from pathlib import Path

import pytest

from app.chunking import (
    chunk_markdown,
    clean_markdown,
    github_slug,
    pack_paragraphs,
    split_sections,
)

FIXTURE = (Path(__file__).parent / "fixtures" / "sample_readme.md").read_text()
URL = "https://github.com/BBSISK/demo/blob/abc123/README.md"


@pytest.fixture
def chunks():
    return chunk_markdown(FIXTURE, repo="demo", path="README.md", url=URL, commit_sha="abc123")


def by_heading(chunks, heading):
    return [c for c in chunks if c.heading == heading]


def test_heading_breadcrumbs(chunks):
    headings = [c.heading for c in chunks]
    assert "Demo Project" in headings
    assert "Demo Project > Setup" in headings
    assert "Demo Project > Testing > CI/CD Pipeline" in headings


def test_intro_text_before_first_heading_is_kept(chunks):
    intro = by_heading(chunks, "")
    assert len(intro) == 1
    assert "Intro paragraph" in intro[0].text
    assert intro[0].url == URL          # no anchor for pre-heading text


def test_heading_inside_code_fence_is_not_a_heading(chunks):
    setup = by_heading(chunks, "Demo Project > Setup")[0]
    assert "# This is a shell comment" in setup.text
    assert all("shell comment" not in c.heading for c in chunks)


def test_empty_sections_are_skipped(chunks):
    assert not by_heading(chunks, "Demo Project > Empty Section")


def test_badges_and_comments_removed(chunks):
    joined = "\n".join(c.text for c in chunks)
    assert "badge.svg" not in joined
    assert "<!--" not in joined


def test_breadcrumb_prefixed_to_text(chunks):
    ci = by_heading(chunks, "Demo Project > Testing > CI/CD Pipeline")[0]
    assert ci.text.startswith("Demo Project > Testing > CI/CD Pipeline\n\n")
    assert "Render deploys only after CI passes." in ci.text


def test_metadata_and_anchor_links(chunks):
    ci = by_heading(chunks, "Demo Project > Testing > CI/CD Pipeline")[0]
    assert ci.repo == "demo" and ci.path == "README.md" and ci.commit_sha == "abc123"
    assert ci.anchor == "cicd-pipeline"
    assert ci.url == URL + "#cicd-pipeline"


def test_duplicate_headings_get_numbered_anchors(chunks):
    anchors = [c.anchor for c in by_heading(chunks, "Demo Project > Setup")]
    assert anchors == ["setup", "setup-1"]


def test_chunk_ids_unique_and_deterministic(chunks):
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    again = chunk_markdown(FIXTURE, repo="demo", path="README.md", url=URL, commit_sha="abc123")
    assert [c.chunk_id for c in again] == ids
    assert [c.content_hash for c in again] == [c.content_hash for c in chunks]


def test_long_section_split_within_limit_with_overlap():
    paragraphs = [f"Paragraph {i} " + "word " * 60 for i in range(20)]   # ~320 chars each
    doc = "# Big\n\n" + "\n\n".join(paragraphs)
    result = chunk_markdown(doc, repo="r", path="p.md", url="u", max_chars=1000)
    assert len(result) > 1
    assert all(len(c.text) <= 1000 for c in result)
    # one paragraph of overlap between consecutive pieces
    last_para_of_first = result[0].text.split("\n\n")[-1]
    assert last_para_of_first in result[1].text


def test_giant_single_paragraph_is_hard_split():
    doc = "# Big\n\n" + "x" * 5000
    result = chunk_markdown(doc, repo="r", path="p.md", url="u", max_chars=1000)
    assert all(len(c.text) <= 1000 for c in result)
    assert sum(c.text.count("x") for c in result) == 5000


def test_code_block_not_split_by_blank_lines():
    doc = "# Code\n\n```python\ndef a():\n\n    return 1\n```\n"
    [chunk] = chunk_markdown(doc, repo="r", path="p.md", url="u")
    assert "def a():\n\n    return 1" in chunk.text


def test_empty_document_gives_no_chunks():
    assert chunk_markdown("", repo="r", path="p.md", url="u") == []


def test_max_chars_too_small_rejected():
    with pytest.raises(ValueError):
        chunk_markdown("# x\n\ny", repo="r", path="p.md", url="u", max_chars=50)


@pytest.mark.parametrize("heading,slug", [
    ("Getting Started", "getting-started"),
    ("CI/CD Pipeline", "cicd-pipeline"),
    ("`models.py` & Schema", "modelspy--schema"),
    ("What's New?", "whats-new"),
])
def test_github_slug(heading, slug):
    assert github_slug(heading) == slug


def test_split_sections_levels():
    sections = split_sections("pre\n# A\na\n## B\nb")
    assert [(lv, t) for lv, t, _ in sections] == [(0, ""), (1, "A"), (2, "B")]


def test_clean_markdown_keeps_normal_links():
    assert "[docs](https://x.y)" in clean_markdown("See [docs](https://x.y) ![img](a.png)")


def test_pack_paragraphs_respects_limit():
    pieces = pack_paragraphs(["a" * 400] * 5, max_chars=1000)
    assert all(len(p) <= 1000 for p in pieces)


def test_breadcrumb_strips_link_and_code_markup():
    doc = "# Guide\n\n## Pillar 4: MCP Server ([`mcp_server.py`](mcp_server.py))\n\nText."
    [chunk] = chunk_markdown(doc, repo="r", path="p.md", url="u")
    assert chunk.heading == "Guide > Pillar 4: MCP Server (mcp_server.py)"

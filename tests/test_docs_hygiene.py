"""This repo's own README and docs are part of the search corpus, so they must not leak the test set.

If a README quoted a golden question, or named a trap-question skill, retrieval would "find" the
test instead of the evidence, and a trap could turn into a false positive.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAP_TERMS = ("kubernetes", "swift", "kotlin", "react", "phd", "mongodb", "kafka", "yolov8", "scrum", "agile")
# "aws" left the list on 3 Oct 2026: trap-02 became answerable (aws-01) once Stage 10 documented real AWS work.


def indexed_docs():
    """Files from this repo that fetch_docs would index (root Markdown + docs/, minus docs/eval/)."""
    files = list(ROOT.glob("*.md")) + [p for p in (ROOT / "docs").rglob("*.md") if "eval" not in p.parts]
    return {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8").lower() for p in files}


def test_no_golden_question_is_quoted_in_indexed_docs():
    questions = json.loads((ROOT / "eval" / "golden_set.json").read_text(encoding="utf-8"))["questions"]
    for name, text in indexed_docs().items():
        for q in questions:
            assert q["question"].lower().rstrip("?") not in text, f"{name} quotes test question {q['id']}"


def test_no_trap_skill_is_named_in_indexed_docs():
    for name, text in indexed_docs().items():
        for term in TRAP_TERMS:
            assert not re.search(rf"\b{term}\b", text), f"{name} mentions trap term '{term}'"


def test_model_card_is_linked_and_covers_the_essentials():
    card = (ROOT / "docs" / "model-card.md").read_text(encoding="utf-8")
    for section in ("Intended use", "Not intended for", "Known limitations", "EU AI Act", "Evaluation"):
        assert section in card
    assert "docs/model-card.md" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert "model-card.md" in (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")


def test_ai_disclosure_on_page_and_in_api():
    from app.answering import Answer
    assert "AI assistant" in (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
    assert Answer("q", "a", True).to_dict()["ai_generated"] is True

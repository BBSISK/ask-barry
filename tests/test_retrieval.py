import json
from pathlib import Path

import pytest

from app.retrieval import BM25Retriever, load_chunks, tokenize
from scripts.evaluate_retrieval import evaluate, load_golden, validate_golden

GOLDEN = Path(__file__).parent.parent / "eval" / "golden_set.json"


def chunk(repo, text, path="README.md"):
    return {"repo": repo, "path": path, "heading": "", "text": text}


CHUNKS = [
    chunk("wall", "Terraform provisions the Render web service and PostgreSQL database."),
    chunk("wall", "The MCP server exposes four tools over JSON-RPC."),
    chunk("brief", "Prompts arrive by WhatsApp or email every week."),
    chunk("brief", "WhatsApp WhatsApp WhatsApp templates are approved by Meta."),
    chunk("profile", "Barry spent 30 years at Intel Ireland leading engineering teams."),
]


# --- tokenizer --------------------------------------------------------------

def test_tokenize_lowercases_drops_stopwords_and_plurals():
    assert tokenize("How does Barry use the Tests and Agents?") == ["use", "test", "agent"]


def test_tokenize_keeps_identifiers_and_short_plurals():
    assert tokenize("mcp_server.py has 86 tests; CSS class") == ["mcp_server", "py", "86", "test", "css", "class"]


# --- BM25 -------------------------------------------------------------------

def test_best_match_ranks_first():
    r = BM25Retriever(CHUNKS)
    top = r.search("Which infrastructure as code tool, Terraform?", k=3)
    assert top[0].chunk["text"].startswith("Terraform")
    assert top[0].rank == 1


def test_rare_terms_outweigh_common_terms():
    # Equal-length chunks, each word once: "flask" is in 3 of 4 chunks, "terraform" in 1.
    docs = [
        chunk("a", "flask app alpha"),
        chunk("b", "flask app beta"),
        chunk("c", "flask app gamma"),
        chunk("d", "terraform app delta"),
    ]
    results = BM25Retriever(docs).search("flask terraform", k=4)
    assert results[0].chunk["repo"] == "d"          # the rare word wins
    assert len(results) == 4


def test_term_frequency_saturates():
    r = BM25Retriever(CHUNKS)
    scores = {res.chunk["text"][:10]: res.score for res in r.search("whatsapp", k=5)}
    repeated, single = scores["WhatsApp W"], scores["Prompts ar"]
    assert repeated > single
    assert repeated < 3 * single          # 3x the mentions is NOT 3x the score


def test_no_overlap_returns_nothing():
    assert BM25Retriever(CHUNKS).search("kubernetes helm") == []


def test_empty_or_stopword_query_returns_nothing():
    r = BM25Retriever(CHUNKS)
    assert r.search("") == []
    assert r.search("what is the") == []


def test_k_limits_results_and_ranks_are_sequential():
    results = BM25Retriever(CHUNKS).search("whatsapp email terraform mcp", k=2)
    assert [x.rank for x in results] == [1, 2]


def test_empty_corpus_rejected():
    with pytest.raises(ValueError):
        BM25Retriever([])


def test_load_chunks(tmp_path):
    p = tmp_path / "chunks.jsonl"
    p.write_text("\n".join(json.dumps(c) for c in CHUNKS) + "\n\n")
    assert load_chunks(p) == CHUNKS


# --- golden set + evaluation ------------------------------------------------

def test_golden_set_is_valid_and_balanced():
    questions = load_golden(GOLDEN)
    types = [q["type"] for q in questions]
    assert types.count("answerable") >= 25
    assert types.count("trap") >= 8


@pytest.mark.parametrize("bad", [
    {"questions": [{"id": "a", "type": "answerable", "question": "q", "expected": []}]},
    {"questions": [{"id": "t", "type": "trap", "question": "q", "expected": ["x/README.md"]}]},
    {"questions": [{"id": "d", "type": "trap", "question": "q", "expected": []},
                   {"id": "d", "type": "trap", "question": "q", "expected": []}]},
    {"questions": [{"id": "m", "type": "answerable", "question": "q"}]},
])
def test_validate_golden_rejects_bad_sets(bad):
    with pytest.raises(ValueError):
        validate_golden(bad)


def test_evaluate_metrics():
    questions = [
        {"id": "1", "type": "answerable", "question": "Terraform Render", "expected": ["wall/README.md"]},
        {"id": "2", "type": "answerable", "question": "Intel engineering", "expected": ["brief/README.md"]},  # wrong on purpose
        {"id": "3", "type": "trap", "question": "Kubernetes", "expected": []},
    ]
    rows, summary = evaluate(BM25Retriever(CHUNKS), questions)
    assert rows[0]["rank"] == 1
    assert rows[1]["rank"] is None
    assert summary["recall@1"] == 0.5
    assert summary["mrr"] == 0.5
    assert summary["n_traps"] == 1 and summary["traps_with_any_hit"] == 0


def test_corpus_sources_lists_repos_with_short_sha():
    from scripts.evaluate_retrieval import corpus_sources
    chunks = [{"repo": "b", "commit_sha": "1234567890"}, {"repo": "a", "commit_sha": ""}, {"repo": "b", "commit_sha": "x"}]
    assert corpus_sources(chunks) == "a, b@1234567"


def test_make_retriever_bm25_and_comparison_report():
    from scripts.evaluate_retrieval import evaluate, make_retriever, render_comparison
    r = make_retriever("bm25", CHUNKS)
    q = [{"id": "q1", "type": "answerable", "question": "Terraform", "expected": ["wall/README.md"]},
         {"id": "q2", "type": "answerable", "question": "kubernetes", "expected": ["wall/README.md"]}]
    report = render_comparison({"bm25": evaluate(r, q)}, len(CHUNKS), "wall@abc")
    assert "| bm25 | 0.50 |" in report and "q2" in report


# --- section-level scoring --------------------------------------------------

def test_section_rank_needs_right_file_and_the_answer():
    from app.retrieval import SearchResult
    from scripts.evaluate_retrieval import first_relevant_rank, first_section_rank
    results = [
        SearchResult({"repo": "profile", "path": "README.md", "text": "How I build: git push, CI, deploy"}, 3.0, 1),
        SearchResult({"repo": "other", "path": "README.md", "text": "email barry.b.sisk@gmail.com"}, 2.0, 2),
        SearchResult({"repo": "profile", "path": "README.md", "text": "Get in touch: Barry.B.Sisk@gmail.com"}, 1.0, 3),
    ]
    expected, evidence = {"profile/README.md"}, ["barry.b.sisk@gmail.com"]
    assert first_relevant_rank(results, expected) == 1            # right file, wrong section
    assert first_section_rank(results, expected, evidence) == 3   # wrong file at 2 doesn't count; case-insensitive


def test_validate_golden_requires_evidence_for_answerable():
    bad = {"questions": [{"id": "a", "type": "answerable", "question": "q", "expected": ["x/README.md"]}]}
    with pytest.raises(ValueError, match="evidence"):
        validate_golden(bad)


def test_check_evidence_flags_drifted_docs():
    from scripts.evaluate_retrieval import check_evidence
    chunks = [{"repo": "wall", "path": "README.md", "text": "Terraform provisions Render"}]
    questions = [
        {"id": "ok", "type": "answerable", "expected": ["wall/README.md"], "evidence": ["terraform"]},
        {"id": "gone", "type": "answerable", "expected": ["wall/README.md"], "evidence": ["Kafka"]},
        {"id": "t", "type": "trap", "expected": []},
    ]
    assert check_evidence(questions, chunks) == ["gone"]


def test_summary_reports_both_levels():
    from scripts.evaluate_retrieval import summarise
    rows = [{"type": "answerable", "rank": 1, "section_rank": 3, "top_score": 1.0},
            {"type": "answerable", "rank": 2, "section_rank": None, "top_score": 1.0}]
    s = summarise(rows)
    assert s["recall@1"] == 0.5 and s["section_recall@1"] == 0.0
    assert s["section_recall@3"] == 0.5 and s["section_mrr"] == pytest.approx(1 / 6)

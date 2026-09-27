"""Offline tests for Stage 6 answer scoring (no Azure calls: the judge is a fake)."""
import pytest

from app.answering import NO_EVIDENCE, Answer, Source
from scripts.evaluate_answers import (
    cited_answer_ok, parse_judge, render_report, run_checks, score_question, summarise,
)


def answer(text, supported=True, sources=(("BBSISK", "README.md", "Toolbox", "Cloud & DevOps: Docker · Terraform"),)):
    srcs = [Source(i, r, p, h, "u") for i, (r, p, h, _) in enumerate(sources, start=1)] if supported else []
    texts = [t for *_, t in sources] if supported else []
    return Answer("q", text, supported, srcs, 8, "gpt-4.1-mini", texts)


def judge_says(**verdict):
    calls = []

    def judge(kind, question, answer_text, sources_text):
        calls.append(kind)
        return verdict
    judge.calls = calls
    return judge


CLOUD_Q = {"id": "profile-10", "type": "answerable", "question": "What cloud tools has Barry used?",
           "expected": ["BBSISK/README.md"], "evidence": ["Terraform"],
           "checks": {"must_include": ["Terraform"], "must_not_include": ["Terraform (planned"]}}
TRAP_Q = {"id": "trap-01", "type": "trap", "question": "Has Barry used Kubernetes?", "expected": []}


# --- citation test ----------------------------------------------------------

def test_cited_answer_needs_right_file_and_evidence():
    assert cited_answer_ok(answer("x"), ["BBSISK/README.md"], ["terraform"])
    assert not cited_answer_ok(answer("x"), ["wall_inspector/README.md"], ["terraform"])
    assert not cited_answer_ok(answer("x"), ["BBSISK/README.md"], ["kafka"])


# --- regression checks ------------------------------------------------------

def test_checks_catch_the_terraform_roadmap_bug():
    bad = "Barry has used Docker and Terraform (planned for later stages)."
    good = "Barry used Terraform for Wall Inspector's Render infrastructure [1]."
    assert run_checks(bad, CLOUD_Q["checks"]) == ["contains 'Terraform (planned'"]
    assert run_checks(good, CLOUD_Q["checks"]) == []
    assert run_checks("Docker only", CLOUD_Q["checks"]) == ["missing 'Terraform'"]


# --- answerable scoring -----------------------------------------------------

def test_answerable_pass():
    row = score_question(CLOUD_Q, answer("Barry used Terraform [1]."), judge_says(faithful=True, unsupported=[]))
    assert row["passed"] and row["answered"] and row["cited_answer"] and row["faithful"]


def test_answerable_fails_when_judge_finds_unsupported_claim():
    row = score_question(CLOUD_Q, answer("Barry used Terraform and Kubernetes [1]."),
                         judge_says(faithful=False, unsupported=["Kubernetes"]))
    assert not row["passed"] and row["unsupported"] == ["Kubernetes"]


def test_answerable_fails_regression_check_even_if_judge_passes():
    row = score_question(CLOUD_Q, answer("Terraform (planned for later) [1]."), judge_says(faithful=True))
    assert not row["passed"] and row["check_failures"]


def test_answerable_refusal_is_a_miss_and_skips_judge():
    judge = judge_says(faithful=True)
    row = score_question(CLOUD_Q, answer(NO_EVIDENCE, supported=False), judge)
    assert not row["passed"] and row["answered"] is False and judge.calls == []
    assert row["check_failures"] == ["did not answer"]


# --- trap scoring -----------------------------------------------------------

def test_trap_refusal_passes_without_calling_judge():
    judge = judge_says(claims_skill=True)
    row = score_question(TRAP_Q, answer(NO_EVIDENCE, supported=False), judge)
    assert row["passed"] and judge.calls == []


def test_trap_grounded_no_passes():
    row = score_question(TRAP_Q, answer("Barry has not used Kubernetes; he deploys with Docker on Render [1]."),
                         judge_says(claims_skill=False, reason="says he has not"))
    assert row["passed"]


def test_trap_false_claim_fails():
    row = score_question(TRAP_Q, answer("Yes, Barry uses Kubernetes [1]."), judge_says(claims_skill=True, reason="claims it"))
    assert not row["passed"] and row["reason"] == "claims it"


def test_trap_unparseable_judge_counts_as_fail():
    row = score_question(TRAP_Q, answer("Maybe [1]."), judge_says(error="unparseable"))
    assert not row["passed"]


def test_parse_judge():
    assert parse_judge('{"faithful": true}') == {"faithful": True}
    assert "error" in parse_judge("nonsense")


# --- summary & report -------------------------------------------------------

def test_summary_and_report():
    rows = [
        score_question(CLOUD_Q, answer("Barry used Terraform [1]."), judge_says(faithful=True)),
        score_question(TRAP_Q, answer(NO_EVIDENCE, supported=False), judge_says()),
        score_question(TRAP_Q, answer("Yes [1]."), judge_says(claims_skill=True, reason="claims it")),
    ]
    s = summarise(rows)
    assert s["answered"] == 1.0 and s["faithful_of_answered"] == 1.0
    assert s["trap_no_false_claim"] == pytest.approx(0.5)
    assert s["passed"] == 2 and s["total"] == 3
    report = render_report(rows, s, "gpt-4.1-mini", when="2026-09-27")
    assert "Traps: no false claim** | **50%" in report
    assert "### trap-01 (trap)" in report and "claims it" in report


def test_api_payload_never_includes_cited_texts():
    assert "cited_texts" not in answer("x").to_dict()

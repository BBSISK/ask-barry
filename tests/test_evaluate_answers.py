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

    def judge(kind, question, answer_text, sources_text, other_text=""):
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
    a = answer("x")
    a.uncited_texts = ["wall_inspector/README.md (section: X)\nsome text"]
    assert "cited_texts" not in a.to_dict() and "uncited_texts" not in a.to_dict()


# --- evidence-based judge verdicts -----------------------------------------

def test_faithfulness_from_quoted_evidence():
    from scripts.evaluate_answers import faithfulness
    ok = {"claims": [{"claim": "uses Claude Code daily", "support": "I build with AI agents every day (Claude Code"}]}
    assert faithfulness(ok) == (True, [])
    bad = {"claims": [{"claim": "uses Claude Code", "support": "…Claude Code"},
                      {"claim": "uses Kubernetes", "support": None},
                      {"claim": "on AWS", "support": "null"}]}
    assert faithfulness(bad) == (False, ["uses Kubernetes", "on AWS"])
    assert faithfulness({"error": "x"}) == (False, ["x"])
    assert faithfulness({})[0] is False


def test_score_uses_quoted_evidence_not_a_bare_boolean():
    verdict = {"faithful": False, "claims": [{"claim": "Terraform", "support": "Docker · Terraform"}]}
    row = score_question(CLOUD_Q, answer("Barry used Terraform [1]."), judge_says(**verdict))
    assert row["faithful"] is True and row["passed"]


def test_report_lists_every_answer_for_review():
    rows = [score_question(TRAP_Q, answer("No, Barry has not used Kubernetes [1]."),
                           judge_says(claims_skill=False, reason="says he has not"))]
    report = render_report(rows, summarise(rows), "m", when="2026-09-27")
    assert "## All answers (for human review)" in report
    assert "No, Barry has not used Kubernetes" in report and "says he has not" in report


def test_invented_evidence_is_rejected():
    from scripts.evaluate_answers import faithfulness, quote_in_sources
    sources = "[1] **Cloud & DevOps:** Docker · Terraform · GitHub Actions"
    assert quote_in_sources("Cloud & DevOps: Docker", sources)                 # markdown ignored
    assert quote_in_sources("…Docker · Terraform…", sources)                   # fragments ok
    assert not quote_in_sources("Barry deployed Kubernetes clusters", sources)  # made up
    verdict = {"claims": [{"claim": "uses Docker", "support": "Docker · Terraform"},
                          {"claim": "uses Kubernetes", "support": "Kubernetes clusters on AKS"}]}
    ok, unsupported = faithfulness(verdict, sources)
    assert not ok and unsupported == ['uses Kubernetes (judge quoted "Kubernetes clusters on AKS", not found in sources)']


def test_quote_matching_ignores_formatting_but_not_wording():
    from scripts.evaluate_answers import quote_in_sources
    src = ("export labeled datasets in **Microsoft COCO 1.0 JSON** format for downstream "
           "Computer Vision (`CVAT` / `YOLOv8`) training. A[\"💬 Prompt<br/>Claude Code\"]")
    assert quote_in_sources("Microsoft COCO 1.0 JSON format for downstream Computer Vision (CVAT / YOLOv8) training", src)
    assert quote_in_sources("Prompt Claude Code", src)                          # HTML + emoji ignored
    assert not quote_in_sources("COCO 1.0 JSON format for model training", src)  # reworded
    assert not quote_in_sources("COCO", src)                                     # too short to prove anything
    assert not quote_in_sources("son format", src)                               # whole words only


def test_judge_sees_repo_and_section_labels_like_the_answerer():
    from scripts.evaluate_answers import judge_sources, quote_in_sources
    a = answer("x", sources=(("ask-barry", "README.md", "Current status: Stage 5 complete (RAG live in production)", "body"),))
    text = judge_sources(a)
    assert text.startswith("[1] ask-barry/README.md (section: Current status")
    assert quote_in_sources("Stage 5 complete (RAG live in production)", text)
    assert quote_in_sources("ask-barry/README.md", text)


def test_light_rewording_by_judge_passes_but_new_content_does_not():
    from scripts.evaluate_answers import quote_in_sources
    src = ('E["🚀 Render<br/>auto-deploys<br/>Docker container"] ... - Azure OpenAI (`gpt-4.1-mini`) writes a short '
           'answer that must cite the retrieved sections.\n- The code refuses any answer without a valid citation.')
    assert quote_in_sources("Render auto-deploys the Docker container", src)              # one added word
    assert quote_in_sources("The code refuses any answer without a valid citation", src)
    assert quote_in_sources("Azure OpenAI gpt-4.1-mini writes a short answer that must cite", src)
    assert not quote_in_sources("Render auto-deploys Kubernetes pods to AWS", src)        # new content words
    assert not quote_in_sources("The code accepts any answer with a citation", src)       # meaning changed
    assert not quote_in_sources("Render deploys", src)                                    # too short to fuzzy-match


def test_joined_passages_must_each_be_found():
    from scripts.evaluate_answers import quote_in_sources
    src = ('D -- fail --> F["🛑 Deploy blocked<br/>live site untouched"]\n E --> G["🌐 Live"]\n'
           '1. Describe the change to an agent.\n2. Review it.\n'
           '**Result:** a reviewed, tested change goes from idea to live in about two minutes.')
    # two real passages joined by a line break (and an emoji the judge mangled)
    assert quote_in_sources('D -- fail --> F["6d1 Deploy blocked<br/>live site untouched"]\n\n'
                            '**Result:** a reviewed, tested change goes from idea to live in about two minutes', src)
    # one real passage joined to an invented one fails
    assert not quote_in_sources("Deploy blocked, live site untouched ... rolled back automatically by Kubernetes", src)


def test_true_but_uncited_is_a_labelled_failure():
    from scripts.evaluate_answers import UNCITED, faithfulness
    cited = "[1] Brief > Features\nTime capsules: seal an entry for 1, 5 or 10 years"
    other = "[other 1] Brief > Private by default\nExport your full history as a text file at any time"
    verdict = {"claims": [{"claim": "time capsules", "support": "seal an entry for 1, 5 or 10 years"},
                          {"claim": "can export history", "support": "Export your full history as a text file"},
                          {"claim": "has an iOS app", "support": "native iOS app in the App Store"}]}
    ok, unsupported = faithfulness(verdict, cited, other)
    assert not ok and len(unsupported) == 2
    assert UNCITED in unsupported[0] and "not found in sources" in unsupported[1]


def test_score_counts_uncited_answers():
    a = answer("Barry used Terraform and GitHub Actions [1].")
    a.uncited_texts = ["BBSISK/README.md (section: Toolbox)\nGitHub Actions · Render · Cloudflare"]
    verdict = {"claims": [{"claim": "Terraform", "support": "Docker · Terraform"},
                          {"claim": "GitHub Actions", "support": "GitHub Actions · Render · Cloudflare"}]}
    row = score_question(CLOUD_Q, a, judge_says(**verdict))
    assert not row["passed"] and row["uncited"] == 1
    assert summarise([row])["answers_with_uncited"] == 1

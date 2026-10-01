"""Stage 9a: building the claim set, labelling it, and measuring two judges against the labels (offline)."""
import json
from types import SimpleNamespace

import pytest

from app.judges import CONTEXT, JevJudge, LLMJudge, split_claims
from scripts.evaluate_judges import band, kappa, labelled, metrics, render, run_judges, summarise, sweep
from scripts.label_claims import label_loop


def test_answers_split_into_claims_without_citation_markers():
    text = "Barry built Wall Inspector [1]. It runs in Docker [2]. Short. Ask Barry is live on Azure OpenAI [3]!"
    assert split_claims(text) == ["Barry built Wall Inspector.", "Ask Barry is live on Azure OpenAI!"]


def test_metrics_count_false_support_as_the_key_error():
    truth = [True, True, False, False]
    m = metrics(truth, [True, None, True, False])            # None (a failed judge call) counts as wrong
    assert m["accuracy"] == 0.5 and m["false_support"] == 1 and m["missed_support"] == 1


def test_kappa_is_zero_for_chance_and_one_for_perfect():
    assert kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert abs(kappa([True, True, False, False], [True, False, True, False])) < 1e-9


def test_threshold_sweep_and_uncertain_band():
    truth, probs = [True, True, False, False], [0.9, 0.55, 0.6, 0.1]
    at = {r["threshold"]: r for r in sweep(truth, probs)}
    assert at[0.5]["false_support"] == 1 and at[0.7]["false_support"] == 0 and at[0.7]["missed_support"] == 1
    b = band(truth, probs)
    assert b["to_human"] == 2 and b["accuracy"] == 1.0 and b["false_support"] == 0


class FakeJudge:
    def __init__(self, answers, fail_on=()):
        self.answers, self.fail_on = answers, fail_on

    def judge(self, claim, sources):
        if claim in self.fail_on:
            raise RuntimeError("HTTP 500")
        p = self.answers[claim]
        return {"supported": p >= 0.5, "p": p, "seconds": 0.1, "input_tokens": 400}


ITEMS = [{"id": "c01", "claim": "A", "sources": "s", "label": "supported", "origin": "answer"},
         {"id": "c02", "claim": "B", "sources": "s", "label": "not_supported", "origin": "near-miss"},
         {"id": "c03", "claim": "C", "sources": "s", "label": "unsure", "origin": "answer"}]


def test_end_to_end_report_with_a_failed_call():
    items = labelled(ITEMS)
    assert [i["id"] for i in items] == ["c01", "c02"]                      # unsure left out
    rows = run_judges(items, {"llm": FakeJudge({"A": 1.0, "B": 1.0}), "jev": FakeJudge({"A": 0.8}, fail_on={"B"})},
                      log=lambda *_: None)
    s = summarise(rows)
    assert s["llm"]["false_support"] == 1 and s["jev"]["errors"] == 1 and s["jev"]["false_support"] == 1
    md = render(s, rows, when="2026-10-01")
    assert "**False support**" in md and "## Jev threshold" in md and "c02: B" in md


def test_jev_judge_sends_labelled_sources_and_context():
    sent = {}

    class Client:
        usage = {"input_tokens": 300}

        def ask(self, state, questions):
            sent.update(state=state, questions=questions)
            return {"supported": {"type": "noul", "noul": 0.82}}
    r = JevJudge(Client()).judge("Barry used Docker.", "[1] wall_inspector/README.md (section: Docker)\n...")
    assert r["p"] == 0.82 and r["supported"] is True and r["input_tokens"] == 300
    assert sent["state"]["context"] == CONTEXT and "wall_inspector/README.md" in sent["state"]["sources"]
    assert sent["questions"]["supported"]["type"] == "noul"


def test_llm_judge_parses_json_and_flags_garbage():
    provider = SimpleNamespace(generate=lambda messages, max_tokens: '{"supported": false}',
                               usage=SimpleNamespace(input_tokens=500))
    assert LLMJudge(provider).judge("x", "y")["supported"] is False
    provider.generate = lambda messages, max_tokens: "not json"
    assert LLMJudge(provider).judge("x", "y")["supported"] is None


def test_labelling_saves_each_answer_supports_back_and_quit():
    items = [{"id": f"c{i}", "question": "q", "claim": f"claim {i}", "sources": "[1] r/p (section: s)\ntext",
              "label": None} for i in range(3)]
    keys = iter(["y", "n", "b", "u", "q"])
    saves = []
    label_loop(items, save=lambda: saves.append(1), ask=lambda _: next(keys), out=lambda *_: None)
    assert [it["label"] for it in items] == ["supported", "unsure", None] and len(saves) == 3


def test_build_mixes_real_and_near_miss_claims_and_hides_nothing_needed(monkeypatch):
    from scripts import build_judge_set as b
    answer = SimpleNamespace(supported=True, answer="Barry built Wall Inspector with Flask. It uses PostgreSQL 15 in production.",
                             sources=[SimpleNamespace(number=1, repo="wall_inspector", path="README.md", heading="Stack")],
                             cited_texts=["Flask, PostgreSQL 15"])
    answerer = SimpleNamespace(ask=lambda q: answer)
    provider = SimpleNamespace(generate=lambda messages, max_tokens: json.dumps({"claim": "It uses MySQL 8 in production."}))
    qs = [{"id": f"q{i}", "question": f"Q{i}?"} for i in range(3)]
    items = b.build(qs, answerer, provider, n_real=3, n_near=2, log=lambda *_: None)
    origins = [i["origin"] for i in items]
    assert origins.count("answer") == 3 and origins.count("near-miss") == 2
    assert all(i["label"] is None and "wall_inspector/README.md" in i["sources"] for i in items)
    assert sorted(i["id"] for i in items) == ["c01", "c02", "c03", "c04", "c05"]


def test_second_pass_keeps_first_labels_and_reports_self_agreement():
    from scripts.evaluate_judges import self_agreement
    from scripts.label_claims import start_second_pass
    items = [{"label": "supported"}, {"label": "supported"}, {"label": "not_supported"}, {"label": "unsure"}]
    start_second_pass(items)
    assert [i["label"] for i in items] == [None] * 4 and items[0]["label_pass1"] == "supported"
    for it, lab in zip(items, ["supported", "not_supported", "not_supported", "supported"]):
        it["label"] = lab
    a = self_agreement(items)
    assert a["n"] == 3 and a["same"] == 2 and a["changed"] == 1
    md = render({**summarise(run_judges(labelled(ITEMS), {"llm": FakeJudge({"A": 1.0, "B": 0.0}),
                                                          "jev": FakeJudge({"A": 0.9, "B": 0.1})},
                                        log=lambda *_: None)), "self_agreement": a}, [])
    assert "Human self-agreement" in md and "2 of 3" in md


def test_labelling_shows_the_full_source_text():
    from scripts.label_claims import show
    long_source = "[1] r/README.md (section: s)\n" + "word " * 400 + "NEEDLE at the end"
    lines = []
    show({"question": "q", "claim": "c", "sources": long_source}, 1, 1, out=lines.append)
    assert "NEEDLE" in "\n".join(lines)                        # Stage 9a bug: text after 900 chars was hidden


def test_review_picks_disputed_claims_plus_a_random_sample_and_scores_the_passes():
    from scripts.evaluate_judges import human_passes
    from scripts.label_claims import review_ids, review_loop
    items = [{"id": f"c{i}", "label": "supported", "label_pass1": "supported", "question": "q", "claim": "x",
              "sources": "[1] r/p (section: s)\nt"} for i in range(20)]
    items[0]["label_pass1"] = "not_supported"                                  # passes differ
    results = [{"id": f"c{i}", "llm": {"supported": i != 1}, "jev": {"supported": i != 1}} for i in range(20)]
    ids = review_ids(items, results, sample=3)                                  # c1: both judges disagree
    assert ids[:2] == ["c0", "c1"] and len(ids) == 5
    keys = iter(["n", "reason", "n", "", "y", "", "y", "", "y", ""])
    review_loop(items, ids, save=lambda: None, ask=lambda _: next(keys), out=lambda *_: None)
    assert items[0]["label_final"] == "not_supported" and items[0]["review_reason"] == "reason"
    h = human_passes(items)
    assert h["reviewed"] == 5 and h["passes"]["pass 2"]["false_support"] == 2


def test_adjudication_reports_both_views_and_keeps_blind_labels():
    from scripts.evaluate_judges import apply_adjudication, report
    items = [dict(it, label_pass1=it["label"]) for it in ITEMS]
    items[1]["label_final"] = "supported"                                  # a blind review got c02 wrong
    rows = [{"id": "c01", "label": "?", "origin": "answer", "claim": "A",
             "llm": {"supported": True, "p": 1.0, "seconds": 0.1, "input_tokens": 400},
             "jev": {"supported": True, "p": 0.9, "seconds": 0.1, "input_tokens": 300}},
            {"id": "c02", "label": "?", "origin": "near-miss", "claim": "B",
             "llm": {"supported": False, "p": 0.0, "seconds": 0.1, "input_tokens": 400},
             "jev": {"supported": False, "p": 0.1, "seconds": 0.1, "input_tokens": 300}}]
    adj = {"date": "2026-10-01", "by": "Barry", "items": [{"id": "c02", "label": "not_supported", "reason": "source says X"}]}
    fixed = apply_adjudication(items, adj)
    assert fixed[1]["label_final"] == "not_supported" and fixed[1]["label_blind"] == "supported"
    assert items[1]["label_final"] == "supported"                          # the original is untouched
    md = report(rows, items, adj, when="2026-10-01")
    assert "| Jev (threshold 0.5) | blind | 50% |" in md and "| Jev (threshold 0.5) | adjudicated | 100% |" in md
    assert "source says X" in md and "| supported | not_supported |" in md
    assert "Two judges vs human labels" in report(rows, items, None)        # no adjudication: the old report

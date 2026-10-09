"""ASK-42: capability ladder and evidence cards. Offline: a fake retriever and a fake model stand in for Azure."""
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from app import create_app
from app.capability import view
from app.capability.builder import (StoryWriter, TierJudge, build_capability, find_sections, same_content,
                                    story_id)
from app.capability.pack import DEFAULT_PACK, PackError, load_pack
from app.capability.store import CapabilityStore, problems
from app.retrieval import SearchResult

ROOT = Path(__file__).resolve().parents[1]
NURSE = ROOT / "tests" / "fixtures" / "profiles" / "nurse"
NOW = datetime(2026, 10, 9, 3, 30, tzinfo=timezone.utc)


def chunk(cid, repo, heading, text, path="README.md"):
    return {"chunk_id": cid, "repo": repo, "path": path, "heading": heading, "text": text,
            "url": f"https://github.com/BBSISK/{repo}/blob/abc123/{path}#{cid}"}


CHUNKS = [
    chunk("wi-docker", "wall_inspector", "Deployment",
          "Render auto-deploys the Docker container after GitHub Actions runs 63 tests."),
    chunk("wi-compose", "wall_inspector", "Quick start", "Run the whole stack locally with docker-compose up."),
    chunk("ab-k8s-plan", "ask-barry", "Notes", "Ideas for later: maybe try Kubernetes one day."),
    chunk("profile-toolbox", "BBSISK", "Toolbox", "Cloud and DevOps: Docker, Terraform, Kubernetes."),
    chunk("ab-incident", "ask-barry", "Readiness bug",
          "The readiness check waited 8 seconds for a hung provider. I fixed the thread pool shutdown and "
          "added a regression test, so it now returns within 3 seconds."),
    chunk("wi-fixture", "wall_inspector", "Testing", "63 tests run in CI on every push."),
]


class FakeRetriever:
    """Returns chunks whose text shares a word with the query, in corpus order."""

    def __init__(self, chunks=CHUNKS):
        self.chunks, self.calls = chunks, []

    def search(self, query, k=5):
        self.calls.append(query)
        words = {w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 3}
        hits = [c for c in self.chunks if words & set(re.findall(r"[a-z]+", c["text"].lower()))]
        return [SearchResult(c, 1.0, n) for n, c in enumerate(hits[:k], start=1)]


class FakeProvider:
    """A model in JSON mode. tiers maps (skill name, heading) -> (tier, quote); stories maps (card, heading)."""

    def __init__(self, tiers=None, stories=None):
        self.tiers, self.stories, self.calls = tiers or {}, stories or {}, 0

    def generate(self, messages, max_tokens=400):
        self.calls += 1
        user = messages[-1]["content"]
        heading = re.search(r"SECTION \[[^\]]*\((.*?)\)\]", user).group(1)
        if user.startswith("SKILL: "):
            name = user[len("SKILL: "):].split(":")[0]
            tier, quote = self.tiers.get((name, heading), (0, ""))
            return json.dumps({"tier": tier, "quote": quote})
        card = user[len("CARD: "):].split("\n")[0]
        story = self.stories.get((card, heading))
        return json.dumps(story or {"example": False})


DOCKER_TIERS = {
    ("Containers (Docker)", "Deployment"): (3, "Render auto-deploys the Docker container"),
    ("Containers (Docker)", "Quick start"): (2, "Run the whole stack locally with docker-compose up"),
    ("Containers (Docker)", "Toolbox"): (4, "Docker, Terraform"),               # self-description: must not count
    ("Kubernetes", "Notes"): (1, "maybe try Kubernetes one day"),          # planned: the judge should say 0,
}                                                                            # but see test_planned_work...
STORY = {"example": True, "title": "Readiness check hung", "quote": "I fixed the thread pool shutdown",
         "summary": "The readiness check waited 8 seconds; the thread pool shutdown was fixed and a test added."}


def build(pack=None, tiers=DOCKER_TIERS, stories=None, first=None, retriever=None, previous=None, log=None):
    pack = pack or load_pack()
    provider = FakeProvider(tiers, stories)
    return build_capability(pack, retriever or FakeRetriever(), TierJudge(provider, pack),
                            StoryWriter(provider, pack), first_committed=first, now=NOW,
                            log=log or (lambda *_: None), previous=previous)


def skill(cap, sid):
    return next(s for s in cap["skills"] if s["id"] == sid)


# --- the profile pack -----------------------------------------------------------------------------------------

def test_barrys_pack_loads_and_has_four_tiers_and_the_agreed_cards():
    pack = load_pack()
    assert [t["label"] for t in pack.tiers] == ["Used", "Built", "In production", "Tested / evaluated"]
    assert {"kubernetes", "java"} <= {s["id"] for s in pack.skills}          # gaps stay on the list
    assert "data-manipulation" in {c["id"] for c in pack.cards}
    assert pack.is_self_description("BBSISK")


def copy_pack(tmp_path, src=DEFAULT_PACK):
    dst = tmp_path / "pack"
    shutil.copytree(src, dst)
    return dst


def test_pack_errors_name_the_file_and_field(tmp_path):
    pack = copy_pack(tmp_path)
    (pack / "skills.yaml").write_text("skills:\n  - id: Bad Id\n    name: x\n    description: y\n    queries: [z]\n")
    with pytest.raises(PackError, match=r"(?s)skills\.yaml.*skills/0/id"):
        load_pack(pack)


def test_pack_needs_all_four_tiers_and_unique_ids(tmp_path):
    pack = copy_pack(tmp_path)
    tiers = yaml.safe_load((pack / "tiers.yaml").read_text())
    tiers["tiers"][3]["level"] = 3
    (pack / "tiers.yaml").write_text(yaml.safe_dump(tiers))
    with pytest.raises(PackError, match="levels 1, 2, 3 and 4"):
        load_pack(pack)
    pack2 = copy_pack(tmp_path / "b")
    cards = yaml.safe_load((pack2 / "cards.yaml").read_text())
    cards["cards"].append(dict(cards["cards"][0]))
    (pack2 / "cards.yaml").write_text(yaml.safe_dump(cards))
    with pytest.raises(PackError, match="used twice"):
        load_pack(pack2)


def test_missing_file_is_explained(tmp_path):
    pack = copy_pack(tmp_path)
    (pack / "cards.yaml").unlink()
    with pytest.raises(PackError, match="Missing .*cards.yaml"):
        load_pack(pack)


# --- the ladder -----------------------------------------------------------------------------------------------

def test_tier_is_the_highest_verified_tier_and_every_filled_tier_has_a_citation():
    cap, _ = build()
    docker = skill(cap, "containers")
    assert docker["tier"] == 3
    assert [e["tier"] for e in docker["evidence"]] == [3, 2]
    for level in range(1, docker["tier"] + 1):
        assert [e for e in docker["evidence"] if e["tier"] >= level and e["url"].startswith("https://")]
    assert docker["projects_by_tier"]["3"] == ["Wall Inspector"]
    assert not problems(cap)


def test_self_description_never_fills_a_tier():
    cap, _ = build()
    assert all(e["repo"] != "BBSISK" for s in cap["skills"] for e in s["evidence"])


def test_an_invented_quote_counts_for_nothing():
    tiers = {("Containers (Docker)", "Deployment"): (4, "Docker runs on Kubernetes with full load testing")}
    cap, _ = build(tiers=tiers)
    assert skill(cap, "containers")["tier"] == 0


def test_planned_work_depends_on_the_judge_but_the_quote_must_still_be_real():
    # The fake judge wrongly gives the "ideas for later" line tier 1. Its heading doesn't say it's a plan. The quote is real, so it would count: that is why
    # the real judge's rules say plans count as 0, and why the trap skills are in the hand-labelled check.
    cap, _ = build()
    assert skill(cap, "kubernetes")["tier"] == 1
    cap, _ = build(tiers={k: v for k, v in DOCKER_TIERS.items() if k[0] != "Kubernetes"})
    assert skill(cap, "kubernetes")["tier"] == 0


def test_a_section_headed_as_a_plan_never_fills_a_tier_whatever_the_judge_says():
    roadmap = [c if c["chunk_id"] != "ab-k8s-plan" else {**c, "heading": "Architecture (planned)"} for c in CHUNKS]
    tiers = {**DOCKER_TIERS, ("Kubernetes", "Architecture (planned)"): (3, "maybe try Kubernetes one day")}
    cap, _ = build(tiers=tiers, retriever=FakeRetriever(roadmap))
    assert skill(cap, "kubernetes")["tier"] == 0
    pack = load_pack()
    assert pack.is_planned("Roadmap") and pack.is_planned("Housing > Architecture (planned)")
    assert not pack.is_planned("Deployment") and not pack.is_planned("Unplanned outage fix")


def test_a_slow_search_is_retried_and_a_dead_one_still_fails():
    from app.capability.builder import search

    class Flaky:
        def __init__(self, fails):
            self.fails, self.calls = fails, 0

        def search(self, query, k=5):
            self.calls += 1
            if self.calls <= self.fails:
                raise TimeoutError("read timed out")
            return ["ok"]

    flaky = Flaky(2)
    assert search(flaky, "q", 5, sleep=lambda _: None, log=lambda *_: None) == ["ok"] and flaky.calls == 3
    with pytest.raises(TimeoutError):
        search(Flaky(3), "q", 5, sleep=lambda _: None, log=lambda *_: None)


def test_skills_without_evidence_stay_on_the_list_as_not_evidenced():
    cap, _ = build(tiers={})
    assert {s["id"] for s in cap["skills"]} == {s["id"] for s in load_pack().skills}
    assert all(s["tier"] == 0 and s["evidence"] == [] for s in cap["skills"])


def test_first_evidence_is_the_earliest_commit_of_a_supporting_file():
    dates = {("wall_inspector", "README.md"): "2025-11-02"}
    cap, _ = build(first=lambda repo, path: dates.get((repo, path)))
    assert skill(cap, "containers")["first_evidence"] == "2025-11"
    assert skill(cap, "java")["first_evidence"] is None


def test_two_builds_from_the_same_answers_are_identical():
    a, _ = build()
    b, _ = build()
    assert same_content(a, b)


def test_retrieval_merges_queries_without_duplicates():
    sections = find_sections(FakeRetriever(), ["docker container", "docker compose"], k=5, limit=10)
    assert [c["chunk_id"] for c in sections].count("wi-docker") == 1


# --- evidence cards -------------------------------------------------------------------------------------------

def test_cards_show_only_approved_examples_and_suggest_the_rest(tmp_path):
    stories = {("Problem solving & debugging", "Readiness bug"): STORY}
    cap, sugg = build(stories=stories)
    card = next(c for c in cap["cards"] if c["id"] == "problem-solving")
    assert card["gap"] is True and card["stories"] == []                    # nothing approved yet
    cands = next(s for s in sugg["cards"] if s["card"] == "problem-solving")["candidates"]
    assert cands and cands[0]["approved"] is False

    pack = copy_pack(tmp_path)
    cards = yaml.safe_load((pack / "cards.yaml").read_text())
    cards["cards"][0]["approved"] = [cands[0]["id"], "problem-solving:gone"]
    (pack / "cards.yaml").write_text(yaml.safe_dump(cards))
    cap, sugg = build(pack=load_pack(pack), stories=stories)
    card = next(c for c in cap["cards"] if c["id"] == "problem-solving")
    assert card["gap"] is False and card["stories"][0]["title"] == "Readiness check hung"
    assert card["stories"][0]["url"].startswith("https://github.com/")
    assert next(s for s in sugg["cards"] if s["card"] == "problem-solving")["approved_but_not_found"] == \
        ["problem-solving:gone"]


def approve_first_candidate(tmp_path, stories):
    """Build once, approve the first problem-solving candidate, return (pack, approved id, published build)."""
    _, sugg = build(stories=stories)
    sid = next(s for s in sugg["cards"] if s["card"] == "problem-solving")["candidates"][0]["id"]
    folder = copy_pack(tmp_path)
    cards = yaml.safe_load((folder / "cards.yaml").read_text())
    cards["cards"][0]["approved"] = [sid]
    (folder / "cards.yaml").write_text(yaml.safe_dump(cards))
    pack = load_pack(folder)
    published, _ = build(pack=pack, stories=stories)
    return pack, sid, published


def test_an_approved_example_stays_live_when_tonights_draft_misses_it(tmp_path):
    pack, sid, published = approve_first_candidate(tmp_path, {("Problem solving & debugging", "Readiness bug"): STORY})
    cap, sugg = build(pack=pack, stories={}, previous=published)            # the writer finds nothing tonight
    card = next(c for c in cap["cards"] if c["id"] == "problem-solving")
    assert [st["id"] for st in card["stories"]] == [sid] and card["gap"] is False
    assert next(s for s in sugg["cards"] if s["card"] == "problem-solving")["approved_but_not_found"] == []


def test_an_approved_example_keeps_its_approved_wording(tmp_path):
    pack, sid, published = approve_first_candidate(tmp_path, {("Problem solving & debugging", "Readiness bug"): STORY})
    redrafted = {("Problem solving & debugging", "Readiness bug"): {**STORY, "title": "A different title"}}
    cap, _ = build(pack=pack, stories=redrafted, previous=published)
    story = next(c for c in cap["cards"] if c["id"] == "problem-solving")["stories"][0]
    assert story["title"] == "Readiness check hung"


def test_an_approved_example_is_dropped_when_its_source_changes(tmp_path):
    pack, sid, published = approve_first_candidate(tmp_path, {("Problem solving & debugging", "Readiness bug"): STORY})
    edited = [c if c["chunk_id"] != "ab-incident" else {**c, "text": "The readiness bug was fixed in October."}
              for c in CHUNKS]
    lines = []
    cap, sugg = build(pack=pack, stories={}, previous=published, retriever=FakeRetriever(edited), log=lines.append)
    card = next(c for c in cap["cards"] if c["id"] == "problem-solving")
    assert card["gap"] is True and card["stories"] == []
    assert next(s for s in sugg["cards"] if s["card"] == "problem-solving")["approved_but_not_found"] == [sid]
    assert any("no longer matches its source" in line for line in lines)


def test_a_card_example_with_an_invented_quote_is_dropped():
    stories = {("Problem solving & debugging", "Readiness bug"): {**STORY, "quote": "I rewrote the whole service"}}
    _, sugg = build(stories=stories)
    assert next(s for s in sugg["cards"] if s["card"] == "problem-solving")["candidates"] == []


def test_gap_cards_carry_their_note_and_data_manipulation_starts_as_a_gap():
    cap, _ = build()
    data = next(c for c in cap["cards"] if c["id"] == "data-manipulation")
    assert data["gap"] and "Not yet evidenced" in data["gap_note"]


def test_adding_a_card_needs_no_code_change(tmp_path):
    pack = copy_pack(tmp_path)
    cards = yaml.safe_load((pack / "cards.yaml").read_text())
    cards["cards"].append({"id": "public-speaking", "title": "Public speaking", "queries": ["talk"],
                           "approved": [], "gap_note": "Coming soon."})
    (pack / "cards.yaml").write_text(yaml.safe_dump(cards))
    cap, _ = build(pack=load_pack(pack))
    assert cap["cards"][-1]["title"] == "Public speaking" and not problems(cap)


def test_story_ids_are_stable():
    assert story_id("x", CHUNKS[0]) == story_id("x", dict(CHUNKS[0]))


# --- the page, the API and the store ---------------------------------------------------------------------------

def app_with(cap, **kw):
    store = CapabilityStore(source="unused", fetch=lambda _src: cap)
    return create_app("testing", capability_store=store, **kw).test_client()


def test_page_says_not_generated_yet_without_a_file():
    html = app_with(None).get("/capability").get_data(as_text=True)
    assert "hasn't been generated yet" in html


def test_page_shows_tiers_evidence_buttons_and_gaps():
    cap, _ = build()
    html = app_with(cap).get("/capability").get_data(as_text=True)
    assert "Used · Built · In production · Tested / evaluated" in html
    assert 'aria-label="Containers (Docker): In production, evidenced. Show the evidence"' in html
    assert html.count("✕ Not evidenced") >= 3                               # Java, front end, streaming...
    assert html.index("Containers (Docker)") < html.index("Java")           # deepest first
    assert "Data manipulation" in html and "Evidence as of 2026-10-09" in html


def test_api_returns_the_same_json_and_one_skill():
    cap, _ = build()
    client = app_with(cap)
    assert client.get("/api/capability").get_json() == cap
    one = client.get("/api/capability?skill=Containers (Docker)").get_json()
    assert [s["id"] for s in one["skills"]] == ["containers"] and one["cards"] == []
    assert client.get("/api/capability?skill=juggling").status_code == 404
    assert app_with(None).get("/api/capability").status_code == 503


def test_job_view_puts_the_ads_skills_first_with_a_fit_summary_and_unmatched_items():
    cap, _ = build()
    report = {"role_title": "Platform Engineer", "requirements": [
        {"requirement": "Docker and containers"}, {"requirement": "Kubernetes"}, {"requirement": "Excellent Excel"}]}

    class OneJob:
        def get(self, job_id):
            return type("Job", (), {"status": "done", "report": report})() if job_id == "job1" else None
    html = app_with(cap, jobstore=OneJob()).get("/capability?job=job1").get_data(as_text=True)
    assert "Matched to <strong>Platform Engineer</strong>" in html
    assert html.index("Kubernetes") < html.index("Python &amp; Flask")      # the ad's skills first
    assert "Not on this profile's skill list: Excellent Excel" in html
    assert "<strong>1 of 2</strong> matched skills at “In production” or above" in html


def test_store_keeps_the_last_good_copy_when_the_file_breaks():
    cap, _ = build()
    answers = [cap, {"broken": True}, OSError("down")]
    clock = [0]
    store = CapabilityStore(source="x", ttl=10, fetch=lambda _s: (lambda a: (_ for _ in ()).throw(a)
                            if isinstance(a, Exception) else a)(answers.pop(0)), clock=lambda: clock[0])
    assert store.get() == cap
    clock[0] = 11
    assert store.get() == cap                                                # invalid -> last good
    clock[0] = 22
    assert store.get() == cap                                                # error -> last good


def test_match_job_uses_whole_words():
    cap, _ = build()
    assert view.matching_skills(cap, "Java and Spring Boot") == ["java"]
    assert view.matching_skills(cap, "JavaScript") == []                     # not Java


# --- the swap test: another person, another profession, no code change ----------------------------------------

def test_a_different_profession_builds_and_renders_with_no_code_change():
    nurse = load_pack(NURSE)
    retriever = FakeRetriever([chunk("w1", "ward-audit", "Wound audit",
                                     "Aoife led the ward wound care audit and mentors new nurses in dressing technique.")])
    tiers = {("Wound care", "Wound audit"): (4, "mentors new nurses in dressing technique")}
    cap, _ = build(pack=nurse, tiers=tiers, retriever=retriever)
    assert not problems(cap)
    assert skill(cap, "wound-care")["tier"] == 4
    assert skill(cap, "wound-care")["projects_by_tier"]["4"] == ["Ward audit project"]
    html = app_with(cap).get("/capability").get_data(as_text=True)
    assert "Supervised practice" in html and "Audited or mentoring" in html and "Aoife" in html
    body = html.split("<main>")[1]
    assert "Barry" not in body.replace("Ask Barry", "")                     # nothing about Barry hard-coded
    assert "production" not in body.lower()                                 # nor about software


# --- the evaluator ---------------------------------------------------------------------------------------------

def test_evaluator_scores_against_labels_and_fails_on_a_claimed_trap():
    from scripts.evaluate_capability import compare, passed, score
    cap, _ = build()
    labels = {"skills": {"containers": 3, "kubernetes": 0, "java": 0}, "traps": ["kubernetes"]}
    result = score(cap, labels)
    assert result["exact"] == pytest.approx(2 / 3) and result["trap_failures"] == ["kubernetes"]
    assert not passed(result)
    clean, _ = build(tiers={k: v for k, v in DOCKER_TIERS.items() if k[0] != "Kubernetes"})
    assert passed(score(clean, labels)) and compare(clean, clean) == []
    assert compare(cap, clean) == [{"skill": "kubernetes", "first": 1, "second": 0}]


def test_report_shows_instability_and_fails():
    from scripts.evaluate_capability import compare, render, score
    cap, _ = build()
    clean, _ = build(tiers={k: v for k, v in DOCKER_TIERS.items() if k[0] != "Kubernetes"})
    labels = {"skills": {"containers": 3}, "traps": []}
    unstable = render(score(cap, labels), cap, labels, diffs=compare(cap, clean))
    assert "Stable across two builds: **no** (kubernetes 1 vs 0)" in unstable and "**FAIL**" in unstable
    stable = render(score(cap, labels), cap, labels, diffs=[])
    assert "Stable across two builds: **yes**" in stable and "**PASS**" in stable


# --- voting: one borderline answer can't move a tier ------------------------------------------------------------

class ScriptedJudge:
    """Gives the answers in order, one per call."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def judge(self, skill, chunk):
        self.calls += 1
        return self.answers.pop(0)


SECTION = {"repo": "ask-barry", "path": "README.md", "heading": "Deploy", "text": "Deployed on Render with Flask."}
SKILL = {"id": "python-flask", "name": "Python & Flask"}


def test_two_matching_answers_settle_it_without_a_third_call():
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 3, "quote": "Deployed on Render"}, {"tier": 3, "quote": "Deployed on Render"})
    assert vote(SKILL, SECTION, judge, log=lambda *_: None)["tier"] == 3 and judge.calls == 2


def test_the_middle_answer_wins_when_answers_differ():
    from app.capability.builder import vote
    lines = []
    up = ScriptedJudge({"tier": 3, "quote": "Deployed on Render"}, {"tier": 1, "quote": "Render with Flask"},
                       {"tier": 4, "quote": "Deployed on Render"})
    assert vote(SKILL, SECTION, up, log=lines.append)["tier"] == 3 and up.calls == 3
    assert "answers 3, 1, 4 -> 3" in lines[0]
    down = ScriptedJudge({"tier": 3, "quote": "Deployed on Render"}, {"tier": 0, "quote": ""}, {"tier": 0, "quote": ""})
    assert vote(SKILL, SECTION, down, log=lambda *_: None)["tier"] == 0


def test_an_answer_with_an_invented_quote_counts_as_zero():
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 4, "quote": "evaluated with 500 tests"}, {"tier": 2, "quote": "Flask"},
                          {"tier": 4, "quote": "evaluated with 500 tests"})
    lines = []
    assert vote(SKILL, SECTION, judge, log=lines.append)["tier"] == 0
    assert "quote not found for 4" in lines[0]


def test_one_vote_is_the_old_behaviour():
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 2, "quote": "Render with Flask"})
    assert vote(SKILL, SECTION, judge, votes=1, log=lambda *_: None)["tier"] == 2 and judge.calls == 1


def test_draft_labels_cover_every_skill_on_barrys_list():
    labels = json.loads((ROOT / "eval" / "capability_labels.json").read_text())
    assert set(labels["skills"]) == {s["id"] for s in load_pack().skills}
    assert set(labels["traps"]) <= {k for k, v in labels["skills"].items() if v == 0}

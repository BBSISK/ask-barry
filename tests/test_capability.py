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

def test_barrys_pack_loads_and_has_five_tiers_and_the_agreed_cards():
    pack = load_pack()
    assert [t["label"] for t in pack.tiers] == ["Used", "Built", "In production", "Tested / evaluated", "Proven over time"]
    assert pack.top_judged == 4 and pack.computed_tier["level"] == 5          # ASK-57: tier 5 is never judged
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


def test_pack_needs_consecutive_tiers_and_unique_ids(tmp_path):
    pack = copy_pack(tmp_path)
    tiers = yaml.safe_load((pack / "tiers.yaml").read_text())
    tiers["tiers"][3]["level"] = 3
    (pack / "tiers.yaml").write_text(yaml.safe_dump(tiers))
    with pytest.raises(PackError, match="no gaps"):
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
    assert "Used, Built, In production, Tested / evaluated, Proven over time" in html     # screen-reader header
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
    assert vote(SKILL, SECTION, judge, log=lines.append, requotes=0)["tier"] == 0
    assert "quote not found for 4" in lines[0]


def test_a_misquote_is_asked_again_and_a_good_quote_keeps_the_tier():
    """ASK-60: a copying slip used to count as a 0 vote and could pull a tier down overnight."""
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 3, "quote": "Deployed to production on Render"},   # not the section's words
                          {"tier": 3, "quote": "Deployed on Render"},
                          {"tier": 3, "quote": "Deployed on Render with Flask"})
    lines = []
    assert vote(SKILL, SECTION, judge, log=lines.append)["tier"] == 3 and judge.calls == 3
    assert "1 misquoted, asked again" in lines[0]
    assert 'quote not in section (tier 3): "Deployed to production on Render"' in lines[1]


def test_a_judge_that_keeps_inventing_quotes_still_gets_nothing():
    from app.capability.builder import vote
    invented = {"tier": 4, "quote": "evaluated with 500 automated tests"}
    judge = ScriptedJudge(*[dict(invented) for _ in range(6)])
    lines = []
    result = vote(SKILL, SECTION, judge, log=lines.append, requotes=2)
    assert result["tier"] == 0 and result["quote"] == "" and judge.calls == 6     # 2 votes x 3 tries, then majority
    assert "answers 0 (quote not found for 4), 0 (quote not found for 4)" in lines[0]


def test_a_genuine_zero_is_never_asked_again():
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 0, "quote": ""}, {"tier": 0, "quote": ""})
    assert vote(SKILL, SECTION, judge, log=lambda *_: None)["tier"] == 0 and judge.calls == 2


def test_one_vote_is_the_old_behaviour():
    from app.capability.builder import vote
    judge = ScriptedJudge({"tier": 2, "quote": "Render with Flask"})
    assert vote(SKILL, SECTION, judge, votes=1, log=lambda *_: None)["tier"] == 2 and judge.calls == 1


def test_draft_labels_cover_every_skill_on_barrys_list():
    labels = json.loads((ROOT / "eval" / "capability_labels.json").read_text())
    assert set(labels["skills"]) == {s["id"] for s in load_pack().skills}
    assert set(labels["traps"]) <= {k for k, v in labels["skills"].items() if v == 0}


# --- ASK-50: gap-closing plans -----------------------------------------------------------------------------------

def plan_pack(tmp_path, plans):
    folder = copy_pack(tmp_path)
    (folder / "plans.yaml").write_text(yaml.safe_dump({"plans": plans}))
    return folder


JAVA_PLAN = {"id": "java-repo", "skill": "java", "target_tier": 2, "work": "Own Java repo", "planned": "2026-10",
             "target": "2026-12"}
DOCKER_PLAN = {"id": "docker-prod", "skill": "containers", "target_tier": 3, "work": "Container in production",
               "planned": "2026-10", "target": "2026-11"}
CARD_PLAN = {"id": "card-ps", "card": "problem-solving", "work": "Approve an example", "planned": "2026-09",
             "target": "2026-09"}


def test_barrys_plans_load_and_point_at_real_skills_and_cards():
    pack = load_pack()
    assert pack.plans and {p["skill"] for p in pack.plans if "skill" in p} <= {s["id"] for s in pack.skills}
    assert {p["card"] for p in pack.plans if "card" in p} <= {c["id"] for c in pack.cards}


def test_a_pack_without_plans_still_loads():
    assert load_pack(NURSE).plans == []


@pytest.mark.parametrize("bad, message", [
    ({**JAVA_PLAN, "skill": "juggling"}, "isn't in skills.yaml"),
    ({**JAVA_PLAN, "target": "2026-09"}, "before the month it was planned"),
    ({**CARD_PLAN, "target_tier": 2}, "plans format"),             # a card has no tier
    ({**JAVA_PLAN, "target": "Dec 2026"}, "plans format"),
])
def test_bad_plans_are_refused_with_the_file_named(tmp_path, bad, message):
    with pytest.raises(PackError, match=message) as err:
        load_pack(plan_pack(tmp_path, [bad]))
    assert "plans.yaml" in str(err.value)


def test_plans_are_open_closed_or_overdue_and_never_fill_a_tier(tmp_path):
    pack = load_pack(plan_pack(tmp_path, [JAVA_PLAN, DOCKER_PLAN, CARD_PLAN]))
    cap, _ = build(pack=pack)                                 # NOW = 9 Oct 2026; Containers reaches 3, Java 0
    assert problems(cap) == []
    status = {p["id"]: p for p in cap["plans"]}
    assert status["java-repo"]["status"] == "open" and skill(cap, "java")["tier"] == 0
    assert status["docker-prod"] == {**status["docker-prod"], "status": "closed", "closed": "2026-10", "on_time": True}
    assert status["card-ps"]["status"] == "overdue"            # no approved example, target month has passed
    assert cap["plan_record"] == {"total": 3, "closed": 1, "on_time": 1, "open": 1, "overdue": 1}
    assert [p["id"] for p in cap["plans"]] == ["card-ps", "docker-prod", "java-repo"]   # by target month


def test_the_month_a_plan_closed_is_kept_across_rebuilds(tmp_path):
    from app.capability.plans import plan_statuses
    pack = load_pack(plan_pack(tmp_path, [DOCKER_PLAN]))
    first, _ = build(pack=pack)
    skills, cards = first["skills"], first["cards"]
    later = datetime(2027, 2, 1, tzinfo=timezone.utc)
    kept, _ = plan_statuses(pack, skills, cards, previous=first, now=later)
    assert kept[0]["closed"] == "2026-10" and kept[0]["on_time"] is True
    fresh, _ = plan_statuses(pack, skills, cards, previous=None, now=later)
    assert fresh[0]["closed"] == "2027-02" and fresh[0]["on_time"] is False        # late if first seen in Feb


def test_a_closed_plan_reopens_if_the_evidence_goes_away(tmp_path):
    from app.capability.plans import plan_statuses
    pack = load_pack(plan_pack(tmp_path, [DOCKER_PLAN]))
    first, _ = build(pack=pack)
    gone = [{**s, "tier": 0} if s["id"] == "containers" else s for s in first["skills"]]
    plans, record = plan_statuses(pack, gone, first["cards"], previous=first, now=NOW)
    assert plans[0]["status"] == "open" and "closed" not in plans[0] and record["closed"] == 0


def test_no_plans_means_no_plan_fields(tmp_path):
    cap, _ = build()
    assert "plans" in cap                                     # Barry's own pack has plans
    cap, _ = build(pack=load_pack(NURSE))
    assert "plans" not in cap and "plan_record" not in cap


def test_page_shows_the_plan_beside_its_gap_and_the_track_record(tmp_path):
    pack = load_pack(plan_pack(tmp_path, [JAVA_PLAN, DOCKER_PLAN, CARD_PLAN]))
    cap, _ = build(pack=pack)
    html = app_with(cap).get("/capability").get_data(as_text=True)
    assert "Gap-closing plan:</strong> 1 of 3 closed (1 on time)" in html and "1 overdue" in html
    java_row = html.split('data-skill="java"', 1)[1].split("</tr>", 2)[1]
    assert "Working on it:</b> Own Java repo · target Built by Dec 2026" in java_row
    assert "Overdue:</b> Approve an example" in html                         # on the card
    table = html.split('id="plans"', 1)[1].split("</section>", 1)[0]
    assert "Closed Oct 2026" in table and "Overdue" in table and "Open" in table


def test_api_keeps_a_skills_plans_and_mcp_reports_them(tmp_path):
    import ask_barry_mcp as server
    pack = load_pack(plan_pack(tmp_path, [JAVA_PLAN, DOCKER_PLAN]))
    cap, _ = build(pack=pack)
    one = app_with(cap).get("/api/capability?skill=java").get_json()
    assert [p["id"] for p in one["plans"]] == ["java-repo"]
    result = server.to_capability_result(cap)
    assert {(p.gap, p.status) for p in result.plans} == {("Java", "open"), ("Containers (Docker)", "closed")}
    assert result.plan_record.startswith("1 of 2 closed (1 on time)")
    assert {p.gap for p in server.to_capability_result(one).plans} == {"Java"}


# --- ASK-52: change control ---------------------------------------------------------------------------------------

def test_change_control_is_its_own_skill_and_not_matched_on_change_management():
    cap, _ = build()
    assert skill(cap, "change-control")["name"] == "Change control"
    assert view.matching_skills(cap, "Experience with Git, pull requests and Jira") == ["change-control"]
    assert "change-control" not in view.matching_skills(cap, "Leads organisational change management")
    assert "change-control" in view.matching_skills(cap, "Release management and change control")


# --- ASK-56: long cards scroll inside the card ------------------------------------------------------------------

def test_cards_with_more_than_two_examples_scroll_and_say_how_many_more():
    cap, _ = build()
    card = next(c for c in cap["cards"] if c["id"] == "problem-solving")
    story = {"id": "x", "title": "T", "summary": "S", "repo": "r", "path": "p", "heading": "h",
             "url": "https://github.com/BBSISK/r/blob/a/p", "quote": "q", "project": "P",
             "source_type": "github_readme", "verified_by": "self"}
    card.update(gap=False, stories=[{**story, "id": f"problem-solving:{i}"} for i in range(4)])
    card.pop("gap_note", None)
    two = next(c for c in cap["cards"] if c["id"] == "security-mindset")
    two.update(gap=False, stories=[{**story, "id": f"security-mindset:{i}"} for i in range(2)])
    two.pop("gap_note", None)
    html = app_with(cap).get("/capability").get_data(as_text=True)
    long_card = html.split("Problem solving", 1)[1].split("</article>", 1)[0]
    assert 'class="stories scrolls" tabindex="0" role="region"' in long_card and "Scroll for 2 more" in long_card
    short_card = html.split("Security mindset", 1)[1].split("</article>", 1)[0]
    assert 'class="stories"' in short_card and "scrolls" not in short_card and "Scroll for" not in short_card
# --- ASK-57: project kinds cap evidence; the top tier is computed, never judged ------------------------------------

def kinds_pack(tmp_path, **projects):
    folder = copy_pack(tmp_path)
    profile = yaml.safe_load((folder / "profile.yaml").read_text())
    profile["projects"].update(projects)
    (folder / "profile.yaml").write_text(yaml.safe_dump(profile))
    return load_pack(folder)


def test_practice_and_coursework_stop_at_built(tmp_path):
    lines = []
    pack = kinds_pack(tmp_path, wall_inspector={"name": "Wall Inspector", "kind": "practice"})
    cap, _ = build(pack=pack, log=lines.append)
    containers = skill(cap, "containers")
    assert containers["tier"] == 2 and all(e["tier"] <= 2 and e["kind"] == "practice" for e in containers["evidence"])
    assert any("capped at tier 2 (practice)" in line for line in lines)
    cap, _ = build(pack=kinds_pack(tmp_path / "b", wall_inspector={"name": "WI", "kind": "application"}))
    assert skill(cap, "containers")["tier"] == 3


def test_an_unlisted_repo_is_treated_as_practice():
    pack = load_pack()
    assert pack.project_kind("some-new-repo") == "practice" and pack.max_tier("some-new-repo") == 2
    assert pack.project_kind("CS627_Advanced_OOP_Java") == "coursework" and pack.max_tier("leetcode-java") == 2
    assert pack.max_tier("ask-barry") == 4 and pack.project_name("ask-barry") == "Ask Barry"


def test_the_judge_never_awards_the_computed_tier():
    pack = load_pack()
    judge = TierJudge(FakeProvider({("Containers (Docker)", "Deployment"): (5, "Render auto-deploys the Docker container")}),
                      pack)
    assert "Proven over time" not in judge.rules() and "Tested / evaluated" in judge.rules()
    verdict = judge.judge(next(s for s in pack.skills if s["id"] == "containers"), CHUNKS[0])
    assert verdict["tier"] == 4


def evidence(project, repo, tier=4, verified="self"):
    return {"tier": tier, "project": project, "repo": repo, "verified_by": verified}


@pytest.mark.parametrize("items, first, reached", [
    ([evidence("Ask Barry", "ask-barry"), evidence("Wall Inspector", "wall_inspector")], "2025-09-01", True),
    ([evidence("Ask Barry", "ask-barry"), evidence("Wall Inspector", "wall_inspector")], "2026-09-01", False),  # 1 month
    ([evidence("Ask Barry", "ask-barry"), evidence("Ask Barry", "ask-barry")], "2024-01-01", False),            # 1 project
    ([evidence("Ask Barry", "ask-barry"), evidence("LeetCode", "leetcode-java")], "2024-01-01", False),         # practice
    ([evidence("Ask Barry", "ask-barry"), evidence("Wall Inspector", "wall_inspector")], None, False),          # no dates
    ([evidence("Ask Barry", "ask-barry", tier=2, verified="third_party")], "2026-10-01", True),                 # confirmed
])
def test_proven_over_time_needs_two_applications_and_a_year_or_a_third_party(items, first, reached):
    from app.capability.builder import depth_check
    depth = depth_check(load_pack(), items, first, NOW)
    assert depth["reached"] is reached


def test_a_skill_reaches_tier_5_only_from_the_top_judged_tier(tmp_path):
    from app.capability.builder import build_skill
    pack = load_pack()
    tiers = {("Containers (Docker)", "Deployment"): (4, "Render auto-deploys the Docker container"),
             ("Containers (Docker)", "Testing"): (4, "63 tests run in CI on every push")}
    chunks = [CHUNKS[0], {**CHUNKS[5], "repo": "ask-barry"}]
    provider = FakeProvider(tiers)
    containers = next(s for s in pack.skills if s["id"] == "containers")
    old = build_skill(pack, {**containers, "queries": ["docker tests"]}, FakeRetriever(chunks), TierJudge(provider, pack),
                      first_committed=lambda repo, path: "2025-06-01", log=lambda *_: None, now=NOW)
    assert old["tier"] == 5 and old["depth"]["projects_at_top"] == ["Ask Barry", "Wall Inspector"]
    new = build_skill(pack, {**containers, "queries": ["docker tests"]}, FakeRetriever(chunks), TierJudge(provider, pack),
                      first_committed=lambda repo, path: "2026-09-01", log=lambda *_: None, now=NOW)
    assert new["tier"] == 4 and new["depth"]["reached"] is False and new["depth"]["months"] == 1


def test_barry_has_no_tier_5_today_and_the_page_shows_five_steps():
    cap, _ = build()
    assert problems(cap) == [] and max(s["tier"] for s in cap["skills"]) <= 4
    assert cap["tiers"][-1] == {"level": 5, "universal": "Sustained", "label": "Proven over time", "computed": True}
    html = app_with(cap).get("/capability").get_data(as_text=True)
    assert 'style="--n:5"' in html and "never awarded by the AI judge" in html
    assert "not yet reached (worked out from the evidence, never self-rated)" in html


def test_a_four_tier_pack_without_kinds_still_works():
    cap, _ = build(pack=load_pack(NURSE))
    assert len(cap["tiers"]) == 4 and all("depth" not in s for s in cap["skills"])
    assert all("kind" not in e for s in cap["skills"] for e in s["evidence"])
    html = app_with(cap).get("/capability").get_data(as_text=True)
    assert 'style="--n:4"' in html and "never awarded by the AI judge" not in html


@pytest.mark.parametrize("change, message", [
    (lambda t: t["tiers"][2].update(computed={"min_projects": 2, "min_months": 12}), "only the top tier can be computed"),
    (lambda t: t["tiers"].pop(1), "no gaps"),
])
def test_tier_rules_are_checked(tmp_path, change, message):
    folder = copy_pack(tmp_path)
    tiers = yaml.safe_load((folder / "tiers.yaml").read_text())
    change(tiers)
    (folder / "tiers.yaml").write_text(yaml.safe_dump(tiers))
    with pytest.raises(PackError, match=message):
        load_pack(folder)


def test_an_unknown_project_kind_is_refused(tmp_path):
    with pytest.raises(PackError, match="isn't in project_kinds"):
        kinds_pack(tmp_path, ask_barry2={"name": "X", "kind": "hobby"})


def test_each_tier_name_sits_above_its_own_column():
    cap, _ = build()
    html = app_with(cap).get("/capability").get_data(as_text=True)
    head = html.split("<thead>", 1)[1].split("</thead>", 1)[0]
    assert 'class="steps heads" style="--n:5"' in head
    assert [t in head for t in ("Used", "Built", "In production", "Tested / evaluated", "Proven over time")] == [True] * 5


# --- ASK-58: evidence is carried forward so new repos can't crowd it out -------------------------------------------

class QuoteOnlyRetriever:
    """Search never ranks the section for the skill's queries (crowded out), but finds it by its quote."""

    def __init__(self, chunk, quote="Render auto-deploys the Docker container"):
        self.chunk, self.quote, self.calls = chunk, quote, []

    def search(self, query, k=5):
        self.calls.append(query)
        return [SearchResult(self.chunk, 1.0, 1)] if query == self.quote else []


def containers_skill():
    return next(s for s in load_pack().skills if s["id"] == "containers")


def last_build_evidence(chunk, quote):
    return {"containers": [{"tier": 3, "repo": chunk["repo"], "path": chunk["path"], "heading": chunk["heading"],
                            "quote": quote}]}


def test_a_section_that_counted_last_night_is_judged_again_even_when_search_misses_it():
    from app.capability.builder import build_skill
    pack, lines = load_pack(), []
    retriever = QuoteOnlyRetriever(CHUNKS[0])
    judge = TierJudge(FakeProvider(DOCKER_TIERS), pack)
    without = build_skill(pack, containers_skill(), retriever, judge, log=lambda *_: None, now=NOW)
    assert without["tier"] == 0                                         # crowded out: nothing found
    carried = build_skill(pack, containers_skill(), retriever, judge, log=lines.append, now=NOW, explain=True,
                          previous=last_build_evidence(CHUNKS[0], "Render auto-deploys the Docker container"))
    assert carried["tier"] == 3 and carried["evidence"][0]["heading"] == "Deployment"
    assert any("[carried from last build] -> tier 3" in line for line in lines)


def test_a_section_whose_quote_no_longer_fits_is_not_carried():
    from app.capability.builder import build_skill
    pack = load_pack()
    edited = {**CHUNKS[0], "text": "Render deploys the app after GitHub Actions runs 63 tests."}
    out = build_skill(pack, containers_skill(), QuoteOnlyRetriever(edited), TierJudge(FakeProvider(DOCKER_TIERS), pack),
                      log=lambda *_: None, now=NOW,
                      previous=last_build_evidence(edited, "Render auto-deploys the Docker container"))
    assert out["tier"] == 0 and out["evidence"] == []


def test_the_build_passes_last_nights_evidence_and_explain_through():
    lines = []
    first, _ = build()
    cap, _ = build(previous=first, log=lines.append)
    assert skill(cap, "containers")["tier"] == skill(first, "containers")["tier"]
    pack = load_pack()
    provider = FakeProvider(DOCKER_TIERS)
    build_capability(pack, FakeRetriever(), TierJudge(provider, pack), StoryWriter(provider, pack), now=NOW,
                     log=lines.append, previous=first, explain=("containers",))
    assert any(line.startswith("  explain containers:") for line in lines)
    assert not any(line.startswith("  explain kubernetes:") for line in lines)


def test_seed_evidence_merges_without_duplicates():
    from scripts.build_capability import merge_evidence
    a = {"skills": [{"id": "python-flask", "evidence": [{"repo": "ask-barry", "path": "README.md", "heading": "Run locally"}]}]}
    b = {"skills": [{"id": "python-flask", "evidence": [{"repo": "ask-barry", "path": "README.md", "heading": "Deployment"},
                                                        {"repo": "ask-barry", "path": "README.md", "heading": "Run locally"}]},
                    {"id": "databases-sql", "evidence": [{"repo": "wall_inspector", "path": "README.md", "heading": "Migrations"}]}]}
    merged = merge_evidence(a, b)
    by_id = {s["id"]: [e["heading"] for e in s["evidence"]] for s in merged["skills"]}
    assert by_id == {"python-flask": ["Run locally", "Deployment"], "databases-sql": ["Migrations"]}
    assert [e["heading"] for e in a["skills"][0]["evidence"]] == ["Run locally"]          # the input is not changed


# --- ASK-60: the quote check reads the judge's quotes the way the judge writes them -------------------------------

README_SECTION = ("Ask Barry is a Flask app running in production on Render at "
                  "[ask-barry.onrender.com](https://ask-barry.onrender.com), served by gunicorn (`gunicorn wsgi:app`). "
                  "`render.yaml` defines the web service (starter plan).\n\n"
                  "CI runs the full pytest suite on every push.\n\n```bash\nmvn test\n```")


@pytest.mark.parametrize("quote", [
    "Ask Barry is a Flask app running in production on Render at ask-barry.onrender.com, served by gunicorn.",
    "served by gunicorn (`gunicorn wsgi:app`). CI runs the full pytest suite on every push.",      # a sentence left out
    "mvn test",                                                                                     # a short command
])
def test_quotes_with_links_dropped_sentences_or_a_short_command_are_found(quote):
    from app.quotes import quote_in_sources
    assert quote_in_sources(quote, README_SECTION, elided=True)


@pytest.mark.parametrize("quote", [
    "Ask Barry is a Flask app running in production on Kubernetes with 500 tests",                 # invented ending
    "CI runs the full pytest suite on every push and deploys to AWS Lambda nightly",
    "Flask",                                                                                         # one word proves nothing
    "Ask Barry runs the full pytest suite",                                                          # 2-word run stitched on
])
def test_invented_or_stitched_quotes_still_fail(quote):
    from app.quotes import quote_in_sources
    assert not quote_in_sources(quote, README_SECTION, elided=True)


def test_answer_evaluation_keeps_the_strict_rule():
    """Elided quotes are for the capability judge only; Stage 6 answer checks are unchanged."""
    from app.quotes import quote_in_sources
    assert not quote_in_sources("mvn test", README_SECTION)


# --- ASK-64: the nightly command line runs the build with or without --seed-evidence ------------------------------

@pytest.mark.parametrize("seeded", [False, True])
def test_build_command_builds_once_with_or_without_seeds(tmp_path, monkeypatch, seeded):
    """The ASK-58 version only built inside the --seed-evidence loop, so the nightly run (no seeds) crashed."""
    import scripts.build_capability as cli
    cap, _ = build()
    calls = []

    def fake_build(*args, **kwargs):
        calls.append(kwargs.get("previous"))
        return cap, {"suggestions": []}

    monkeypatch.setattr(cli, "load_env", lambda: None)
    monkeypatch.setattr(cli, "live_parts", lambda: (None, None))
    monkeypatch.setattr(cli, "build_capability", fake_build)
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps(cap))
    argv = ["--no-dates", "--previous", str(tmp_path / "none.json"),
            "--out", str(tmp_path / "out.json"), "--suggestions", str(tmp_path / "sugg.json")]
    cli.main(argv + (["--seed-evidence", str(seed)] if seeded else []))
    assert len(calls) == 1 and (calls[0] is not None) == seeded
    assert json.loads((tmp_path / "out.json").read_text())["skills"]

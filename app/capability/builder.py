"""Build capability.json from the search index (ASK-42): the ladder and the evidence cards.

For each skill: run its queries through the production retriever, then for each section found ask the judge
one narrow question: "what is the highest tier this section shows for this skill?", with a quote. The quote
must really be in the section (checked in code, as in the Stage 6 evaluator), or that answer counts as 0.
The question is asked up to three times per section and the section gets the middle answer (the median), so
one borderline answer can't move a skill up or down. Two matching answers settle it without a third call.
The skill's tier is the highest tier any section gets. No scores, no averages.

Cards work the same way: each card's queries find sections, a writer drafts a short example with a quote,
the quote is checked, and only examples the person has approved (cards.yaml) go live. The rest are written
to a suggestions file for review.

Everything about the person and their profession comes from the profile pack; nothing is hard-coded here.
"""
import hashlib
import json
import time
from datetime import datetime, timezone

from app.capability.plans import plan_statuses
from app.quotes import quote_in_sources

SCHEMA_VERSION = "1.0"
PER_QUERY = 6              # sections retrieved per query
MAX_SECTIONS = 10          # sections judged per skill or card (keeps the nightly cost small)
MAX_EVIDENCE = 8           # evidence links kept per skill in the output
MAX_QUOTE_WORDS = 40
SEARCH_TRIES = 3           # a search that times out is retried (Azure AI Search can be slow under load)
VOTES = 3                  # judge answers per section; the section gets the median (ASK-42 stability check)


def section_label(chunk):
    heading = f" ({chunk.get('heading')})" if chunk.get("heading") else ""
    return f"{chunk.get('repo', '')}/{chunk.get('path', '')}{heading}"


def section_text(chunk):
    return f"{section_label(chunk)}\n{chunk.get('text', '')}"


def _parse(raw):
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def _short(quote):
    words = str(quote or "").split()
    return " ".join(words[:MAX_QUOTE_WORDS])


# --- the two model calls -------------------------------------------------------------------------------------

class TierJudge:
    """One section, one skill -> {"tier": 0-4, "quote": "..."} from a model in JSON mode."""

    def __init__(self, provider, pack):
        self.provider, self.pack = provider, pack

    def rules(self):
        name = self.pack.person["name"]
        tiers = "\n".join(f"{t['level']} {t['label']}: {t['criteria']}" for t in self.pack.tiers)
        return f"""You check evidence of a skill in {name}'s public documentation.
You get one SECTION, labelled with its repo, file and heading, and one SKILL.
Decide the HIGHEST tier that this section itself shows for the skill. Each tier includes the ones below it:
{tiers}
0 = the section doesn't show the skill at tier 1, or only mentions it as planned, future, optional, or done by
someone else.
Judge only what this section states. Copy the words that prove the tier exactly from the section (at most 30
words). For tier 0 the quote is "".
Reply with JSON only: {{"tier": 0, "quote": ""}}"""

    def judge(self, skill, chunk):
        user = (f"SKILL: {skill['name']}: {skill['description']}\n\n"
                f"SECTION [{section_label(chunk)}]:\n{chunk.get('text', '')}")
        data = _parse(self.provider.generate([{"role": "system", "content": self.rules()},
                                              {"role": "user", "content": user}], max_tokens=200))
        try:
            tier = max(0, min(4, int(data.get("tier", 0))))
        except (TypeError, ValueError):
            tier = 0
        return {"tier": tier, "quote": _short(data.get("quote"))}


class StoryWriter:
    """One section, one card -> a short documented example, or {"example": false}."""

    def __init__(self, provider, pack):
        self.provider, self.pack = provider, pack

    def rules(self):
        name, short = self.pack.person["name"], self.pack.person["short_name"]
        return f"""You find documented examples of a professional skill in {name}'s public documentation.
You get one SECTION, labelled with its repo, file and heading, and one CARD (the skill).
If the section describes a concrete example of the skill (a specific situation, what {short} did, and the
result if stated), write it up. Otherwise set "example" to false.
Use only facts the section states. No praise and no adjectives the section doesn't use.
"title": at most 6 words. "summary": at most 35 words, past tense. "quote": words copied exactly from the
section (at most 30) that show the example.
Reply with JSON only: {{"example": false, "title": "", "summary": "", "quote": ""}}"""

    def write(self, card, chunk):
        user = f"CARD: {card['title']}\n\nSECTION [{section_label(chunk)}]:\n{chunk.get('text', '')}"
        data = _parse(self.provider.generate([{"role": "system", "content": self.rules()},
                                              {"role": "user", "content": user}], max_tokens=300))
        return {"example": bool(data.get("example")), "title": str(data.get("title") or "").strip(),
                "summary": str(data.get("summary") or "").strip(), "quote": _short(data.get("quote"))}


# --- retrieval ------------------------------------------------------------------------------------------------

def search(retriever, query, k, tries=SEARCH_TRIES, wait=5, sleep=time.sleep, log=print):
    """retriever.search with a few retries, so one slow reply doesn't end a whole build."""
    for attempt in range(1, tries + 1):
        try:
            return retriever.search(query, k=k)
        except Exception as err:                       # timeouts and throttling from the search service
            if attempt == tries:
                raise
            log(f"  search for {query!r} failed ({type(err).__name__}); retry {attempt} of {tries - 1}")
            sleep(wait * attempt)


def find_sections(retriever, queries, k=PER_QUERY, limit=MAX_SECTIONS):
    """Union of the top-k sections for each query, best rank first, no duplicates."""
    best = {}
    for query in queries:
        for result in search(retriever, query, k):
            cid = result.chunk.get("chunk_id") or section_label(result.chunk)
            if cid not in best or result.rank < best[cid][0]:
                best[cid] = (result.rank, len(best), result.chunk)
    ranked = sorted(best.values(), key=lambda v: (v[0], v[1]))
    return [chunk for _, _, chunk in ranked[:limit]]


def story_id(card_id, chunk):
    key = chunk.get("chunk_id") or section_label(chunk)
    return f"{card_id}:{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"


# --- the build ------------------------------------------------------------------------------------------------

def _source_fields(pack, chunk):
    return {"repo": chunk.get("repo", ""), "path": chunk.get("path", ""), "heading": chunk.get("heading", ""),
            "url": chunk.get("url", ""), "project": pack.project_name(chunk.get("repo", "")),
            "source_type": "github_readme", "verified_by": "self"}


def vote(skill, chunk, judge, votes=VOTES, log=print):
    """Ask the judge up to `votes` times; return the median answer. A quote that isn't in the section makes
    that answer 0. Stops early once one answer has a majority."""
    answers = []
    for _ in range(max(1, votes)):
        verdict = judge.judge(skill, chunk)
        if verdict["tier"] and not quote_in_sources(verdict["quote"], section_text(chunk)):
            verdict = {"tier": 0, "quote": "", "discarded": verdict["tier"]}
        answers.append(verdict)
        tiers = [a["tier"] for a in answers]
        if max(tiers.count(t) for t in tiers) * 2 > votes:
            break
    ordered = sorted(answers, key=lambda a: a["tier"])
    chosen = ordered[(len(ordered) - 1) // 2]          # the median; with an even count, the lower middle
    tiers = [a["tier"] for a in answers]
    if len(set(tiers)) > 1 or any("discarded" in a for a in answers):
        shown = ", ".join(f"{a['tier']}" + (f" (quote not found for {a['discarded']})" if "discarded" in a else "")
                          for a in answers)
        log(f"  {skill['id']}: {section_label(chunk)} answers {shown} -> {chosen['tier']}")
    return chosen


def build_skill(pack, skill, retriever, judge, first_committed=None, log=print, votes=VOTES):
    evidence = []
    for rank, chunk in enumerate(find_sections(retriever, skill["queries"])):
        if pack.is_self_description(chunk.get("repo", "")):
            continue                                   # a self-description isn't evidence of use
        if pack.is_planned(chunk.get("heading", "")):
            continue                                   # nor is a plan
        verdict = vote(skill, chunk, judge, votes, log)
        tier, quote = verdict["tier"], verdict["quote"]
        if not tier:
            continue
        item = {"tier": tier, **_source_fields(pack, chunk), "quote": quote}
        if first_committed:
            item["first_committed"] = first_committed(chunk.get("repo", ""), chunk.get("path", ""))
        evidence.append((tier, rank, item))
    evidence.sort(key=lambda e: (-e[0], e[1]))
    items = [e[2] for e in evidence]
    tier = items[0]["tier"] if items else 0
    projects = {str(t): sorted({i["project"] for i in items if i["tier"] >= t}) for t in range(1, 5)}
    dates = sorted(d for d in (i.get("first_committed") for i in items) if d)
    out = {"id": skill["id"], "name": skill["name"], "tier": tier,
           "first_evidence": dates[0][:7] if dates else None,
           "projects_by_tier": {t: p for t, p in projects.items() if p},
           "evidence": items[:MAX_EVIDENCE]}
    if skill.get("esco_uri"):
        out["esco_uri"] = skill["esco_uri"]
    if skill.get("match"):
        out["match"] = skill["match"]
    return out


def _recheck(card, story, sections, retriever, log):
    """An approved example from the last build stays live, word for word, while its quote is still in its section.
    The section is looked for among this build's sections first, then by searching for the quote itself."""
    pool = list(sections)
    if not any(story_id(card["id"], c) == story["id"] for c in pool):
        pool += [r.chunk for r in search(retriever, story["quote"], PER_QUERY)]
    for chunk in pool:
        if story_id(card["id"], chunk) == story["id"]:
            if quote_in_sources(story["quote"], section_text(chunk)):
                return story
            break
    log(f"  card {card['id']}: approved example {story['id']} no longer matches its source; dropped")
    return None


def build_card(pack, card, retriever, writer, log=print, previous=None):
    """Returns (card for capability.json, every candidate for the suggestions file).

    previous: {story id: story} from the last published build. An approved example that was already live keeps
    its approved wording (re-checked against the source), so the page doesn't change because a draft did."""
    previous = previous or {}
    sections = find_sections(retriever, card["queries"])
    candidates = []
    for chunk in sections:
        draft = writer.write(card, chunk)
        if not (draft["example"] and draft["summary"]):
            continue
        if not quote_in_sources(draft["quote"], section_text(chunk)):
            log(f"  card {card['id']}: quote not found in {section_label(chunk)}; example discarded")
            continue
        candidates.append({"id": story_id(card["id"], chunk), "title": draft["title"] or card["title"],
                           "summary": draft["summary"], **_source_fields(pack, chunk), "quote": draft["quote"]})
    approved = list(card.get("approved") or [])
    by_id = {c["id"]: c for c in candidates}
    stories = []
    for sid in approved:
        kept = _recheck(card, previous[sid], sections, retriever, log) if sid in previous else None
        story = kept or by_id.get(sid)
        if story:
            stories.append(story)
    live = {"id": card["id"], "title": card["title"], "gap": not stories, "stories": stories}
    if not stories and card.get("gap_note"):
        live["gap_note"] = card["gap_note"]
    found = {st["id"] for st in stories}
    suggestion = {"card": card["id"], "title": card["title"],
                  "approved_but_not_found": [i for i in approved if i not in found],
                  "candidates": [{**c, "approved": c["id"] in approved} for c in candidates]}
    return live, suggestion


def previous_stories(capability):
    """{story id: story} from an earlier capability.json (or {} if there isn't one)."""
    return {st["id"]: st for c in (capability or {}).get("cards", []) for st in c.get("stories", [])}


def build_capability(pack, retriever, judge, writer, first_committed=None, now=None, log=print, votes=VOTES,
                     previous=None):
    """-> (capability dict, suggestions dict). Deterministic given the same retriever and model answers.
    previous: the last published capability.json, so approved examples keep their approved wording."""
    now = now or datetime.now(timezone.utc)
    skills, cards, suggestions = [], [], []
    for skill in pack.skills:
        log(f"skill {skill['id']}")
        skills.append(build_skill(pack, skill, retriever, judge, first_committed, log, votes))
    for card in pack.cards:
        log(f"card {card['id']}")
        live, suggestion = build_card(pack, card, retriever, writer, log, previous_stories(previous))
        cards.append(live)
        suggestions.append(suggestion)
    repos = sorted({e["repo"] for s in skills for e in s["evidence"]} |
                   {st["repo"] for c in cards for st in c["stories"]})
    capability = {
        "schema_version": SCHEMA_VERSION,
        "profile_id": pack.profile_id,
        "person": dict(pack.person),
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sources": {"repos": repos},
        "tiers": [{"level": t["level"], "universal": t["universal"], "label": t["label"]} for t in pack.tiers],
        "skills": skills,
        "cards": cards,
    }
    plans, record = plan_statuses(pack, skills, cards, previous, now)
    if plans:
        capability["plans"], capability["plan_record"] = plans, record
    return capability, {"generated_at": capability["generated_at"], "cards": suggestions}


def same_content(a, b):
    """True if two builds say the same thing (ignores when they were generated)."""
    strip = lambda d: {k: v for k, v in (d or {}).items() if k != "generated_at"}    # noqa: E731
    return json.dumps(strip(a), sort_keys=True) == json.dumps(strip(b), sort_keys=True)

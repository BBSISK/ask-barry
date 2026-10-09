"""Turn capability.json into what the page shows (ASK-42): ladder rows, the job-ad view, the fit summary.

Kept free of Flask so it's easy to test, and free of anything about a particular person or profession.
"""
import re


def _words(text):
    return " " + " ".join(re.findall(r"[a-z0-9+#/.]+", str(text or "").lower())) + " "


def matching_skills(capability, requirement):
    """Skill ids whose match phrases appear (as whole words) in a job-ad requirement."""
    text = _words(requirement)
    return [s["id"] for s in capability["skills"]
            if any(_words(p) in text for p in s.get("match") or [])]


def match_job(capability, requirements):
    """-> (required skill ids in ad order, requirements that match no skill on the list)."""
    required, unmatched = [], []
    for req in requirements:
        ids = matching_skills(capability, req)
        if not ids:
            unmatched.append(req)
        for i in ids:
            if i not in required:
                required.append(i)
    return required, unmatched


def ladder(capability, required=None):
    """Rows for the page. Full profile: deepest tier first. Job view: the ad's skills first, then the rest."""
    order = {sid: n for n, sid in enumerate(required or [])}
    rows = []
    for n, skill in enumerate(capability["skills"]):
        rows.append({**skill, "required": skill["id"] in order, "position": n})
    if required:
        rows.sort(key=lambda r: (not r["required"], order.get(r["id"], 0), -r["tier"], r["position"]))
    else:
        rows.sort(key=lambda r: (-r["tier"], r["position"]))
    return rows


def fit_summary(capability, required):
    """Counts for the job view, by tier reached: delivered or proven (3+), built or used (1-2), none."""
    skills = {s["id"]: s for s in capability["skills"]}
    tiers = [skills[i]["tier"] for i in required if i in skills]
    return {"required": len(tiers),
            "delivered": sum(t >= 3 for t in tiers),
            "partial": sum(1 <= t <= 2 for t in tiers),
            "none": sum(t == 0 for t in tiers)}


def evidence_for(capability, skill_ref, level=None):
    """The evidence for one skill (by id or name, any case), optionally only what proves a given tier."""
    ref = str(skill_ref or "").strip().lower()
    for skill in capability["skills"]:
        if ref in (skill["id"], skill["name"].lower()):
            items = skill["evidence"] if level is None else [e for e in skill["evidence"] if e["tier"] >= level]
            return skill, items
    return None, []

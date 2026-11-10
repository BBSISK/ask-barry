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


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month_text(value):
    """'2026-12' -> 'Dec 2026' (anything else is shown as it is)."""
    try:
        year, mon = str(value).split("-")
        return f"{MONTHS[int(mon) - 1]} {year}"
    except (ValueError, IndexError):
        return str(value or "")


def day_text(value):
    """'2026-11-10' -> '10 Nov 2026' (anything else is shown as it is)."""
    try:
        year, mon, day = str(value).split("-")
        return f"{int(day)} {MONTHS[int(mon) - 1]} {year}"
    except (ValueError, IndexError):
        return str(value or "")


def plan_view(capability):
    """Gap-closing plans for the page (ASK-50): the next unmet plan per skill and card, every plan for the
    record table, and the track record. Empty when the profile has no plans."""
    plans = [{**p, "target_text": month_text(p["target"]), "planned_text": month_text(p["planned"]),
              "closed_text": month_text(p.get("closed")) if p.get("closed") else ""}
             for p in capability.get("plans") or []]
    by_skill, by_card = {}, {}
    for p in plans:                                     # already sorted by target month
        if p["status"] == "closed":
            continue
        if p.get("skill"):
            by_skill.setdefault(p["skill"], p)
        else:
            by_card.setdefault(p["card"], p)
    return {"plans": plans, "by_skill": by_skill, "by_card": by_card, "record": capability.get("plan_record")}


# --- the evidence curve (ASK-74) ------------------------------------------------------------------------------
# A fixed drawing on a 1100 x 640 canvas: a first climb to a peak, a dip, and a second climb. Which skills sit on
# each climb comes from the profile pack's curve.yaml; every tier, quote and link comes from capability.json.
CURVE_W, CURVE_H = 1100, 640
CURVE_PATHS = {
    "first": "M180 570 C310 570 370 250 440 70",
    "peak_and_dip": "M440 70 C460 20 490 20 512 80 C570 260 590 575 660 575",
    "second": "M660 575 C740 575 780 330 840 230 C870 180 900 155 940 150",
}
_FIRST = [((180, 570), (310, 570), (370, 250), (440, 70))]
_SECOND = [((660, 575), (740, 575), (780, 330), (840, 230)), ((840, 230), (870, 180), (900, 155), (940, 150))]
_FIRST_Y, _SECOND_Y = (535, 103), (440, 175)        # where the lowest and highest dot of each climb sit


def _bezier(p, t):
    u = 1 - t
    return tuple(u ** 3 * p[0][i] + 3 * u * u * t * p[1][i] + 3 * u * t * t * p[2][i] + t ** 3 * p[3][i]
                 for i in (0, 1))


def _x_at(segments, y):
    """x on a climb (y falls as it rises) where it reaches height y."""
    points = [_bezier(seg, k / 200) for seg in segments for k in range(201)]
    return round(min(points, key=lambda pt: abs(pt[1] - y))[0])


def _heights(n, low, high):
    if n == 1:
        return [round((low + high) / 2)]
    return [round(low - k * (low - high) / (n - 1)) for k in range(n)]


def _best_evidence(skill):
    items = skill.get("evidence") or []
    return max(items, key=lambda e: e["tier"]) if items else None


def curve_view(capability, curve):
    """Everything /curve draws: dot positions, tier classes, and each dot's proof. None without a curve."""
    if not curve or not capability:
        return None
    skills = {s["id"]: s for s in capability["skills"]}
    labels = {t["level"]: t["label"] for t in capability["tiers"]}
    plans = {p["skill"]: p for p in capability.get("plans") or [] if p.get("skill") and p.get("status") != "closed"}
    climbs = []
    for side, climb in enumerate(curve["climbs"][:2]):
        ids = [sid for sid in climb["skills"] if sid in skills]
        segments, (low, high) = (_FIRST, _FIRST_Y) if side == 0 else (_SECOND, _SECOND_Y)
        nodes = []
        for sid, y in zip(ids, _heights(len(ids), low, high)):
            skill, x = skills[sid], _x_at(segments, y)
            best = _best_evidence(skill)
            plan = plans.get(sid)
            projects = (skill.get("projects_by_tier") or {}).get(str(skill["tier"])) or []
            nodes.append({
                "id": sid, "name": skill["name"], "tier": skill["tier"],
                "tier_label": labels.get(skill["tier"], "Not evidenced yet") if skill["tier"] else "Not evidenced yet",
                "cls": f"t{skill['tier']}" if skill["tier"] else "gap",
                "x": x, "y": y, "label_x": x - 24 if side == 0 else x + 24, "anchor": "end" if side == 0 else "start",
                "sub": ", ".join(projects[:2]) if skill["tier"] else "Not evidenced yet",
                "projects": ", ".join(projects),
                "quote": best["quote"] if best and skill["tier"] else "",
                "url": best["url"] if best and skill["tier"] else "",
                "source": f"{best['repo']} · {best['path']}" + (f" · {best['heading'].split(' > ')[-1]}" if best.get("heading") else "")
                          if best and skill["tier"] else "",
                "plan": {"work": plan["work"], "target": month_text(plan["target"])} if plan else None,
            })
        climbs.append({"name": climb["name"], "note": climb.get("note", ""), "nodes": nodes})
    return {"title": curve["title"], "intro": curve.get("intro", ""), "credit": curve.get("credit", ""),
            "dip": curve["dip"], "bridge": curve["bridge"], "climbs": climbs,
            "as_of": capability.get("generated_at", "")[:10], "width": CURVE_W, "height": CURVE_H,
            "paths": CURVE_PATHS, "top_tier": max(labels) if labels else 0}

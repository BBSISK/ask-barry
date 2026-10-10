"""Gap-closing plans on the capability page (ASK-50).

A plan says what the person is doing about a gap, by when. It is shown beside the gap and never fills a tier:
tiers still come only from evidence the judge has checked. Each nightly build works out where every plan stands:

  open     the evidence hasn't reached the target yet, and the target month hasn't passed
  overdue  the target month has passed without the evidence (kept visible, never dropped quietly)
  closed   the evidence reached the target. The month it first did is kept from the previous build, so the
           record of "planned for March, closed in February" survives every later rebuild.

The track record (closed, on time, open, overdue) is what lets a reader judge whether plans get delivered.
Nothing here is about a particular person or profession: plans.yaml is part of the profile pack.
"""

def month(now):
    return now.strftime("%Y-%m")


def _met(plan, skills, cards):
    if "skill" in plan:
        return skills[plan["skill"]]["tier"] >= plan["target_tier"]
    return not cards[plan["card"]]["gap"]


def plan_statuses(pack, skills, cards, previous=None, now=None):
    """-> (plans for capability.json, plan_record). skills/cards are this build's; previous is the last build."""
    if not pack.plans:
        return [], None
    this_month = month(now)
    skills = {s["id"]: s for s in skills}
    cards = {c["id"]: c for c in cards}
    before = {p["id"]: p for p in (previous or {}).get("plans", [])}
    out = []
    for plan in sorted(pack.plans, key=lambda p: (p["target"], p["id"])):
        item = {"id": plan["id"], "work": plan["work"], "planned": plan["planned"], "target": plan["target"]}
        if "skill" in plan:
            item.update(skill=plan["skill"], name=skills[plan["skill"]]["name"], target_tier=plan["target_tier"],
                        target_label=pack.tier_label(plan["target_tier"]))
        else:
            item.update(card=plan["card"], name=cards[plan["card"]]["title"])
        if _met(plan, skills, cards):
            earlier = before.get(plan["id"])
            closed = earlier["closed"] if earlier and earlier.get("status") == "closed" else this_month
            item.update(status="closed", closed=closed, on_time=closed <= plan["target"])
        else:
            item["status"] = "overdue" if this_month > plan["target"] else "open"
        out.append(item)
    record = {"total": len(out),
              "closed": sum(p["status"] == "closed" for p in out),
              "on_time": sum(bool(p.get("on_time")) for p in out),
              "open": sum(p["status"] == "open" for p in out),
              "overdue": sum(p["status"] == "overdue" for p in out)}
    return out, record

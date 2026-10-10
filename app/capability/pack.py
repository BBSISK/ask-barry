"""Load and validate a profile pack: the folder that says whose capability this is (ASK-42, ASK-43).

A pack is four YAML files (profile, tiers, skills, cards), plus an optional plans.yaml (ASK-50). Each is checked against a JSON Schema, then
against a few rules a schema can't express (unique ids, tiers 1-4 in order). Errors name the file and the
field, so someone setting up their own pack can fix it without reading code.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).resolve().parent / "schemas"
FILES = ("profile", "tiers", "skills", "cards")
DEFAULT_PACK = Path(__file__).resolve().parents[2] / "profile"


class PackError(ValueError):
    """The profile pack is missing a file or breaks a rule. The message says which file and field."""


@dataclass
class Pack:
    profile: dict
    tiers: list
    skills: list
    cards: list
    path: Path = field(default=None)
    plans: list = field(default_factory=list)

    @property
    def profile_id(self):
        return self.profile["profile_id"]

    @property
    def person(self):
        return self.profile["person"]

    def tier_label(self, level):
        return next((t["label"] for t in self.tiers if t["level"] == level), str(level))

    def project_name(self, repo):
        return (self.profile.get("projects") or {}).get(repo, repo)

    def is_self_description(self, repo):
        return repo in (self.profile.get("self_description_repos") or [])

    def is_planned(self, heading):
        """True if a section heading marks plans rather than done work (words from planned_headings)."""
        words = self.profile.get("planned_headings") or []
        text = str(heading or "").lower()
        return any(re.search(rf"\b{re.escape(w.lower())}\b", text) for w in words)


def schema(name):
    return json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate(data, name, where):
    """Raise PackError listing every schema problem in one file."""
    errors = sorted(Draft202012Validator(schema(name)).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"  {'/'.join(str(p) for p in e.path) or '(top level)'}: {e.message}" for e in errors[:10]]
        raise PackError(f"{where} doesn't match the {name} format:\n" + "\n".join(lines))


def _read(folder, name):
    path = Path(folder) / f"{name}.yaml"
    if not path.exists():
        raise PackError(f"Missing {path}: a profile pack needs {', '.join(f + '.yaml' for f in FILES)}.")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as err:
        raise PackError(f"{path} isn't valid YAML: {err}") from None
    validate(data, name, path)
    return data


def _unique(items, what, where):
    seen = set()
    for item in items:
        if item["id"] in seen:
            raise PackError(f"{where}: {what} id '{item['id']}' is used twice.")
        seen.add(item["id"])


def load_pack(folder=DEFAULT_PACK):
    folder = Path(folder)
    data = {name: _read(folder, name) for name in FILES}
    tiers = sorted(data["tiers"]["tiers"], key=lambda t: t["level"])
    if [t["level"] for t in tiers] != [1, 2, 3, 4]:
        raise PackError(f"{folder / 'tiers.yaml'}: tiers must be levels 1, 2, 3 and 4, once each.")
    _unique(data["skills"]["skills"], "skill", folder / "skills.yaml")
    _unique(data["cards"]["cards"], "card", folder / "cards.yaml")
    return Pack(profile=data["profile"], tiers=tiers, skills=data["skills"]["skills"],
                cards=data["cards"]["cards"], path=folder, plans=_plans(folder, data))


def _plans(folder, data):
    """Optional plans.yaml: each plan must point at a skill or card on this pack."""
    path = Path(folder) / "plans.yaml"
    if not path.exists():
        return []
    plans = _read(folder, "plans")["plans"]
    _unique(plans, "plan", path)
    skills = {s["id"] for s in data["skills"]["skills"]}
    cards = {c["id"] for c in data["cards"]["cards"]}
    for plan in plans:
        if "skill" in plan and plan["skill"] not in skills:
            raise PackError(f"{path}: plan '{plan['id']}' names skill '{plan['skill']}', which isn't in skills.yaml.")
        if "card" in plan and plan["card"] not in cards:
            raise PackError(f"{path}: plan '{plan['id']}' names card '{plan['card']}', which isn't in cards.yaml.")
        if plan["target"] < plan["planned"]:
            raise PackError(f"{path}: plan '{plan['id']}' has a target month before the month it was planned.")
    return plans

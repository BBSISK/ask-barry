"""Load and validate a profile pack: the folder that says whose capability this is (ASK-42, ASK-43).

A pack is four YAML files (profile, tiers, skills, cards), plus an optional plans.yaml (ASK-50). Each is checked against a JSON Schema, then
against a few rules a schema can't express (unique ids, tiers 1..N in order, project kinds that exist). Errors name the file and the
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

    # --- tiers (ASK-57): the judge awards only the judged tiers; a computed top tier comes from the evidence ---
    @property
    def judged_tiers(self):
        return [t for t in self.tiers if not t.get("computed")]

    @property
    def top_judged(self):
        return self.judged_tiers[-1]["level"]

    @property
    def computed_tier(self):
        return next((t for t in self.tiers if t.get("computed")), None)

    # --- projects: a display name and a kind; the kind caps how far its evidence can go (ASK-57) ---
    def _project(self, repo):
        value = (self.profile.get("projects") or {}).get(repo)
        return value if isinstance(value, dict) else {"name": value or repo}

    def project_name(self, repo):
        return self._project(repo)["name"]

    def project_kind(self, repo):
        """The repo's kind, or the pack's default_kind. None when the pack defines no kinds (no caps)."""
        if not self.profile.get("project_kinds"):
            return None
        return self._project(repo).get("kind") or self.profile.get("default_kind")

    def max_tier(self, repo):
        kind = self.project_kind(repo)
        if kind is None:
            return self.top_judged
        return min(self.profile["project_kinds"][kind]["max_tier"], self.top_judged)

    def counts_for_depth(self, repo):
        kind = self.project_kind(repo)
        return kind is None or bool(self.profile["project_kinds"][kind].get("counts_for_depth"))

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
    where = folder / "tiers.yaml"
    if [t["level"] for t in tiers] != list(range(1, len(tiers) + 1)):
        raise PackError(f"{where}: tiers must be levels 1, 2, 3 ... with no gaps, once each.")
    computed = [t["level"] for t in tiers if t.get("computed")]
    if computed and (computed != [tiers[-1]["level"]] or len(tiers) - 1 < 2):
        raise PackError(f"{where}: only the top tier can be computed, and at least two judged tiers must sit below it.")
    _check_kinds(folder, data["profile"], tiers)
    _unique(data["skills"]["skills"], "skill", folder / "skills.yaml")
    _unique(data["cards"]["cards"], "card", folder / "cards.yaml")
    return Pack(profile=data["profile"], tiers=tiers, skills=data["skills"]["skills"],
                cards=data["cards"]["cards"], path=folder, plans=_plans(folder, data))


def _check_kinds(folder, profile, tiers):
    """Every project's kind, and the default kind, must be defined in project_kinds."""
    kinds = profile.get("project_kinds") or {}
    where = folder / "profile.yaml"
    if not kinds:
        return
    default = profile.get("default_kind")
    if default is None or default not in kinds:
        raise PackError(f"{where}: default_kind must name one of project_kinds ({', '.join(kinds)}).")
    for repo, value in (profile.get("projects") or {}).items():
        kind = value.get("kind") if isinstance(value, dict) else None
        if kind is not None and kind not in kinds:
            raise PackError(f"{where}: project '{repo}' has kind '{kind}', which isn't in project_kinds.")
    top = max(t["level"] for t in tiers)
    for name, spec in kinds.items():
        if spec["max_tier"] > top:
            raise PackError(f"{where}: project kind '{name}' has max_tier {spec['max_tier']}, above the top tier {top}.")


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

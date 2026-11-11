"""ASK-74: the evidence curve. Its layout comes from the profile pack; every tier, quote and link from capability.json."""
import copy
import json
import re
import shutil
from pathlib import Path

import pytest
import yaml

from app import create_app
from app.capability import view
from app.capability.pack import DEFAULT_PACK, PackError, load_pack
from app.capability.store import CapabilityStore

ROOT = Path(__file__).resolve().parents[1]
CAP = json.loads((ROOT / "data" / "capability.json").read_text(encoding="utf-8"))


def client(cap=CAP, curve="pack"):
    app = create_app("testing", capability_store=CapabilityStore(source="unused", fetch=lambda _s: cap))
    if curve != "pack":
        app.extensions["curve"] = curve
    return app.test_client()


def pack_copy(tmp_path, change):
    folder = tmp_path / "pack"
    shutil.copytree(DEFAULT_PACK, folder)
    data = yaml.safe_load((folder / "curve.yaml").read_text(encoding="utf-8"))
    change(data)
    (folder / "curve.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    return folder


# --- the profile pack ------------------------------------------------------------------------------------------

def test_the_pack_has_a_curve_of_two_climbs_using_real_skill_names():
    pack = load_pack()
    ids = {s["id"] for s in pack.skills}
    climbs = pack.curve["climbs"]
    assert len(climbs) == 2 and all(set(c["skills"]) <= ids for c in climbs)
    assert "Raju Dandigam" in pack.curve["credit"]                     # the original chart is credited


def test_a_skill_that_isnt_in_the_pack_is_refused(tmp_path):
    folder = pack_copy(tmp_path, lambda d: d["climbs"][1]["skills"].append("prompt-wizardry"))
    with pytest.raises(PackError, match="prompt-wizardry"):
        load_pack(folder)


def test_a_skill_on_the_curve_twice_is_refused(tmp_path):
    folder = pack_copy(tmp_path, lambda d: d["climbs"][1]["skills"].append(d["climbs"][0]["skills"][0]))
    with pytest.raises(PackError, match="twice"):
        load_pack(folder)


def test_the_curve_is_optional(tmp_path):
    folder = tmp_path / "pack"
    shutil.copytree(DEFAULT_PACK, folder)
    (folder / "curve.yaml").unlink()
    assert load_pack(folder).curve is None


# --- the view --------------------------------------------------------------------------------------------------

def test_every_dot_takes_its_tier_and_proof_from_the_data():
    curve = view.curve_view(CAP, load_pack().curve)
    skills = {s["id"]: s for s in CAP["skills"]}
    for climb in curve["climbs"]:
        ys = [n["y"] for n in climb["nodes"]]
        assert ys == sorted(ys, reverse=True)                          # each climb rises, bottom to top
        for n in climb["nodes"]:
            skill = skills[n["id"]]
            assert n["tier"] == skill["tier"] and n["name"] == skill["name"]
            if n["tier"]:
                assert n["quote"] in [e["quote"] for e in skill["evidence"]]
                assert n["url"] in [e["url"] for e in skill["evidence"]]


def test_a_gap_is_an_empty_dot_with_no_quote():
    curve = view.curve_view(CAP, load_pack().curve)
    gaps = [n for c in curve["climbs"] for n in c["nodes"] if n["tier"] == 0]
    assert gaps and all(n["cls"] == "gap" and not n["quote"] and not n["url"] for n in gaps)


def test_a_skill_missing_from_the_data_is_left_off_rather_than_invented():
    cap = copy.deepcopy(CAP)
    cap["skills"] = [s for s in cap["skills"] if s["id"] != "java"]
    curve = view.curve_view(cap, load_pack().curve)
    assert "java" not in [n["id"] for c in curve["climbs"] for n in c["nodes"]]


# --- the page --------------------------------------------------------------------------------------------------

def test_page_draws_each_dot_as_a_link_to_its_evidence_card():
    html = client().get("/curve").get_data(as_text=True)
    for climb in load_pack().curve["climbs"]:
        for sid in climb["skills"]:
            assert f'href="#skill-{sid}"' in html and f'id="skill-{sid}"' in html
    assert "<script" not in html                                       # works without JavaScript
    assert "Raju Dandigam" in html and "Evidence as of 26 Oct 2026" in html


def test_page_shows_the_checked_quote_and_a_github_link_only():
    html = client().get("/curve").get_data(as_text=True)
    skill = next(s for s in CAP["skills"] if s["id"] == "rag-llm")
    best = max(skill["evidence"], key=lambda e: e["tier"])
    card = html.split('id="skill-rag-llm"', 1)[1].split("</li>", 1)[0]
    assert best["quote"].split("`")[0][:40] in card.replace("&#39;", "'").replace("&amp;", "&")
    links = re.findall(r'href="([^"#][^"]*)"', html)
    assert all(u.startswith(("https://github.com/", "/")) for u in links)


def test_the_gap_card_says_not_evidenced_not_lacking():
    html = client().get("/curve").get_data(as_text=True)
    card = html.split('id="skill-kubernetes"', 1)[1].split("</li>", 1)[0]
    assert "isn't evidenced, not that I couldn't learn it" in card and "github.com" not in card


def test_page_without_data_says_not_generated_yet():
    html = client(cap=None).get("/curve").get_data(as_text=True)
    assert "hasn't been generated yet" in html and 'href="/capability"' in html


def test_page_without_a_curve_falls_back_to_the_ladder():
    resp = client(curve=None).get("/curve")
    assert resp.status_code == 200 and "no curve set up" in resp.get_data(as_text=True)


def test_home_page_links_to_the_curve_first():
    html = create_app("testing").test_client().get("/").get_data(as_text=True)
    tiles = html.split('class="tiles"', 1)[1].split("</nav>", 1)[0]
    assert tiles.index('href="/curve"') < tiles.index('href="/capability"')


# --- ASK-75: the link-preview image ------------------------------------------------------------------------------

def test_curve_page_has_link_preview_tags_for_the_curve_image():
    html = client().get("/curve").get_data(as_text=True)
    assert 'property="og:image" content="http://localhost/static/curve-og.png"' in html
    assert 'content="1200"' in html and 'content="627"' in html and 'name="twitter:card" content="summary_large_image"' in html


def test_the_shipped_preview_image_is_1200_by_627():
    import struct
    png = (ROOT / "app" / "static" / "curve-og.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", png[16:24]) == (1200, 627)


def test_the_card_draws_the_same_dots_and_is_not_indexed():
    resp = client().get("/curve/card")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200 and resp.headers["X-Robots-Tag"] == "noindex"
    for climb in load_pack().curve["climbs"]:
        for sid in climb["skills"]:
            assert f'href="#skill-{sid}"' in html
    assert "ask-barry.onrender.com/curve" in html and "Raju Dandigam" in html


def test_the_card_is_404_without_data():
    assert client(cap=None).get("/curve/card").status_code == 404

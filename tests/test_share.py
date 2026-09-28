"""Stage 8f: share an evidence map on the spot. Signed links can't be altered; the short QR link redirects."""
import pytest

from app import create_app
from app.share import BadShareLink, pack, unpack
from tests.test_evidence_web import AD, SyncStore, fake_runner

REPORT = {"role_title": "Graduate Engineer", "counts": {"evidenced": 1}, "fallback": False, "dropped": [],
          "requirements": [{"requirement": "Docker", "kind": "must", "status": "evidenced",
                            "evidence": "Wall Inspector runs in Docker.", "notes": [],
                            "sources": ["https://github.com/BBSISK/wall_inspector/blob/abc/README.md#docker",
                                        "javascript:alert(1)"]}]}


def test_share_link_round_trips_and_rejects_any_change():
    token = pack(REPORT, "secret", now=1790000000)
    back = unpack(token, "secret")
    assert back["created"] == 1790000000 and back["report"]["requirements"][0]["requirement"] == "Docker"
    with pytest.raises(BadShareLink):
        unpack(token, "another-servers-secret")
    tampered = token[:-6] + ("A" if token[-6] != "A" else "B") + token[-5:]
    with pytest.raises(BadShareLink):
        unpack(tampered, "secret")
    for junk in ("", "!!!", "abc"):
        with pytest.raises(BadShareLink):
            unpack(junk, "secret")


def test_the_job_ad_is_not_in_the_link():
    report = dict(REPORT, ad_text="Contact jobs@example.com")          # extra fields are dropped
    assert "ad_text" not in unpack(pack(report, "s"), "s")["report"]


@pytest.fixture
def web():
    return create_app("testing", jobstore=SyncStore(runner=fake_runner)).test_client()


def finished_job(web):
    job_id = web.post("/api/evidence", json={"job_ad": AD}).get_json()["id"]
    return web.get(f"/api/evidence/{job_id}").get_json()


def test_finished_job_offers_share_links_and_a_qr(web):
    share = finished_job(web)["share"]
    assert "/evidence/shared/" in share["url"] and "/s/" in share["short"]
    assert share["qr"].startswith("data:image/svg+xml;base64,")
    assert len(share["short"]) < 80                                      # short enough for a scannable QR


def test_short_link_redirects_to_the_signed_link(web):
    share = finished_job(web)["share"]
    resp = web.get(share["short"].split("localhost")[-1])
    assert resp.status_code == 302 and "/evidence/shared/" in resp.headers["Location"]
    assert web.get("/s/not-a-job").status_code == 404


def test_shared_page_shows_the_map_with_disclaimers_and_only_github_links(web):
    token = pack(REPORT, create_app("testing").config["SECRET_KEY"])
    resp = web.get(f"/evidence/shared/{token}")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200 and "Evidence map: Graduate Engineer" in html
    assert "not an assessment of suitability" in html and "Listed on profile" in html
    assert "github.com/BBSISK/wall_inspector" in html and "javascript:" not in html
    assert 'name="robots" content="noindex"' in html


def test_altered_or_foreign_links_show_expired_not_content(web):
    resp = web.get("/evidence/shared/" + pack(REPORT, "someone-elses-key"))
    assert resp.status_code == 404 and "expired" in resp.get_data(as_text=True)
    assert "Wall Inspector runs in Docker" not in resp.get_data(as_text=True)


def test_blocked_reports_are_not_shareable():
    from app.job_agent import blocked_report
    web = create_app("testing", jobstore=SyncStore(
        runner=lambda text, on_call: (blocked_report("injection"), {}))).test_client()
    assert "share" not in finished_job(web)


def test_page_has_share_buttons(web):
    html = web.get("/evidence").get_data(as_text=True)
    for word in ("Share this evidence map", "wa.me", "mailto:", "Copy link", "navigator.share"):
        assert word in html

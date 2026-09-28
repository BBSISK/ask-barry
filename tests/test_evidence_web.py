"""Stage 8d: the job-ad evidence agent on the website (background job + polling), offline."""
import json
import threading
import time

import pytest

from app import create_app
from app.agent_jobs import JOB_TTL, Busy, JobStore
from app.job_agent import ToolLog, blocked_report, parse_report, verify

URL = "https://github.com/BBSISK/wall_inspector/blob/abc/README.md#docker"
AD = "Platform Engineer. Must: Docker, Kafka. Salary EUR 50k. Contact jobs@example.com"


def fake_runner(text, on_call):
    """Behaves like the real agent: two tool calls reported as they happen, then a verified report."""
    log = ToolLog()
    on_call(log.record("Has Barry used Docker?", json.dumps({"supported": True, "sources": [{"url": URL}],
                                                              "answer": "Wall Inspector runs in Docker."})))
    on_call(log.record("Has Barry used Kafka?", json.dumps({"supported": False, "sources": []})))
    rows = parse_report(json.dumps({"role_title": "Platform Engineer", "requirements": [
        {"requirement": "Docker", "status": "evidenced", "evidence": "Wall Inspector runs in Docker.", "sources": [URL]},
        {"requirement": "Kafka", "status": "not_documented"}]}))[1]
    return verify("Platform Engineer", rows, log), {}


class SyncStore(JobStore):
    """Runs the job before returning, so tests don't need to poll."""
    def start(self, job_ad, wait=True):
        return super().start(job_ad, wait=True)


@pytest.fixture
def web():
    return create_app("testing", jobstore=SyncStore(runner=fake_runner)).test_client()


def test_start_then_poll_returns_steps_and_a_verified_report(web):
    resp = web.post("/api/evidence", json={"job_ad": AD})
    assert resp.status_code == 202
    job = web.get(f"/api/evidence/{resp.get_json()['id']}").get_json()
    assert job["status"] == "done" and job["ai_generated"] is True
    assert [s["question"] for s in job["steps"]] == ["Has Barry used Docker?", "Has Barry used Kafka?"]
    assert [(r["requirement"], r["status"]) for r in job["report"]["requirements"]] == [
        ("Docker", "evidenced"), ("Kafka", "not_documented")]


def test_the_job_ad_is_never_returned_or_kept(web):
    job_id = web.post("/api/evidence", json={"job_ad": AD}).get_json()["id"]
    body = web.get(f"/api/evidence/{job_id}").get_data(as_text=True)
    assert "jobs@example.com" not in body and "EUR 50k" not in body


def test_bad_input_is_rejected(web):
    assert web.post("/api/evidence", json={"job_ad": "   "}).status_code == 400
    assert web.post("/api/evidence", json={"job_ad": "x" * 8001}).status_code == 400
    assert web.post("/api/evidence", data="not json").status_code == 400


def test_rate_limit_is_three_per_hour_per_visitor(web):
    codes = [web.post("/api/evidence", json={"job_ad": AD}).status_code for _ in range(4)]
    assert codes == [202, 202, 202, 429]
    assert "evidence maps" in web.post("/api/evidence", json={"job_ad": AD}).get_json()["error"]


def test_only_one_run_at_a_time():
    gate = threading.Event()

    def slow_runner(text, on_call):
        gate.wait(5)
        return fake_runner(text, on_call)

    store = JobStore(runner=slow_runner)
    client = create_app("testing", jobstore=store).test_client()
    first = client.post("/api/evidence", json={"job_ad": AD})
    second = client.post("/api/evidence", json={"job_ad": AD})
    assert first.status_code == 202 and second.status_code == 429
    assert "Another evidence map" in second.get_json()["error"]
    with pytest.raises(Busy):
        store.start(AD)
    gate.set()
    for _ in range(50):
        if client.get(f"/api/evidence/{first.get_json()['id']}").get_json()["status"] == "done":
            break
        time.sleep(0.05)
    assert client.get(f"/api/evidence/{first.get_json()['id']}").get_json()["status"] == "done"


def test_failures_are_hidden_from_the_browser():
    def broken(text, on_call):
        raise RuntimeError("secret internal detail")
    client = create_app("testing", jobstore=SyncStore(runner=broken)).test_client()
    job_id = client.post("/api/evidence", json={"job_ad": AD}).get_json()["id"]
    job = client.get(f"/api/evidence/{job_id}").get_json()
    assert job["status"] == "error" and "secret" not in json.dumps(job)


def test_blocked_ad_is_reported_not_crashed():
    client = create_app("testing", jobstore=SyncStore(
        runner=lambda text, on_call: (blocked_report("the ad contains text that looks like a prompt-injection attempt"), {}))
    ).test_client()
    job_id = client.post("/api/evidence", json={"job_ad": AD}).get_json()["id"]
    report = client.get(f"/api/evidence/{job_id}").get_json()["report"]
    assert report["blocked"] and report["requirements"] == []


def test_unknown_and_expired_jobs_are_404():
    now = [1000.0]
    store = SyncStore(runner=fake_runner, clock=lambda: now[0])
    client = create_app("testing", jobstore=store).test_client()
    assert client.get("/api/evidence/nope").status_code == 404
    job_id = client.post("/api/evidence", json={"job_ad": AD}).get_json()["id"]
    assert client.get(f"/api/evidence/{job_id}").status_code == 200
    now[0] += JOB_TTL + 1
    assert client.get(f"/api/evidence/{job_id}").status_code == 404


def test_not_offered_when_azure_is_not_configured(client):
    assert client.post("/api/evidence", json={"job_ad": AD}).status_code == 503
    assert b'id="ad-form"' not in client.get("/evidence").data
    assert client.get("/health").get_json()["features"]["job_agent"] is False
    assert b"/evidence" not in client.get("/").data


def test_page_renders_with_disclosures(web):
    html = web.get("/evidence").get_data(as_text=True)
    assert 'id="ad-form"' in html and "AI agent" in html and "never scores, ranks or judges fit" in html
    assert "textContent" in html and "innerHTML" not in html          # model output is never parsed as HTML
    assert web.get("/health").get_json()["features"]["job_agent"] is True


def test_render_runs_one_worker_so_jobs_stay_in_memory():
    text = open("render.yaml", encoding="utf-8").read()
    assert "--workers 1" in text and "--threads" in text and "AGENT_RATE_PER_HOUR" in text


def test_rate_limiter_forgets_ip_addresses_after_the_window():
    from app.ratelimit import RateLimiter
    now = [0.0]
    rl = RateLimiter(per_minute=3, per_day=20, clock=lambda: now[0], window=3600, noun="evidence maps")
    assert rl.allow("1.2.3.4")[0] and "1.2.3.4" in rl._hits
    now[0] += 3601
    rl.allow("5.6.7.8")
    assert "1.2.3.4" not in rl._hits


@pytest.mark.parametrize("path", ["/", "/evidence"])
def test_pages_have_link_preview_tags(web, path):
    html = web.get(path, base_url="https://ask-barry.example").get_data(as_text=True)
    for prop in ("og:title", "og:description", "og:image", "og:url"):
        assert f'property="{prop}"' in html
    assert 'content="https://ask-barry.example/static/og-image.png"' in html      # absolute URL, as LinkedIn needs
    image = web.get("/static/og-image.png")
    assert image.status_code == 200 and image.mimetype == "image/png"


def test_connect_page_lists_every_link_with_a_qr_code(web):
    from pathlib import Path

    from app.routes import CONNECT_SECTIONS
    resp = web.get("/connect")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200 and 'property="og:title"' in html
    cards = [c for s in CONNECT_SECTIONS for c in s["cards"]]
    assert len(cards) == 10
    for c in cards:
        assert f'href="{c["url"]}"' in html
        assert Path("app/static/qr", c["qr"] + ".png").is_file(), c["qr"]
    assert "linkedin.com/in/barry-s-50135113" in html and "/evidence" in html

"""ASK-27: fetch a job ad from a careers-page link. Offline: Firecrawl, DNS and robots.txt are all faked."""
import pytest

from app import create_app
from app.job_fetch import (AD_SCHEMA, FIRECRAWL_URL, FetchError, FirecrawlFetcher, check_url, clean_markdown,
                           compose, is_public, robots_allows)

AD_MARKDOWN = ("# Graduate Software Engineer\n\n![logo](https://x/logo.png)\n\nJoin our platform team in Dublin. "
               "You will build services in Python and Java, write SQL against PostgreSQL, and ship through "
               "GitHub Actions. [Apply now](https://example.com/apply)\n\n\n\nWe offer hybrid working and a "
               "learning budget. Closing date 31 October 2026.")
FIRECRAWL_OK = {"success": True, "data": {
    "markdown": AD_MARKDOWN,
    "json": {"is_job_ad": True, "title": "Graduate Software Engineer", "company": "Example Ltd",
             "location": "Dublin (hybrid)", "required_skills": ["Python", "Java", "SQL", "  "],
             "closing_date": "31 October 2026"},
    "metadata": {"statusCode": 200, "sourceURL": "https://jobs.example.com/123"}}}


def allow_all(url):
    return True


class FakePost:
    def __init__(self, status=200, body=FIRECRAWL_OK):
        self.status, self.body, self.calls = status, body, []

    def __call__(self, url, payload, headers, timeout=None):
        self.calls.append((url, payload, headers))
        return self.status, self.body


# --- the link ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url, name", [
    ("https://www.linkedin.com/jobs/view/12345", "LinkedIn"),
    ("ie.linkedin.com/jobs/view/1", "LinkedIn"),
    ("https://lnkd.in/abc", "LinkedIn"),
    ("https://ie.indeed.com/viewjob?jk=1", "Indeed"),
    ("https://www.glassdoor.ie/job-listing/x", "Glassdoor"),
])
def test_sites_whose_terms_forbid_scraping_are_refused_with_a_paste_hint(url, name):
    with pytest.raises(FetchError) as err:
        check_url(url)
    assert err.value.status == 422 and name in str(err.value) and "paste" in str(err.value)


@pytest.mark.parametrize("url", ["", "ftp://example.com/job", "https://127.0.0.1/job", "http://[::1]/x",
                                 "https://localhost/job", "https://intranet/job", "https://user:pw@example.com/",
                                 "https://svc.internal/job", "https://example.com/" + "a" * 2100])
def test_bad_links_are_refused(url):
    with pytest.raises(FetchError):
        check_url(url)


def test_a_bare_domain_gets_https_and_the_fragment_is_dropped():
    assert check_url("careers.example.com/jobs/1#apply") == ("https://careers.example.com/jobs/1", "careers.example.com")


def test_linkedin_lookalikes_are_not_blocked():
    assert check_url("https://notlinkedin.com/job")[1] == "notlinkedin.com"


def test_only_public_addresses_count():
    resolve = lambda ips: (lambda host, port: [(0, 0, 0, "", (ip, 0)) for ip in ips])    # noqa: E731
    assert is_public("x", resolve(["93.184.216.34"]))
    assert not is_public("x", resolve(["93.184.216.34", "10.0.0.5"]))              # one private address is enough
    assert not is_public("x", resolve(["169.254.169.254"]))                          # cloud metadata address
    assert not is_public("x", lambda h, p: (_ for _ in ()).throw(OSError("no such host")))


# --- robots.txt --------------------------------------------------------------------------------------------------

def robots_get(answers):
    """answers: url -> (status, headers, text)."""
    def get(url, timeout=None):
        return answers[url]
    return get


PUBLIC = lambda host: True                                                                  # noqa: E731


def test_robots_txt_that_disallows_the_page_is_respected():
    get = robots_get({"https://jobs.example.com/robots.txt": (200, {}, "User-agent: *\nDisallow: /jobs/\n")})
    with pytest.raises(FetchError, match="robots.txt") as err:
        robots_allows("https://jobs.example.com/jobs/1", get=get, public=PUBLIC)
    assert err.value.status == 422
    assert robots_allows("https://jobs.example.com/about", get=get, public=PUBLIC)


def test_robots_txt_naming_ask_barry_is_respected():
    text = "User-agent: AskBarryBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
    get = robots_get({"https://jobs.example.com/robots.txt": (200, {}, text)})
    with pytest.raises(FetchError):
        robots_allows("https://jobs.example.com/jobs/1", get=get, public=PUBLIC)


def test_no_robots_txt_allows_and_a_forbidden_one_does_not():
    assert robots_allows("https://a.example/j", get=robots_get({"https://a.example/robots.txt": (404, {}, "")}),
                         public=PUBLIC)
    with pytest.raises(FetchError):
        robots_allows("https://a.example/j", get=robots_get({"https://a.example/robots.txt": (403, {}, "")}),
                      public=PUBLIC)
    with pytest.raises(FetchError) as err:
        robots_allows("https://a.example/j", get=robots_get({"https://a.example/robots.txt": (503, {}, "")}),
                      public=PUBLIC)
    assert err.value.status == 502


def test_a_robots_redirect_to_a_private_address_is_not_followed():
    get = robots_get({"https://a.example/robots.txt": (301, {"Location": "http://internal.example/robots.txt"}, "")})
    public = lambda host: host == "a.example"                                               # noqa: E731
    with pytest.raises(FetchError, match="public internet"):
        robots_allows("https://a.example/j", get=get, public=public)


def test_a_robots_redirect_to_www_is_followed():
    get = robots_get({"https://a.example/robots.txt": (301, {"Location": "https://www.a.example/robots.txt"}, ""),
                      "https://www.a.example/robots.txt": (200, {}, "User-agent: *\nDisallow: /private\n")})
    assert robots_allows("https://a.example/jobs/1", get=get, public=PUBLIC)


# --- Firecrawl ---------------------------------------------------------------------------------------------------

def test_firecrawl_gets_the_schema_and_the_key_only_in_the_header():
    post = FakePost()
    ad = FirecrawlFetcher("fc-test-key", post=post, robots=allow_all).fetch("jobs.example.com/123")
    url, payload, headers = post.calls[0]
    assert url == FIRECRAWL_URL and headers == {"Authorization": "Bearer fc-test-key"}
    assert payload["url"] == "https://jobs.example.com/123" and payload["onlyMainContent"] is True
    assert payload["formats"] == ["markdown", {"type": "json", "schema": AD_SCHEMA}]
    assert "fc-test-key" not in str(payload) and "fc-test-key" not in str(ad)
    assert ad["title"] == "Graduate Software Engineer" and ad["company"] == "Example Ltd"
    assert ad["required_skills"] == ["Python", "Java", "SQL"] and ad["host"] == "jobs.example.com"
    assert ad["text"].startswith("Job title: Graduate Software Engineer\nCompany: Example Ltd")
    assert "logo.png" not in ad["text"] and "Apply now" in ad["text"] and "](" not in ad["text"]


def test_robots_is_checked_before_firecrawl_is_called():
    post = FakePost()

    def refuse(url):
        raise FetchError("no", 422)
    with pytest.raises(FetchError):
        FirecrawlFetcher("k", post=post, robots=refuse).fetch("https://jobs.example.com/1")
    assert post.calls == []


@pytest.mark.parametrize("status, body, words, code", [
    (402, {"success": False}, "free allowance", 503),
    (429, {"success": False}, "busy", 503),
    (500, {"success": False}, "Couldn't fetch", 502),
    (200, {"success": True, "data": {**FIRECRAWL_OK["data"], "metadata": {"statusCode": 404}}}, "closed", 422),
    (200, {"success": True, "data": {**FIRECRAWL_OK["data"], "json": {"is_job_ad": False, "title": ""}}},
     "single job ad", 422),
    (200, {"success": True, "data": {**FIRECRAWL_OK["data"], "markdown": "Jobs: see below"}}, "single job ad", 422),
])
def test_firecrawl_problems_become_plain_messages(status, body, words, code):
    with pytest.raises(FetchError, match=words) as err:
        FirecrawlFetcher("k", post=FakePost(status, body), robots=allow_all).fetch("https://jobs.example.com/1")
    assert err.value.status == code


def test_a_long_ad_is_shortened_to_fit_the_box():
    text = compose({"title": "T"}, "word " * 5000, 8000)
    assert len(text) <= 8000 and text.endswith("[ad shortened to fit]")


def test_markdown_cleaning():
    assert clean_markdown("a ![x](y) [b](c)\n\n\n\nd") == "a  b\n\nd"


def test_no_key_means_no_fetcher(monkeypatch):
    from app.job_fetch import fetcher_from_env
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    assert fetcher_from_env() is None
    with pytest.raises(ValueError):
        FirecrawlFetcher("")


# --- the route and the page ------------------------------------------------------------------------------------

class FakeFetcher:
    def __init__(self, error=None):
        self.error, self.calls = error, []

    def fetch(self, url):
        self.calls.append(url)
        if self.error:
            raise self.error
        return {"title": "Graduate Software Engineer", "company": "Example Ltd", "location": "Dublin",
                "closing_date": "", "required_skills": ["Python"], "text": "Job title: Graduate Software Engineer\n\n…",
                "source_url": url, "host": "jobs.example.com"}


def client(fetcher=None, **config):
    from tests.test_evidence_web import SyncStore, fake_runner
    app = create_app("testing", jobstore=SyncStore(runner=fake_runner), ad_fetcher=fetcher)
    app.config.update(config)
    return app.test_client()


def test_fetch_returns_the_text_for_the_visitor_to_check():
    fetcher = FakeFetcher()
    resp = client(fetcher).post("/api/fetch-ad", json={"url": "https://jobs.example.com/1"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["title"] == "Graduate Software Engineer" and body["ai_generated"] is True and body["text"]


def test_linkedin_is_refused_before_any_fetch_or_allowance_is_used():
    fetcher = FakeFetcher()
    web = client(fetcher)
    resp = web.post("/api/fetch-ad", json={"url": "https://www.linkedin.com/jobs/view/1"})
    assert resp.status_code == 422 and "LinkedIn" in resp.get_json()["error"] and fetcher.calls == []
    assert web.application.extensions["fetch_budget"]._hits == {}


def test_fetch_errors_pass_through_with_their_status():
    resp = client(FakeFetcher(FetchError("robots says no", 422))).post("/api/fetch-ad", json={"url": "a.example/j"})
    assert resp.status_code == 422 and resp.get_json()["error"] == "robots says no"


def test_unexpected_errors_are_hidden():
    resp = client(FakeFetcher(RuntimeError("secret detail"))).post("/api/fetch-ad", json={"url": "a.example/j"})
    assert resp.status_code == 502 and "secret detail" not in resp.get_data(as_text=True)


def test_not_offered_without_a_key():
    web = client(None)
    assert web.post("/api/fetch-ad", json={"url": "https://a.example/j"}).status_code == 503
    assert 'id="ad-url"' not in web.get("/evidence").get_data(as_text=True)
    assert web.get("/health").get_json()["features"]["job_url"] is False


def test_offered_with_a_key():
    web = client(FakeFetcher())
    html = web.get("/evidence").get_data(as_text=True)
    assert 'id="ad-url"' in html and "/api/fetch-ad" in html and "innerHTML" not in html
    assert web.get("/health").get_json()["features"]["job_url"] is True


def test_the_shared_daily_budget_protects_the_free_allowance():
    from app.ratelimit import RateLimiter
    web = client(FakeFetcher())
    web.application.extensions["fetch_budget"] = RateLimiter(per_minute=2, per_day=2, window=3600, noun="x")
    codes = [web.post("/api/fetch-ad", json={"url": "https://a.example/j"},
                      environ_base={"REMOTE_ADDR": f"10.0.0.{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]


def test_render_keeps_the_key_out_of_the_blueprint():
    text = open("render.yaml", encoding="utf-8").read()
    block = text.split("key: FIRECRAWL_API_KEY", 1)[1].split("- key:", 1)[0]
    assert "sync: false" in block and "value:" not in block


# --- real careers pages, replayed offline (saved with python -m scripts.try_fetch URL --save ...) -------------------

from pathlib import Path  # noqa: E402
import json  # noqa: E402

FIXTURES = sorted((Path(__file__).parent / "fixtures" / "firecrawl").glob("*.json"))


@pytest.mark.skipif(not FIXTURES, reason="no saved careers pages yet (ASK-29)")
@pytest.mark.parametrize("path", FIXTURES, ids=[p.stem for p in FIXTURES])
def test_saved_careers_pages_still_give_a_checkable_ad(path):
    case = json.loads(path.read_text(encoding="utf-8"))
    ad = FirecrawlFetcher("k", post=FakePost(case["status"], case["response"]), robots=allow_all).fetch(case["url"])
    assert ad["title"] and len(ad["text"]) >= 200 and ad["text"].startswith("Job title:")

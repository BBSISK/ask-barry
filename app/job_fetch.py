"""Fetch a job ad from a careers-page link (ASK-27), for the visitor to check before running the agent.

Same shape as "Scan a job ad": the link becomes text in the box, and the visitor reads it before anything
else happens. Fetching is a fixed step in code, not a tool the AI agent can call, so nothing the model reads
can make the server fetch a URL.

Policy, in order:
  1. Only http(s) links to a named public host. IP addresses, localhost, and links with a username are refused.
  2. Sites whose terms forbid automated fetching (LinkedIn, Indeed, Glassdoor) are refused with a clear message.
  3. The site's robots.txt must allow it. It's read from this server, so every hop is checked to be a public
     address first (no reaching the server's own network through a redirect).
  4. Firecrawl (https://firecrawl.dev, REST v2) fetches the page and returns the main content as markdown plus a
     few fields extracted against a fixed JSON schema. The page content is untrusted: it only fills the text box.

The Firecrawl key is a secret: FIRECRAWL_API_KEY in the environment (Render dashboard, local .env), never in code.
Only the Python standard library is used, so the fetch adds no dependencies.
"""
import ipaddress
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from urllib.robotparser import RobotFileParser

FIRECRAWL_URL = "https://api.firecrawl.dev/v2/scrape"
USER_AGENT = "AskBarryBot/1.0 (+https://ask-barry.onrender.com)"
MAX_URL = 2000
MAX_SKILLS = 30
TIMEOUT = 45                      # seconds for Firecrawl; it renders the page, which can take a while
ROBOTS_TIMEOUT = 6

# Domain -> name. Their terms don't allow automated fetching, so the visitor is asked to paste the text.
BLOCKED = {"linkedin.com": "LinkedIn", "lnkd.in": "LinkedIn", "indeed.com": "Indeed", "glassdoor.com": "Glassdoor",
           "glassdoor.ie": "Glassdoor", "glassdoor.co.uk": "Glassdoor"}

# What Firecrawl's extraction must return. Kept small: the full text comes from the markdown.
AD_SCHEMA = {
    "type": "object",
    "properties": {
        "is_job_ad": {"type": "boolean", "description": "true only if the page is a single job advertisement"},
        "title": {"type": "string", "description": "the job title"},
        "company": {"type": "string", "description": "the hiring company"},
        "location": {"type": "string", "description": "work location, including remote or hybrid if stated"},
        "required_skills": {"type": "array", "items": {"type": "string"},
                            "description": "skills, tools and qualifications the ad asks for, as written"},
        "closing_date": {"type": "string", "description": "application closing date as written, or empty"},
    },
    "required": ["is_job_ad", "title"],
}


class FetchError(Exception):
    """A user-facing reason the link can't be used. status is the HTTP status the API should return."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# --- 1 and 2: the link itself ------------------------------------------------------------------------------------

def blocked_site(host):
    host = host.lower().rstrip(".")
    for domain, name in BLOCKED.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def check_url(url):
    """-> (normalised url, host), or FetchError saying what's wrong with the link."""
    url = str(url or "").strip()
    if not url:
        raise FetchError("Please paste a link to the job ad.")
    if len(url) > MAX_URL:
        raise FetchError("That link is too long.")
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    parts = urllib.parse.urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host:
        raise FetchError("That doesn't look like a web link.")
    if parts.username or parts.password:
        raise FetchError("Links with a username or password aren't accepted.")
    try:
        ipaddress.ip_address(host)
        raise FetchError("Please use the careers page's address, not an IP address.")
    except ValueError:
        pass
    if "." not in host or host.endswith((".local", ".internal", ".localhost")) or host == "localhost":
        raise FetchError("That isn't a public website.")
    name = blocked_site(host)
    if name:
        raise FetchError(f"{name}'s terms don't allow automated fetching, so Ask Barry won't fetch it. "
                         f"Please copy the ad text from {name} and paste it into the box instead.", 422)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path or "/", parts.query, "")), host


def is_public(host, resolve=socket.getaddrinfo):
    """True only if every address the host resolves to is a public internet address."""
    try:
        infos = resolve(host, None)
    except (OSError, UnicodeError):
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(ipaddress.ip_address(a.split("%")[0]).is_global for a in addresses)


# --- 3: robots.txt ---------------------------------------------------------------------------------------------

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None                                   # redirects are followed by hand, each hop checked


def _get(url, timeout=ROBOTS_TIMEOUT):
    """GET without following redirects -> (status, headers, text)."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.headers, resp.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, err.headers, ""


def robots_allows(url, get=_get, public=is_public, hops=3):
    """Read the site's robots.txt (following up to 3 redirects, each to a public host) and check the link."""
    parts = urllib.parse.urlsplit(url)
    robots = f"{parts.scheme}://{parts.netloc}/robots.txt"
    for _ in range(hops + 1):
        host = urllib.parse.urlsplit(robots).hostname or ""
        if not public(host):
            raise FetchError("That site isn't on the public internet, so it can't be fetched.")
        try:
            status, headers, text = get(robots)
        except (OSError, ValueError):
            raise FetchError("Couldn't reach that site to check whether it allows fetching. "
                             "Please paste the ad text instead.", 502) from None
        if status in (301, 302, 303, 307, 308) and headers and headers.get("Location"):
            robots = urllib.parse.urljoin(robots, headers["Location"])
            continue
        break
    else:
        raise FetchError("That site redirects too many times. Please paste the ad text instead.", 502)
    if status in (401, 403):
        allowed = False                               # the standard reading: an unreadable robots.txt allows nothing
    elif 400 <= status < 500:
        allowed = True                                # no robots.txt: no restrictions
    elif status >= 500 or status < 200:
        raise FetchError("That site didn't answer properly, so Ask Barry can't check it allows fetching. "
                         "Please paste the ad text instead.", 502)
    else:
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        allowed = parser.can_fetch(USER_AGENT, url) and parser.can_fetch("*", url)
    if not allowed:
        raise FetchError("That site's robots.txt asks automated tools not to fetch this page, so Ask Barry won't. "
                         "Please copy the ad text and paste it instead.", 422)
    return True


# --- 4: Firecrawl ----------------------------------------------------------------------------------------------

def _post_json(url, payload, headers, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        try:
            return err.code, json.loads(err.read().decode("utf-8"))
        except ValueError:
            return err.code, {}


def clean_markdown(text):
    """Page markdown -> plain ad text: images out, links reduced to their words, blank runs squeezed."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text or "")
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _short(value, limit=200):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def compose(fields, body, max_chars):
    """The text that goes into the box: a short header from the extracted fields, then the ad itself."""
    header = [f"{label}: {fields[key]}" for key, label in
              (("title", "Job title"), ("company", "Company"), ("location", "Location"),
               ("closing_date", "Closing date")) if fields.get(key)]
    head = "\n".join(header)
    room = max_chars - len(head) - 2
    if len(body) > room:
        body = body[:max(0, room - 40)].rstrip() + "\n\n[ad shortened to fit]"
    return (head + "\n\n" + body).strip() if head else body[:max_chars]


class FirecrawlFetcher:
    """url -> {title, company, location, required_skills, closing_date, text, source_url, host}."""

    def __init__(self, api_key, post=_post_json, robots=robots_allows, max_chars=8000):
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY is not set")
        self.api_key, self.post, self.robots, self.max_chars = api_key, post, robots, max_chars

    def request_body(self, url):
        return {"url": url, "formats": ["markdown", {"type": "json", "schema": AD_SCHEMA}],
                "onlyMainContent": True, "blockAds": True, "timeout": TIMEOUT * 1000 - 5000}

    def fetch(self, url):
        url, host = check_url(url)
        self.robots(url)
        try:
            status, body = self.post(FIRECRAWL_URL, self.request_body(url),
                                     {"Authorization": f"Bearer {self.api_key}"})
        except (OSError, ValueError):
            raise FetchError("The page fetcher didn't respond. Please try again, or paste the ad text.", 502) from None
        if status == 402:
            raise FetchError("Fetching links is paused for this month (the free allowance is used up). "
                             "Please paste the ad text instead.", 503)
        if status == 429:
            raise FetchError("The page fetcher is busy. Please try again in a minute, or paste the ad text.", 503)
        data = (body or {}).get("data") or {}
        if status != 200 or not body.get("success", True) or not data:
            raise FetchError("Couldn't fetch that page. Please check the link, or paste the ad text instead.", 502)
        page_status = (data.get("metadata") or {}).get("statusCode")
        if isinstance(page_status, int) and page_status >= 400:
            raise FetchError(f"The careers page answered with an error ({page_status}). The ad may have closed.", 422)
        fields = data.get("json") or {}
        text = clean_markdown(data.get("markdown"))
        if not fields.get("is_job_ad") or len(text) < 200:
            raise FetchError("That page doesn't look like a single job ad. Please open the ad itself and use its "
                             "link, or paste the text.", 422)
        result = {key: _short(fields.get(key)) for key in ("title", "company", "location", "closing_date")}
        skills = fields.get("required_skills") if isinstance(fields.get("required_skills"), list) else []
        result["required_skills"] = [s for s in (_short(x, 80) for x in skills) if s][:MAX_SKILLS]
        result.update(text=compose(result, text, self.max_chars), source_url=url, host=host)
        return result


def fetcher_from_env(max_chars=8000):
    key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    return FirecrawlFetcher(key, max_chars=max_chars) if key else None

"""HTTP routes: the question page, the answer API, the job-ad evidence agent, health and readiness checks."""
import concurrent.futures
import logging
import os
import time

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for

from .agent_jobs import Busy
from .answering import answerer_from_env, azure_configured, validate_question
from .job_agent import MAX_JOB_AD_CHARS
from .scan import ScanError, transcriber_from_env
from .share import BadShareLink, pack, qr_data_uri, unpack

bp = Blueprint("main", __name__)


@bp.app_template_test("github_link")
def is_github_link(url):
    """Shared evidence maps only ever link to github.com (the sources the agent verified)."""
    return isinstance(url, str) and url.startswith("https://github.com/")
log = logging.getLogger(__name__)


def get_search_client():
    """Azure AI Search client: injected (tests), from answerer, or from environment."""
    client = current_app.extensions.get("search_client")
    if client is not None:
        return client
    answerer = current_app.extensions.get("answerer")
    if answerer is not None and hasattr(answerer, "retriever"):
        retriever_client = getattr(answerer.retriever, "client", None)
        if retriever_client is not None:
            return retriever_client
    if current_app.config["ANSWERING_FROM_ENV"] and azure_configured():
        from .azure_search import search_client_from_env
        client = search_client_from_env()
        current_app.extensions["search_client"] = client
        return client
    return None


def get_model_provider():
    """Default model provider: injected (tests), from answerer, or from environment."""
    provider = current_app.extensions.get("model_provider")
    if provider is not None:
        return provider
    answerer = current_app.extensions.get("answerer")
    if answerer is not None and hasattr(answerer, "provider"):
        return answerer.provider
    if current_app.config["ANSWERING_FROM_ENV"] and azure_configured():
        from .answering import azure_chat_client
        from .providers import AzureOpenAIProvider
        provider = AzureOpenAIProvider(azure_chat_client(), os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"])
        current_app.extensions["model_provider"] = provider
        return provider
    return None


def get_answerer():
    """The configured Answerer, built lazily from AZURE_* settings; None if unavailable."""
    answerer = current_app.extensions.get("answerer")
    if answerer is None and current_app.config["ANSWERING_FROM_ENV"] and azure_configured():
        answerer = answerer_from_env()
        current_app.extensions["answerer"] = answerer
    return answerer


def answering_available():
    if current_app.extensions.get("answerer") is not None:
        return True
    return current_app.config["ANSWERING_FROM_ENV"] and azure_configured()


def agent_available():
    store = current_app.extensions["jobstore"]
    if not getattr(store, "from_env", False):
        return True
    return current_app.config["ANSWERING_FROM_ENV"] and azure_configured()


@bp.get("/")
def index():
    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
        available=answering_available(),
        agent_available=agent_available(),
    )


@bp.get("/evidence")
def evidence_page():
    return render_template(
        "evidence.html",
        app_name=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
        available=agent_available(),
        max_chars=MAX_JOB_AD_CHARS,
        per_hour=current_app.config["AGENT_RATE_PER_HOUR"],
    )


CONNECT_SECTIONS = [
    {"title": "Start here", "cards": [
        {"title": "Paste a job ad", "text": "My AI agent maps each requirement to evidence in my project docs, with links",
         "url": "/evidence", "qr": "evidence", "primary": True},
        {"title": "Ask me anything", "text": "Ask Barry answers questions about my work, citing its sources",
         "url": "/", "qr": "askbarry"},
    ]},
    {"title": "Profiles", "cards": [
        {"title": "LinkedIn", "text": "linkedin.com/in/barry-s-50135113",
         "url": "https://www.linkedin.com/in/barry-s-50135113/", "qr": "linkedin"},
        {"title": "GitHub", "text": "github.com/BBSISK: code and documentation",
         "url": "https://github.com/BBSISK", "qr": "github"},
        {"title": "Career history", "text": "30 years at Intel, teaching, and the HDip",
         "url": "https://github.com/BBSISK/BBSISK/blob/main/career.md", "qr": "career"},
    ]},
    {"title": "What I've built", "cards": [
        {"title": "Ask Barry", "text": "Live RAG assistant (Azure OpenAI + AI Search) with an evaluated job-ad agent",
         "url": "/", "qr": "askbarry"},
        {"title": "Wall Inspector", "text": "Masonry skills assessment with AI agents and human-in-the-loop provenance",
         "url": "https://wall-inspector.onrender.com", "qr": "wall-inspector"},
        {"title": "In My Time", "text": "Privacy-first family-history service over WhatsApp",
         "url": "https://www.inmytime.app", "qr": "inmytime"},
        {"title": "AgentMath", "text": "Adaptive maths practice, 3,000+ items",
         "url": "https://www.agentmath.app", "qr": "agentmath"},
        {"title": "Brief", "text": "A 30-words-a-week journal by WhatsApp and email",
         "url": "https://www.my30words.com", "qr": "brief"},
    ]},
]


@bp.get("/connect")
def connect():
    """One landing page for printed material (e.g. the careers-fair sheet): every link, one QR code."""
    return render_template("connect.html", sections=CONNECT_SECTIONS)


@bp.post("/api/evidence")
def start_evidence():
    """Start the job-ad evidence agent. Returns 202 + a job id; poll GET /api/evidence/<id>."""
    payload = request.get_json(silent=True) or {}
    job_ad = payload.get("job_ad")
    if not isinstance(job_ad, str) or not job_ad.strip():
        return jsonify(error="Please paste a job advertisement."), 400
    if len(job_ad) > MAX_JOB_AD_CHARS:
        return jsonify(error=f"That's too long: please paste at most {MAX_JOB_AD_CHARS} characters."), 400
    if not agent_available():
        return jsonify(error="The evidence agent is not configured on this server."), 503
    store = current_app.extensions["jobstore"]
    if store.running():
        return jsonify(error="Another evidence map is being prepared. Please try again in a minute."), 429
    allowed, reason = current_app.extensions["agent_ratelimiter"].allow(request.remote_addr or "unknown")
    if not allowed:
        return jsonify(error=reason), 429
    try:
        job = store.start(job_ad)
    except ValueError as err:
        return jsonify(error=str(err)), 400
    except Busy as err:
        return jsonify(error=str(err)), 429
    # The ad text is deliberately not logged or stored (it may be a third party's).
    log.info("evidence map started (ad length %d)", len(job_ad))
    return jsonify(id=job.id, status=job.status), 202


def get_transcriber():
    """Photo -> text for "Scan a job ad": the injected one (tests) or Azure, when configured."""
    fn = current_app.extensions.get("transcriber")
    if fn is None and current_app.config["ANSWERING_FROM_ENV"] and azure_configured():
        fn = transcriber_from_env()
        current_app.extensions["transcriber"] = fn
    return fn


@bp.post("/api/scan")
def scan_job_ad():
    """A photo of a job ad -> its text, for the visitor to check before running the agent.
    The photo is never stored or logged."""
    upload = request.files.get("image")
    if upload is None:
        return jsonify(error="No photo received. Please try again."), 400
    transcriber = get_transcriber()
    if transcriber is None:
        return jsonify(error="Scanning is not configured on this server."), 503
    allowed, reason = current_app.extensions["scan_ratelimiter"].allow(request.remote_addr or "unknown")
    if not allowed:
        return jsonify(error=reason), 429
    data = upload.read()
    try:
        text = transcriber(data)
    except ScanError as err:
        return jsonify(error=str(err)), 400
    except Exception:
        log.exception("scan failed (photo size %d bytes)", len(data))
        return jsonify(error="Sorry, something went wrong reading that photo. Please try again."), 502
    log.info("scanned a job ad (photo %d bytes, text %d chars)", len(data), len(text))
    return jsonify(text=text, ai_generated=True)


@bp.errorhandler(413)
def too_large(_err):
    return jsonify(error="That photo is too large. Please try again, closer to the text."), 413


@bp.get("/api/evidence/<job_id>")
def evidence_status(job_id):
    job = current_app.extensions["jobstore"].get(job_id)
    if job is None:
        return jsonify(error="Unknown or expired job."), 404
    data = job.to_dict()
    if job.status == "done" and job.report and not job.report.get("blocked"):
        short = url_for("main.short_share", job_id=job.id, _external=True)
        data["share"] = {"url": url_for("main.shared_map", token=share_token(job), _external=True),
                         "short": short, "qr": qr_data_uri(short)}
    return jsonify(data)


def share_token(job):
    return pack(job.report, current_app.config["SECRET_KEY"], now=job.finished)


@bp.get("/s/<job_id>")
def short_share(job_id):
    """The on-screen QR link: short enough to scan, redirects to the durable signed link."""
    job = current_app.extensions["jobstore"].get(job_id)
    if job is None or job.status != "done" or not job.report or job.report.get("blocked"):
        return render_template("shared.html", app_name=current_app.config["APP_NAME"], expired=True), 404
    return redirect(url_for("main.shared_map", token=share_token(job)), code=302)


@bp.get("/evidence/shared/<token>")
def shared_map(token):
    """A shared evidence map, read-only. Only shown if the signature proves this server produced it."""
    try:
        shared = unpack(token, current_app.config["SECRET_KEY"])
    except BadShareLink:
        return render_template("shared.html", app_name=current_app.config["APP_NAME"], expired=True), 404
    from datetime import datetime, timezone
    created = datetime.fromtimestamp(shared["created"], tz=timezone.utc).strftime("%-d %B %Y")
    return render_template("shared.html", app_name=current_app.config["APP_NAME"], expired=False,
                           report=shared["report"], created=created)


@bp.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    try:
        question = validate_question(payload.get("question"))
    except ValueError as err:
        return jsonify(error=str(err)), 400

    answerer = get_answerer()
    if answerer is None:
        return jsonify(error="Answering is not configured on this server."), 503

    allowed, reason = current_app.extensions["ratelimiter"].allow(request.remote_addr or "unknown")
    if not allowed:
        return jsonify(error=reason), 429

    try:
        answer = answerer.ask(question)
    except Exception:                                    # never leak internals to the browser
        log.exception("answering failed (question length %d)", len(question))
        return jsonify(error="Sorry, something went wrong answering that. Please try again."), 502
    # Question text is deliberately not logged (privacy); only outcome and size.
    log.info("answered: supported=%s sources=%d chars=%d", answer.supported, len(answer.sources), len(question))
    return jsonify(answer.to_dict())


@bp.get("/health")
def health():
    """Used by Render's health check and by CI. Reports honestly what is live."""
    live = bool(answering_available())
    return jsonify(
        status="ok",
        app=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
        features={"search": live, "embeddings": live, "generation": live, "job_agent": bool(agent_available())},
        retrieval="azure-hybrid" if live else None,
    )


READY_TIMEOUT = 3.0
READY_PING_MESSAGES = [
    {"role": "system", "content": 'Reply with a JSON object only: {"ok": true}'},
    {"role": "user", "content": "ping"},
]


def check_search_live(client, timeout=READY_TIMEOUT):
    if client is None:
        raise RuntimeError("search client not configured")
    if hasattr(client, "search") and callable(client.search):
        try:
            hits = client.search(search_text="*", top=1, select=["id"], connection_timeout=timeout, read_timeout=timeout)
        except TypeError:
            try:
                hits = client.search(search_text="*", top=1, select=["id"])
            except TypeError:
                hits = client.search(search_text="*")
        if hasattr(hits, "__iter__"):
            next(iter(hits), None)
        return
    if hasattr(client, "get_document_count") and callable(client.get_document_count):
        try:
            client.get_document_count(connection_timeout=timeout, read_timeout=timeout)
        except TypeError:
            client.get_document_count()
        return
    raise RuntimeError("search client has no search or get_document_count method")


def check_provider_live(provider, timeout=READY_TIMEOUT):
    if provider is None:
        raise RuntimeError("model provider not configured")
    if hasattr(provider, "generate") and callable(provider.generate):
        try:
            provider.generate(READY_PING_MESSAGES, max_tokens=16)
        except TypeError:
            provider.generate(READY_PING_MESSAGES)
        return
    if hasattr(provider, "chat") and hasattr(provider.chat, "completions"):
        model = getattr(provider, "model", None) or os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini")
        try:
            provider.chat.completions.create(
                model=model,
                messages=READY_PING_MESSAGES,
                max_completion_tokens=16,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
        except TypeError:
            try:
                provider.chat.completions.create(
                    model=model,
                    messages=READY_PING_MESSAGES,
                    max_completion_tokens=16,
                )
            except TypeError:
                provider.chat.completions.create(
                    model=model,
                    messages=READY_PING_MESSAGES,
                )
        return
    if callable(provider):
        try:
            provider(READY_PING_MESSAGES)
        except TypeError:
            provider()
        return
    raise RuntimeError("model provider has no generate or chat method")


@bp.get("/ready")
def ready():
    """Readiness probe: makes cheap live calls to Azure AI Search and the default model provider."""
    search_client = get_search_client()
    provider = get_model_provider()

    timeout = current_app.config.get("READY_TIMEOUT", READY_TIMEOUT)
    failed = []

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        search_future = executor.submit(check_search_live, search_client, timeout)
        provider_future = executor.submit(check_provider_live, provider, timeout)

        try:
            search_future.result(timeout=timeout)
        except Exception:
            log.warning("readiness check failed for search", exc_info=True)
            failed.append("search")

        remaining = max(0.1, timeout - (time.monotonic() - start))
        try:
            provider_future.result(timeout=remaining)
        except Exception:
            log.warning("readiness check failed for model provider", exc_info=True)
            failed.append("provider")

    if failed:
        return jsonify(
            status="unavailable",
            ready=False,
            failed=failed,
            error=f"Dependency check failed: {', '.join(failed)}",
        ), 503

    return jsonify(
        status="ready",
        ready=True,
        checks={"search": "ok", "provider": "ok"},
    ), 200

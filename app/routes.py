"""HTTP routes: the question page, the answer API, the job-ad evidence agent and the health check."""
import logging

from flask import Blueprint, current_app, jsonify, render_template, request

from .agent_jobs import Busy
from .answering import answerer_from_env, azure_configured, validate_question
from .job_agent import MAX_JOB_AD_CHARS

bp = Blueprint("main", __name__)
log = logging.getLogger(__name__)


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


@bp.get("/api/evidence/<job_id>")
def evidence_status(job_id):
    job = current_app.extensions["jobstore"].get(job_id)
    if job is None:
        return jsonify(error="Unknown or expired job."), 404
    return jsonify(job.to_dict())


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

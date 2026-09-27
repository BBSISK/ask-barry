"""HTTP routes: the question page, the answer API and the health check."""
import logging

from flask import Blueprint, current_app, jsonify, render_template, request

from .answering import answerer_from_env, azure_configured, validate_question

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


@bp.get("/")
def index():
    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
        available=answering_available(),
    )


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
        features={"search": live, "embeddings": live, "generation": live},
        retrieval="azure-hybrid" if live else None,
    )

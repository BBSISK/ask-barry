"""Ask Barry: Flask application factory."""
import os

from flask import Flask

from .config import CONFIGS
from .ratelimit import RateLimiter


def create_app(config_name=None, answerer=None, jobstore=None, transcriber=None,
               search_client=None, model_provider=None, chat_client=None, capability_store=None):
    """Create and configure the Flask app.

    config_name: "development", "testing" or "production". Defaults to the
    APP_ENV environment variable, then "production" (safest default).
    answerer: optional Answerer to use (tests pass a fake). If omitted, the
    real Azure-backed one is built on first use when the AZURE_* settings exist.
    jobstore: optional JobStore for the job-ad agent (tests pass one with a fake runner).
    transcriber: optional photo -> text function for "Scan a job ad" (tests pass a fake).
    search_client: optional Azure AI Search client (tests pass a fake).
    model_provider: optional model provider or chat client for the answering step (tests pass a fake).
    chat_client: optional alias for model_provider when passing a raw chat completions client.
    capability_store: optional CapabilityStore for /capability (tests pass one over a fixture file).
    """
    config_name = config_name or os.getenv("APP_ENV", "production")
    if config_name not in CONFIGS:
        raise ValueError(f"Unknown config '{config_name}'. Use one of {sorted(CONFIGS)}.")

    app = Flask(__name__)
    app.config.from_object(CONFIGS[config_name])

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is not set. Add it as an environment variable "
            "(Render dashboard, or your local .env). It is never committed."
        )

    if app.config.get("BEHIND_PROXY"):
        # Render terminates HTTPS and forwards the client IP in X-Forwarded-For.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    app.extensions["answerer"] = answerer
    if jobstore is None:
        from .agent_jobs import JobStore
        jobstore = JobStore()
        jobstore.from_env = True               # the real agent: only offered when Azure is configured
    app.extensions["jobstore"] = jobstore
    app.extensions["transcriber"] = transcriber
    app.extensions["search_client"] = search_client
    app.extensions["model_provider"] = model_provider or chat_client
    app.extensions["scan_ratelimiter"] = RateLimiter(
        per_minute=app.config["SCAN_RATE_PER_HOUR"], per_day=app.config["SCAN_RATE_PER_DAY"],
        window=3600, noun="photo scans")
    app.extensions["agent_ratelimiter"] = RateLimiter(
        per_minute=app.config["AGENT_RATE_PER_HOUR"], per_day=app.config["AGENT_RATE_PER_DAY"],
        window=3600, noun="evidence maps")
    if capability_store is None:
        from .capability.store import CapabilityStore
        capability_store = CapabilityStore(app.config.get("CAPABILITY_SOURCE"))
    app.extensions["capability"] = capability_store
    app.extensions["ratelimiter"] = RateLimiter(
        per_minute=app.config["RATE_LIMIT_PER_MINUTE"], per_day=app.config["RATE_LIMIT_PER_DAY"]
    )

    from .routes import bp
    app.register_blueprint(bp)

    return app

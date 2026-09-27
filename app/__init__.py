"""Ask Barry: Flask application factory."""
import os

from flask import Flask

from .config import CONFIGS
from .ratelimit import RateLimiter


def create_app(config_name=None, answerer=None):
    """Create and configure the Flask app.

    config_name: "development", "testing" or "production". Defaults to the
    APP_ENV environment variable, then "production" (safest default).
    answerer: optional Answerer to use (tests pass a fake). If omitted, the
    real Azure-backed one is built on first use when the AZURE_* settings exist.
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
    app.extensions["ratelimiter"] = RateLimiter(
        per_minute=app.config["RATE_LIMIT_PER_MINUTE"], per_day=app.config["RATE_LIMIT_PER_DAY"]
    )

    from .routes import bp
    app.register_blueprint(bp)

    return app

"""Ask Barry: Flask application factory."""
import os

from flask import Flask

from .config import CONFIGS


def create_app(config_name=None):
    """Create and configure the Flask app.

    config_name: "development", "testing" or "production". Defaults to the
    APP_ENV environment variable, then "production" (safest default).
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

    from .routes import bp
    app.register_blueprint(bp)

    return app

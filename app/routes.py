"""HTTP routes. Stage 0: a placeholder home page and a health check."""
from flask import Blueprint, current_app, jsonify, render_template

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template(
        "index.html",
        app_name=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
    )


@bp.get("/health")
def health():
    """Used by Render's health check and by CI. Reports honestly what is live."""
    return jsonify(
        status="ok",
        app=current_app.config["APP_NAME"],
        stage=current_app.config["BUILD_STAGE"],
        features={"search": False, "embeddings": False, "generation": False},
    )

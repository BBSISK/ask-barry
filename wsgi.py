"""Entry point for Gunicorn (production) and `flask run` (local)."""
from app import create_app

app = create_app()

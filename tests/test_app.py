import pytest

from app import create_app


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["stage"] == "4-hybrid-search"


def test_health_reports_no_ai_features_yet(client):
    # Honesty check: nothing claims to be live before it is built.
    features = client.get("/health").get_json()["features"]
    assert features == {"search": False, "embeddings": False, "generation": False}


def test_index_page_renders(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Ask Barry" in resp.data


def test_production_refuses_to_start_without_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    # ProductionConfig reads SECRET_KEY at import time, so patch the class too.
    from app.config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", None)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_starts_with_secret_key(monkeypatch):
    from app.config import ProductionConfig
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "x" * 32)
    app = create_app("production")
    assert app.config["DEBUG"] is False


def test_unknown_config_rejected():
    with pytest.raises(ValueError):
        create_app("staging")

from unittest.mock import MagicMock

import pytest

from app import create_app


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["stage"] == "8-job-agent"


def test_health_reports_no_ai_features_yet(client):
    # Honesty check: nothing claims to be live before it is built.
    features = client.get("/health").get_json()["features"]
    assert features == {"search": False, "embeddings": False, "generation": False, "job_agent": False}


def test_ready_ok():
    mock_search = MagicMock()
    mock_search.search.return_value = [{"id": "chunk-1"}]
    mock_provider = MagicMock()
    mock_provider.generate.return_value = '{"ok": true}'

    app = create_app("testing", search_client=mock_search, model_provider=mock_provider)
    client = app.test_client()

    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ready"
    assert data["ready"] is True
    assert data["checks"] == {"search": "ok", "provider": "ok"}
    assert mock_search.search.called
    assert mock_provider.generate.called


def test_ready_search_down():
    mock_search = MagicMock()
    mock_search.search.side_effect = RuntimeError("Azure AI Search unavailable: secret-api-key-12345")
    mock_provider = MagicMock()
    mock_provider.generate.return_value = '{"ok": true}'

    app = create_app("testing", search_client=mock_search, model_provider=mock_provider)
    client = app.test_client()

    resp = client.get("/ready")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["status"] == "unavailable"
    assert data["ready"] is False
    assert "search" in data["failed"]
    assert "provider" not in data["failed"]
    assert "search" in data["error"]
    assert "secret-api-key-12345" not in resp.get_data(as_text=True)
    assert "Traceback" not in resp.get_data(as_text=True)
    assert "RuntimeError" not in resp.get_data(as_text=True)


def test_ready_provider_down():
    mock_search = MagicMock()
    mock_search.search.return_value = [{"id": "chunk-1"}]
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = RuntimeError("Azure OpenAI rate limited: secret-openai-key-abcde")

    app = create_app("testing", search_client=mock_search, model_provider=mock_provider)
    client = app.test_client()

    resp = client.get("/ready")
    assert resp.status_code == 503
    data = resp.get_json()
    assert data["status"] == "unavailable"
    assert data["ready"] is False
    assert "provider" in data["failed"]
    assert "search" not in data["failed"]
    assert "provider" in data["error"]
    assert "secret-openai-key-abcde" not in resp.get_data(as_text=True)
    assert "Traceback" not in resp.get_data(as_text=True)
    assert "RuntimeError" not in resp.get_data(as_text=True)


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


def test_ready_returns_within_timeout_when_a_dependency_hangs():
    import time
    mock_search = MagicMock()
    mock_search.search.return_value = [{"id": "chunk-1"}]
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = lambda *a, **k: time.sleep(6)

    app = create_app("testing", search_client=mock_search, model_provider=mock_provider)
    started = time.monotonic()
    resp = app.test_client().get("/ready")
    elapsed = time.monotonic() - started

    assert resp.status_code == 503
    assert resp.get_json()["failed"] == ["provider"]
    assert elapsed < 4.5, f"/ready took {elapsed:.1f}s; the timeout should cap it near 3s"

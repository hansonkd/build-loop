"""Tests for bearer token authentication middleware."""

import os

import pytest
from starlette.testclient import TestClient

# We test the middleware logic directly rather than through the full app
# to avoid needing LLM backends.
from glass.auth import BearerAuthMiddleware, _is_public


def test_public_paths():
    """Health probes and static assets are always public."""
    assert _is_public("/healthz") is True
    assert _is_public("/readyz") is True
    assert _is_public("/") is True
    assert _is_public("/static/app.js") is True
    assert _is_public("/static/style.css") is True
    assert _is_public("/docs") is True


def test_api_paths_not_public():
    """API paths are not public."""
    assert _is_public("/api/query") is False
    assert _is_public("/api/status") is False
    assert _is_public("/api/calibration") is False
    assert _is_public("/api/history") is False


def test_auth_middleware_no_token_configured():
    """When no token is configured, middleware passes everything through."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(BearerAuthMiddleware, token=None)

    @app.get("/api/test")
    def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/test")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_auth_middleware_rejects_without_token():
    """When token is configured, requests without Authorization are rejected."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(BearerAuthMiddleware, token="secret-token-123")

    @app.get("/api/test")
    def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/test")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_auth_middleware_accepts_correct_token():
    """Correct bearer token allows access."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(BearerAuthMiddleware, token="secret-token-123")

    @app.get("/api/test")
    def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/test", headers={"Authorization": "Bearer secret-token-123"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_auth_middleware_rejects_wrong_token():
    """Wrong bearer token is rejected."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(BearerAuthMiddleware, token="secret-token-123")

    @app.get("/api/test")
    def test_endpoint():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/api/test", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401
    assert "Invalid token" in resp.json()["detail"]


def test_auth_middleware_public_paths_bypass():
    """Public paths bypass auth even when token is configured."""
    from fastapi import FastAPI
    from starlette.testclient import TestClient

    app = FastAPI()
    app.add_middleware(BearerAuthMiddleware, token="secret-token-123")

    @app.get("/healthz")
    def healthz():
        return {"status": "alive"}

    @app.get("/readyz")
    def readyz():
        return {"status": "ready"}

    client = TestClient(app)

    # No auth header needed for health probes
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200

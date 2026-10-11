"""Tests for the /api/system endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def _get_teacher_token() -> str:
    client.post(
        "/api/auth/register",
        json={
            "email": "system_teacher@test.com",
            "password": "password123",
            "first_name": "Sys",
            "last_name": "Teacher",
            "role": "teacher",
        },
    )
    resp = client.post(
        "/api/auth/login",
        data={"username": "system_teacher@test.com", "password": "password123"},
    )
    return resp.json()["access_token"]


def test_ai_status_endpoint():
    resp = client.get("/api/system/ai-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ai_configured" in data
    assert "model_name" in data
    assert "message" in data


def test_configure_key_unauthenticated():
    resp = client.post("/api/system/configure-key", json={"api_key": "some_test_key_12345"})
    assert resp.status_code == 401


def test_configure_key_invalid_short():
    token = _get_teacher_token()
    resp = client.post(
        "/api/system/configure-key",
        headers={"Authorization": f"Bearer {token}"},
        json={"api_key": "short"},
    )
    assert resp.status_code == 422


def test_configure_key_success():
    token = _get_teacher_token()
    test_key = "AIzaSyTestKeyForSystemVerification123"
    resp = client.post(
        "/api/system/configure-key",
        headers={"Authorization": f"Bearer {token}"},
        json={"api_key": test_key},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["ai_configured"] is True
    assert settings.get_effective_ai_api_key() == test_key

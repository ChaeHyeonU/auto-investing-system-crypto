from collections.abc import Generator
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth import RefreshToken


TEST_DATABASE_URL = "sqlite:///./test_auto_investing.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_auto_investing.db"):
        os.remove("test_auto_investing.db")


def test_register_login_and_subscription() -> None:
    client = TestClient(app)
    email = "test-user@example.com"
    password = "password123"

    register_response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["user"]["email"] == email
    assert register_payload["access_token"]

    login_response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["access_token"]
    assert login_payload["refresh_token"]

    db = TestingSessionLocal()
    try:
        token_row = db.query(RefreshToken).filter(RefreshToken.user_id == login_payload["user"]["id"]).first()
        assert token_row is not None
    finally:
        db.close()

    token = login_payload["access_token"]
    sub_response = client.get("/v1/billing/subscription", headers={"Authorization": f"Bearer {token}"})
    assert sub_response.status_code == 200
    assert sub_response.json()["plan"] == "basic"


def test_login_invalid_credentials_returns_401() -> None:
    client = TestClient(app)
    email = "login-invalid@example.com"
    password = "password123"

    register_response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert register_response.status_code == 201

    invalid = client.post("/v1/auth/login", json={"email": email, "password": "wrong-password"})
    assert invalid.status_code == 401


def test_refresh_token_rotation() -> None:
    client = TestClient(app)
    email = "refresh-rotation@example.com"
    password = "password123"

    register_response = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert register_response.status_code == 201
    initial_refresh = register_response.json()["refresh_token"]

    refresh_response = client.post("/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]
    assert new_refresh != initial_refresh

    replay_response = client.post("/v1/auth/refresh", json={"refresh_token": initial_refresh})
    assert replay_response.status_code == 401

    second_refresh_response = client.post("/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert second_refresh_response.status_code == 200

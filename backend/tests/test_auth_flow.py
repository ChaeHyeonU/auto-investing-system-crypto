from collections.abc import Generator
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User


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

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.password_hash != password
    finally:
        db.close()

    login_response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["access_token"]

    token = login_payload["access_token"]
    sub_response = client.get("/v1/billing/subscription", headers={"Authorization": f"Bearer {token}"})
    assert sub_response.status_code == 200
    assert sub_response.json()["plan"] == "basic"


def test_register_duplicate_email_returns_conflict() -> None:
    client = TestClient(app)
    email = "duplicate-user@example.com"
    password = "password123"

    first = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert first.status_code == 201

    second = client.post("/v1/auth/register", json={"email": email, "password": password})
    assert second.status_code == 409

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # CI sets TEST_DATABASE_URL to run the same suite against a real PostgreSQL service.
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        engine = create_engine(url)
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def register_and_login(client: TestClient, email: str = "ada@example.com") -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "full_name": "Ada Lovelace", "password": "s3cret-pass"})
    res = client.post("/auth/token", data={"username": email, "password": "s3cret-pass"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)

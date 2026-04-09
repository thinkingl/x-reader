import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, init_db
from app.models.database import Base

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


def test_health_check(client):
    response = client.get("/api/books")
    assert response.status_code == 200


def test_create_voice_preset(client):
    response = client.post("/api/voice-presets", json={
        "name": "test_preset",
        "voice_mode": "design",
        "instruct": "female, young adult",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_preset"


def test_list_voice_presets(client):
    client.post("/api/voice-presets", json={
        "name": "preset1",
        "voice_mode": "design",
    })
    response = client.get("/api/voice-presets")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_get_config(client):
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "model_path" in data


def test_update_config(client):
    response = client.put("/api/config", json={"concurrency": 2})
    assert response.status_code == 200
    assert response.json()["concurrency"] == 2


def test_delete_voice_preset(client):
    create_resp = client.post("/api/voice-presets", json={
        "name": "to_delete",
        "voice_mode": "auto",
    })
    preset_id = create_resp.json()["id"]

    response = client.delete(f"/api/voice-presets/{preset_id}")
    assert response.status_code == 200

    response = client.get("/api/voice-presets")
    assert len(response.json()["items"]) == 0


def test_set_default_preset(client):
    create_resp = client.post("/api/voice-presets", json={
        "name": "default_test",
        "voice_mode": "design",
    })
    preset_id = create_resp.json()["id"]

    response = client.patch(f"/api/voice-presets/{preset_id}/set-default")
    assert response.status_code == 200
    assert response.json()["is_default"] == True


def test_list_books_empty(client):
    response = client.get("/api/books")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_list_tasks_empty(client):
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_cancel_nonexistent_task(client):
    response = client.delete("/api/tasks/999")
    assert response.status_code == 404

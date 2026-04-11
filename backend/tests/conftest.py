import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Import after setting environment
from app.main import app
from app.database import get_db
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


# Mock the audio converter to avoid loading the model
@pytest.fixture(autouse=True)
def mock_audio_converter():
    with patch("app.services.audio_converter.AudioConverter") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


# Mock the task queue
@pytest.fixture(autouse=True)
def mock_task_queue():
    with patch("app.main.task_queue") as mock:
        mock.max_workers = 1
        mock.executor = MagicMock()
        mock.submit_task = MagicMock()
        mock.submit_book_tasks = MagicMock()
        mock.shutdown = MagicMock()
        yield mock


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    # Reset the global auth manager for each test
    import app.main as main_module
    main_module._global_auth_manager = None
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Set test environment
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

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

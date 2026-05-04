import sys
import importlib.util

import pytest
from pathlib import Path

# Add the 2048 backend directory to sys.path so `from game import Game2048` resolves
# when backend/2048/backend/main.py is imported.
GAME_2048_BACKEND_DIR = str(Path(__file__).parent.parent / "backend" / "2048" / "backend")
if GAME_2048_BACKEND_DIR not in sys.path:
    sys.path.insert(0, GAME_2048_BACKEND_DIR)


@pytest.fixture
def game2048_client():
    """TestClient for the 2048 FastAPI app, reset to fresh state each test."""
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    client.post("/api/game/new", json={"board_size": 4, "target_tile": 2048})
    return client


@pytest.fixture
def todo_client(tmp_path, monkeypatch):
    """TestClient for the Todo FastAPI app with an isolated SQLite DB in tmp_path."""
    monkeypatch.chdir(tmp_path)

    todo_main_path = str(
        Path(__file__).parent.parent / "backend" / "todo" / "backend" / "main.py"
    )
    spec = importlib.util.spec_from_file_location("todo_main", todo_main_path)
    todo_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(todo_main)

    from fastapi.testclient import TestClient

    return TestClient(todo_main.app)

"""Tests for Todo FastAPI routes (backend/todo/backend/main.py)."""

import pytest


class TestCrud:
    def test_create_and_retrieve(self, todo_client):
        resp = todo_client.post("/api/items", json={"title": "Test", "description": "A test item"})
        assert resp.status_code == 200
        item = resp.json()
        assert item["title"] == "Test"
        assert item["completed"] is False

        fetched = todo_client.get(f"/api/items/{item['id']}").json()
        assert fetched["title"] == "Test"

    def test_update_marks_completed(self, todo_client):
        item = todo_client.post("/api/items", json={"title": "Do it", "description": ""}).json()
        todo_client.put(
            f"/api/items/{item['id']}",
            json={"title": "Do it", "description": "", "completed": True},
        )
        assert todo_client.get(f"/api/items/{item['id']}").json()["completed"] is True

    def test_delete_removes_item(self, todo_client):
        item = todo_client.post("/api/items", json={"title": "Gone", "description": ""}).json()
        todo_client.delete(f"/api/items/{item['id']}")
        assert todo_client.get(f"/api/items/{item['id']}").status_code == 404

    def test_get_nonexistent_returns_404(self, todo_client):
        assert todo_client.get("/api/items/999").status_code == 404


class TestEvaluation:
    def test_seed_creates_test_data(self, todo_client):
        todo_client.post("/api/eval/seed")
        stats = todo_client.get("/api/eval/stats").json()
        assert stats["total_items"] == 5
        assert stats["completed_items"] == 2
        assert stats["pending_items"] == 3

    def test_reset_clears_all(self, todo_client):
        todo_client.post("/api/eval/seed")
        todo_client.delete("/api/eval/reset")
        assert todo_client.get("/api/items").json() == []

    def test_has_todo_searches_title_and_description(self, todo_client):
        todo_client.post("/api/items", json={"title": "Buy milk", "description": "urgent errand"})
        assert todo_client.get("/api/eval/has_todo", params={"text": "Buy"}).json()["exists"] is True
        assert todo_client.get("/api/eval/has_todo", params={"text": "urgent"}).json()["exists"] is True
        assert todo_client.get("/api/eval/has_todo", params={"text": "xyz"}).json()["exists"] is False

    def test_bulk_update_completes_items(self, todo_client):
        ids = []
        for t in ("A", "B", "C"):
            ids.append(todo_client.post("/api/items", json={"title": t, "description": ""}).json()["id"])
        resp = todo_client.post("/api/eval/bulk_update", json={"item_ids": ids, "completed": True})
        assert resp.json()["updated_count"] == 3

    def test_completion_rate(self, todo_client):
        todo_client.post("/api/eval/seed")
        rate = todo_client.get("/api/eval/completion_rate").json()
        assert rate["completion_rate"] == pytest.approx(0.4)

    def test_seed_then_complete_all(self, todo_client):
        todo_client.post("/api/eval/seed")
        all_ids = [i["id"] for i in todo_client.get("/api/items").json()]
        todo_client.post("/api/eval/bulk_update", json={"item_ids": all_ids, "completed": True})
        assert todo_client.get("/api/eval/completion_rate").json()["completion_rate"] == 1.0

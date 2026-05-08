"""Tests for 2048 FastAPI routes (backend/2048/backend/main.py)."""


class TestGamePlay:
    def test_new_game(self, game2048_client):
        resp = game2048_client.post("/api/game/new", json={"board_size": 4, "target_tile": 512})
        assert resp.status_code == 200
        state = resp.json()
        assert state["board_size"] == 4
        assert state["target_tile"] == 512
        assert state["score"] == 0

    def test_valid_move_merges_and_scores(self, game2048_client):
        game2048_client.post(
            "/api/eval/set_board",
            json={"board": [[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]},
        )
        resp = game2048_client.post("/api/game/move", json={"direction": "left"})
        assert resp.status_code == 200
        assert resp.json()["score"] == 4

    def test_invalid_move_returns_400(self, game2048_client):
        game2048_client.post(
            "/api/eval/set_board",
            json={"board": [[2, 4, 8, 16], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]},
        )
        resp = game2048_client.post("/api/game/move", json={"direction": "left"})
        assert resp.status_code == 400

    def test_set_target_triggers_win(self, game2048_client):
        game2048_client.post(
            "/api/eval/set_board",
            json={"board": [[64, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]},
        )
        resp = game2048_client.post("/api/game/set_target", json={"target_tile": 64})
        assert resp.json()["won"] is True


class TestEvalEndpoints:
    def test_eval_stats_efficiency(self, game2048_client):
        game2048_client.post("/api/game/new", json={})
        resp = game2048_client.get("/api/eval/stats")
        assert resp.json()["efficiency"] == 0.0  # No moves yet

    def test_set_board_and_read_back(self, game2048_client):
        board = [[4, 8, 16, 32], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        game2048_client.post("/api/eval/set_board", json={"board": board, "score": 500, "moves": 50})
        state = game2048_client.get("/api/game/state").json()
        assert state["board"] == board
        assert state["score"] == 500

    def test_seed_produces_known_board(self, game2048_client):
        resp = game2048_client.post("/api/eval/seed")
        assert resp.json()["highest_tile"] == 1024

    def test_reset_clears_score(self, game2048_client):
        game2048_client.post("/api/eval/seed")  # Set some state
        resp = game2048_client.post("/api/eval/reset")
        assert resp.json()["score"] == 0
        assert resp.json()["moves"] == 0

    def test_empty_cells_count(self, game2048_client):
        game2048_client.post(
            "/api/eval/set_board",
            json={"board": [[2, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]},
        )
        resp = game2048_client.get("/api/eval/board")
        assert resp.json()["empty_cells"] == 15

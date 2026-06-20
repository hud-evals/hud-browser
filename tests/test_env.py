"""Offline tests for the browser env templates — grading logic only, no browser or substrate.

Each test drives an `@env.template` generator with a fake HTTP client that returns canned app state,
so the reward math is exercised without Docker. The real browser rollout is verified separately.
"""

import pytest

import env as M


class _Resp:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class _FakeHTTP:
    """Stand-in for the module httpx client: GET returns canned state keyed by trailing path."""

    def __init__(self, state: dict):
        self.state = state

    async def post(self, url, **kw):
        return _Resp({})

    async def delete(self, url, **kw):
        return _Resp({})

    async def get(self, url, **kw):
        for suffix, data in self.state.items():
            if url.endswith(suffix):
                return _Resp(data)
        return _Resp({})


@pytest.fixture(autouse=True)
def _no_browser(monkeypatch):
    """There is no browser in unit tests — pre-navigation is a no-op."""

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(M, "_navigate", _noop)


async def _grade(monkeypatch, template, state, **kwargs):
    monkeypatch.setattr(M, "_http", _FakeHTTP(state))
    gen = template.func(**kwargs)
    await gen.asend(None)  # setup + first yield (prompt)
    return await gen.asend("done")  # second yield (reward)


async def test_2048_reach_tile_hit(monkeypatch):
    reward = await _grade(
        monkeypatch, M.reach_tile,
        {"/api/game/state": {"highest_tile": 512, "score": 4000}}, target=512,
    )
    assert reward == pytest.approx(1.0)


async def test_2048_reach_tile_partial(monkeypatch):
    reward = await _grade(
        monkeypatch, M.reach_tile,
        {"/api/game/state": {"highest_tile": 64, "score": 600}}, target=512,
    )
    assert 0.0 < reward < 1.0


async def test_2048_reach_tile_zero_score(monkeypatch):
    reward = await _grade(
        monkeypatch, M.reach_tile,
        {"/api/game/state": {"highest_tile": 0, "score": 0}}, target=512,
    )
    assert reward == 0.0


async def test_2048_near_win(monkeypatch):
    win = await _grade(monkeypatch, M.near_win, {"/api/game/state": {"won": True}}, target=2048)
    assert win == 1.0
    lose = await _grade(
        monkeypatch, M.near_win,
        {"/api/game/state": {"won": False, "highest_tile": 1024}}, target=2048,
    )
    assert lose == 0.0


async def test_2048_score(monkeypatch):
    reward = await _grade(
        monkeypatch, M.reach_score, {"/api/game/state": {"score": 2500}}, target_score=5000,
    )
    assert reward == pytest.approx(0.5)


async def test_todo_complete(monkeypatch):
    full = await _grade(
        monkeypatch, M.complete_todos, {"/api/eval/stats": {"completed_items": 3}}, expected_count=3,
    )
    assert full == 1.0
    half = await _grade(
        monkeypatch, M.complete_todos, {"/api/eval/stats": {"completed_items": 1}}, expected_count=2,
    )
    assert half == pytest.approx(0.5)


async def test_todo_create(monkeypatch):
    hit = await _grade(
        monkeypatch, M.create_todo,
        {"/api/eval/todos": [{"title": "Buy groceries"}]}, title="Buy groceries",
    )
    assert hit == 1.0
    miss = await _grade(
        monkeypatch, M.create_todo, {"/api/eval/todos": [{"title": "Other"}]}, title="Buy groceries",
    )
    assert miss == 0.0


async def test_todo_completion_rate(monkeypatch):
    reward = await _grade(
        monkeypatch, M.completion_rate,
        {"/api/eval/stats": {"total_items": 4, "completed_items": 2}}, target_rate=0.5,
    )
    assert reward == pytest.approx(1.0)

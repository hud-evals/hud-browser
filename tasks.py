"""Tasks for the browser environment.

`hud eval tasks.py` and `hud sync tasks` collect the public `tasks` list below. Add a task by
calling one of the env templates, setting a `.slug`, and appending it to the list. The rfb desktop
is Linux-only, so verify a real rollout on the image / `--runtime hud`, not on macOS.

    hud eval tasks.py claude --task-ids 2048-reach-256 --runtime tcp://127.0.0.1:8765 -y
"""

from env import (  # noqa: F401  (re-export env for `hud eval tasks.py`)
    complete_todos,
    completion_rate,
    create_todo,
    env,
    near_win,
    reach_score,
    reach_tile,
)

# -- 2048: logarithmic partial credit ------------------------------------------
_reach_256 = reach_tile(target=256)
_reach_256.slug = "2048-reach-256"

_reach_512 = reach_tile(target=512)
_reach_512.slug = "2048-reach-512"

# -- 2048: near-win (binary) ---------------------------------------------------
_near_2048 = near_win(target=2048)
_near_2048.slug = "2048-near-win"

_near_1024 = near_win(target=1024)
_near_1024.slug = "2048-near-win-1024"

# -- 2048: score target (linear partial credit) --------------------------------
_score_5000 = reach_score(target_score=5000)
_score_5000.slug = "2048-score-5000"

# -- todo: count-based partial credit ------------------------------------------
_complete_3 = complete_todos(expected_count=3)
_complete_3.slug = "todo-complete-3"

# -- todo: exact-title (binary) ------------------------------------------------
_create_groceries = create_todo(title="Buy groceries")
_create_groceries.slug = "todo-create-groceries"

_create_meeting = create_todo(title="Schedule team meeting")
_create_meeting.slug = "todo-create-meeting"

# -- todo: rate-based partial credit -------------------------------------------
_rate_50 = completion_rate(target_rate=0.5)
_rate_50.slug = "todo-rate-50"

_rate_80 = completion_rate(target_rate=0.8)
_rate_80.slug = "todo-rate-80"


tasks = [
    _reach_256,
    _reach_512,
    _near_2048,
    _near_1024,
    _score_5000,
    _complete_3,
    _create_groceries,
    _create_meeting,
    _rate_50,
    _rate_80,
]

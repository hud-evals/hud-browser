"""Tasks for the browser environment.

Each task is created via scenario.task() and can be run locally or remotely:

    python local_test.py --list
    python local_test.py --task reach_tile_256
    python local_test.py --task complete_3 --model gpt-4o
"""

from env import SCENARIOS

# -- 2048: partial credit (logarithmic scaling) --------------------------------

reach_tile_256 = SCENARIOS["reach_tile"].task(target=256)
reach_tile_256.slug = "2048-reach-256"

reach_tile_512 = SCENARIOS["reach_tile"].task(target=512)
reach_tile_512.slug = "2048-reach-512"

# -- 2048: binary scoring (near-win) ------------------------------------------

near_win_2048 = SCENARIOS["near_win"].task(target=2048)
near_win_2048.slug = "2048-near-win"

near_win_1024 = SCENARIOS["near_win"].task(target=1024)
near_win_1024.slug = "2048-near-win-1024"

# -- 2048: score target (linear partial credit) --------------------------------

score_5000 = SCENARIOS["reach_score"].task(target_score=5000)
score_5000.slug = "2048-score-5000"

# -- todo: partial credit (count-based) ----------------------------------------

complete_3 = SCENARIOS["complete_todos"].task(expected_count=3)
complete_3.slug = "todo-complete-3"

# -- todo: binary scoring (exact match) ----------------------------------------

create_groceries = SCENARIOS["create_todo"].task(title="Buy groceries")
create_groceries.slug = "todo-create-groceries"

create_meeting = SCENARIOS["create_todo"].task(title="Schedule team meeting")
create_meeting.slug = "todo-create-meeting"

# -- todo: partial credit (rate-based) -----------------------------------------

rate_50 = SCENARIOS["completion_rate"].task(target_rate=0.5)
rate_50.slug = "todo-rate-50"

rate_80 = SCENARIOS["completion_rate"].task(target_rate=0.8)
rate_80.slug = "todo-rate-80"

# -- registry for discovery ----------------------------------------------------

ALL_TASKS = {
    # 2048 tasks
    "reach_tile_256": reach_tile_256,
    "reach_tile_512": reach_tile_512,
    "near_win_2048": near_win_2048,
    "near_win_1024": near_win_1024,
    "score_5000": score_5000,
    # todo tasks
    "complete_3": complete_3,
    "create_groceries": create_groceries,
    "create_meeting": create_meeting,
    "rate_50": rate_50,
    "rate_80": rate_80,
}

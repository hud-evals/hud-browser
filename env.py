"""Browser Environment — visual browser automation with 2048 + todo apps.

- @env.tool() routers from tools/ for browser interaction (playwright, computer)
- @env.scenario() definitions for 2048 game and todo app evaluation flows
- Apps are launched dynamically via tools/apps.py
"""

import logging
import math
import subprocess
import sys
from typing import Any

from hud import Environment

from tools.apps import _launch_app_internal, router as apps_router
from tools.browser import http_client, router as browser_router

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
    force=True,
)
for logger_name in ["httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

env = Environment(name="browser")
env.include_router(browser_router)
env.include_router(apps_router)


@env.tool()
async def hud_validate() -> str:
    """Run the test suite to validate the environment is working correctly."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd="/app",
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(output or f"pytest exited with code {result.returncode}")
    return output


# =============================================================================
# 2048 game scenarios
# =============================================================================

GAME_2048_SYSTEM_PROMPT = """You are an expert 2048 game player using a browser interface.

HOW 2048 WORKS:
- 4x4 grid with numbered tiles (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048...)
- When you move, all tiles slide in that direction
- When two tiles with SAME number touch, they merge (2+2=4, 4+4=8, etc.)
- After each move, a new tile (2 or 4) appears randomly
- Game ends when grid is full and no merges possible

BROWSER INTERACTION:
1. First, take a screenshot to see the board
2. Make moves using arrow keys: up, down, left, right
3. Continue until you reach the target or game ends

Strategy: keep highest tiles in a corner; maintain order; avoid random moves."""


@env.scenario("2048-reach-tile", exclude_tools=["hud_validate"])
async def reach_tile(target: int = 512, board_size: int = 4) -> Any:
    """Play 2048 and try to reach the target tile.

    Args:
        target: Target tile value to reach (e.g., 512, 1024, 2048)
        board_size: Size of the game board (default: 4)
    """
    try:
        app_info = await _launch_app_internal("2048")
    except Exception as e:
        logger.error("Failed to launch 2048: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5001)
    await http_client.post(
        f"http://localhost:{backend_port}/api/game/new",
        json={"board_size": board_size, "target_tile": target},
    )

    logger.info("2048 scenario started: target=%d, board=%dx%d", target, board_size, board_size)

    prompt = f"""Play the 2048 game and try to reach the {target} tile.

Use the computer tool to:
1. Take a screenshot to see the current board
2. Press arrow keys (up, down, left, right) to make moves
3. Continue until you reach {target} or the game ends

Start by taking a screenshot."""

    _ = yield prompt

    try:
        state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
        state_response.raise_for_status()
        game_state = state_response.json()

        highest_tile = game_state.get("highest_tile", 0)
        score = game_state.get("score", 0)

        # Logarithmic reward scaling
        if score == 0:
            reward = 0.0
        elif target > 1 and highest_tile > 1:
            reward = min(1.0, math.log(highest_tile) / math.log(target))
        else:
            reward = 0.0

        logger.info("2048 result: highest=%d, target=%d, reward=%.2f", highest_tile, target, reward)
        yield reward

    except Exception as e:
        logger.error("2048 evaluation failed: %s", e)
        yield 0.0


@env.scenario("2048-near-win", exclude_tools=["hud_validate"])
async def near_win(target: int = 2048) -> Any:
    """Start with a near-winning board and finish the game.

    Args:
        target: Target tile to reach (board is set up one merge away)
    """
    try:
        app_info = await _launch_app_internal("2048")
    except Exception as e:
        logger.error("Failed to launch 2048: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5001)
    target = int(target)

    if target == 2048:
        board = [[1024, 1024, 256, 128], [512, 256, 64, 32], [128, 64, 16, 8], [32, 16, 4, 2]]
    elif target == 1024:
        board = [[512, 512, 128, 64], [256, 128, 32, 16], [64, 32, 8, 4], [16, 8, 2, 0]]
    else:
        half = target // 2
        quarter = target // 4
        board = [
            [half, half, quarter, quarter // 2],
            [quarter, quarter // 2, 16, 8],
            [16, 8, 4, 2],
            [4, 2, 0, 0],
        ]

    await http_client.post(
        f"http://localhost:{backend_port}/api/eval/set_board",
        json={"board": board, "score": sum(sum(row) for row in board) * 2, "moves": 150},
    )

    logger.info("2048 near-win scenario: target=%d", target)

    prompt = f"""You're one move away from winning! Reach the {target} tile.

The board is set up with two {target // 2} tiles ready to merge.
Use arrow keys to make the winning move.

Take a screenshot first to see the board."""

    _ = yield prompt

    try:
        state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
        game_state = state_response.json()
        won = game_state.get("won", False) or game_state.get("highest_tile", 0) >= target
        yield 1.0 if won else 0.0
    except Exception:
        yield 0.0


@env.scenario("2048-score", exclude_tools=["hud_validate"])
async def reach_score(target_score: int = 5000) -> Any:
    """Play 2048 and try to reach a target score.

    Args:
        target_score: Target score to reach
    """
    try:
        app_info = await _launch_app_internal("2048")
    except Exception as e:
        logger.error("Failed to launch 2048: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5001)
    await http_client.post(f"http://localhost:{backend_port}/api/game/new", json={})

    prompt = f"""Play 2048 and try to reach a score of {target_score}.

Use the computer tool to take screenshots and make moves with arrow keys.
Focus on efficient tile merging to maximize your score."""

    _ = yield prompt

    try:
        state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
        game_state = state_response.json()
        score = game_state.get("score", 0)
        reward = min(1.0, score / target_score) if target_score > 0 else 0.0
        yield reward
    except Exception:
        yield 0.0


# =============================================================================
# Todo app scenarios
# =============================================================================


@env.scenario("todo-complete", exclude_tools=["hud_validate"])
async def complete_todos(expected_count: int = 3) -> Any:
    """Mark todos as complete.

    Args:
        expected_count: Number of todos that should be completed
    """
    try:
        app_info = await _launch_app_internal("todo")
    except Exception as e:
        logger.error("Failed to launch todo: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5000)
    await http_client.post(f"http://localhost:{backend_port}/api/eval/seed")

    logger.info("Todo scenario started: complete %d todos", expected_count)

    prompt = f"""Complete {expected_count} todo items in the list.

Use the browser to:
1. Take a screenshot to see the todo list
2. Click on todo items to mark them as complete
3. Continue until {expected_count} items are marked done

Start by taking a screenshot."""

    _ = yield prompt

    try:
        stats_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/stats")
        stats = stats_response.json()
        completed = stats.get("completed_items", 0)

        if completed >= expected_count:
            reward = 1.0
        elif expected_count > 0:
            reward = completed / expected_count
        else:
            reward = 0.0

        logger.info(
            "Todo result: completed=%d, expected=%d, reward=%.2f",
            completed, expected_count, reward,
        )
        yield reward
    except Exception as e:
        logger.error("Todo evaluation failed: %s", e)
        yield 0.0


@env.scenario("todo-create", exclude_tools=["hud_validate"])
async def create_todo(title: str) -> Any:
    """Create a new todo item with a specific title.

    Args:
        title: The exact title the new todo should have
    """
    try:
        app_info = await _launch_app_internal("todo")
    except Exception as e:
        logger.error("Failed to launch todo: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5000)
    await http_client.delete(f"http://localhost:{backend_port}/api/eval/reset")

    logger.info("Todo create scenario: title='%s'", title)

    prompt = f"""Create a new todo item with the title: "{title}"

Use the browser to:
1. Take a screenshot to see the todo app
2. Find the input field for new todos
3. Type the title and submit

The todo title must be exactly: {title}"""

    _ = yield prompt

    try:
        todos_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/todos")
        todos = todos_response.json()
        exists = any(todo.get("title") == title for todo in todos)
        yield 1.0 if exists else 0.0
    except Exception:
        yield 0.0


@env.scenario("todo-completion-rate", exclude_tools=["hud_validate"])
async def completion_rate(target_rate: float = 0.5) -> Any:
    """Complete a percentage of seeded todos.

    Args:
        target_rate: Target completion rate (0.0 to 1.0)
    """
    try:
        app_info = await _launch_app_internal("todo")
    except Exception as e:
        logger.error("Failed to launch todo: %s", e)
        yield 0.0
        return

    backend_port = app_info.get("backend_port", 5000)
    await http_client.post(f"http://localhost:{backend_port}/api/eval/seed")

    pct = int(target_rate * 100)
    prompt = f"""Complete at least {pct}% of the todo items in the list.

Use the browser to view and complete todo items.
You need to mark enough items as done to reach {pct}% completion."""

    _ = yield prompt

    try:
        stats_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/stats")
        stats = stats_response.json()
        total = stats.get("total_items", 0)
        completed = stats.get("completed_items", 0)

        actual_rate = completed / total if total > 0 else 0.0
        reward = min(1.0, actual_rate / target_rate) if target_rate > 0 else 1.0
        yield reward
    except Exception:
        yield 0.0


if __name__ == "__main__":
    from tools.browser import _discover_cdp_url, playwright

    playwright._cdp_url = _discover_cdp_url()
    env.run(transport="stdio")

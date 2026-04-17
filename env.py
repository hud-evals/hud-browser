"""Browser Environment - Visual browser automation with multiple apps.

This demonstrates:
- @env.tool() for browser interaction (playwright, computer tools)
- @env.scenario() for different app-based evaluation flows
- Dynamic app launching (2048 game, todo app, etc.)
"""

import logging
import subprocess
import sys

from hud import Environment

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
    force=True,
)
for logger_name in ["httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Environment instance
env = Environment(name="browser")

# Include tool routers
from tools.apps import router as apps_router
from tools.browser import router as browser_router

env.include_router(browser_router)
env.include_router(apps_router)

# Register scenarios and collect handles automatically
from scenarios.game_2048 import register_scenarios as register_2048_scenarios
from scenarios.todo import register_scenarios as register_todo_scenarios

SCENARIOS: dict = {}
SCENARIOS.update(register_2048_scenarios(env))
SCENARIOS.update(register_todo_scenarios(env))


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


if __name__ == "__main__":
    from tools.browser import playwright, _discover_cdp_url

    playwright._cdp_url = _discover_cdp_url()
    env.run(transport="stdio")

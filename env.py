"""Browser Environment - Visual browser automation with multiple apps.

This demonstrates:
- @env.tool() for browser interaction (playwright, computer tools)
- @env.scenario() for different app-based evaluation flows
- Dynamic app launching (2048 game, todo app, etc.)
"""
import logging
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
from tools.browser import router as browser_router
from tools.apps import router as apps_router

env.include_router(browser_router)
env.include_router(apps_router)

# Register scenarios (scenarios must use @env.scenario, not routers)
from scenarios.game_2048 import register_scenarios as register_2048_scenarios
from scenarios.todo import register_scenarios as register_todo_scenarios

register_2048_scenarios(env)
register_todo_scenarios(env)


if __name__ == "__main__":
    env.run(transport="stdio")

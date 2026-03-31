"""Browser environment scenarios.

Scenarios are registered with @env.scenario(). Each module exports a
register_scenarios(env) function that returns a dict of scenario handles.
"""

from scenarios.game_2048 import register_scenarios as register_2048_scenarios
from scenarios.todo import register_scenarios as register_todo_scenarios

__all__ = ["register_2048_scenarios", "register_todo_scenarios"]

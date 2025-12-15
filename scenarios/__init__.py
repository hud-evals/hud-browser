"""Browser environment scenarios.

Scenarios must be registered with @env.scenario() since they're Environment-specific.
Each module exports a register_scenarios(env) function.
"""
from scenarios.game_2048 import register_scenarios as register_2048_scenarios
from scenarios.todo import register_scenarios as register_todo_scenarios

__all__ = ["register_2048_scenarios", "register_todo_scenarios"]

# Browser Environment

A visual browser automation environment with multiple web apps (2048 game, todo app). Agents interact through Playwright, computer-use tools, and app management APIs.

## Quick Start

```bash
uv sync                # install dependencies
hud deploy .           # build and deploy to HUD platform
hud sync tasks <name>  # upload task definitions
```

## Scenarios

### 2048 Game

| Scenario | Args | Description |
|----------|------|-------------|
| `2048-reach-tile` | `target` (int) | Play until reaching target tile |
| `2048-near-win` | `target` (int) | Start near-win board, finish the game |
| `2048-score` | `target_score` (int) | Play until reaching target score |

### Todo App

| Scenario | Args | Description |
|----------|------|-------------|
| `todo-complete` | `expected_count` (int) | Mark N todos as complete |
| `todo-create` | `title` (str) | Create a todo with a specific title |
| `todo-completion-rate` | `target_rate` (float) | Complete a percentage of todos |

## Documentation

To learn more about tasks, evaluations, and running at scale see the [full docs](https://docs.hud.ai).

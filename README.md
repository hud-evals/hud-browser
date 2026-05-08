# Browser Environment

A visual browser automation environment with multiple web apps (2048 game, todo app). Agents interact through Playwright, computer-use tools, and app management APIs.

## Setup

```bash
uv sync
hud set HUD_API_KEY=your-key-here   # CLI auth, get one at hud.ai/project/api-keys
```

## Deploy & Run

```bash
hud deploy .                              # deploy the environment (once)
hud sync tasks <taskset-name>             # push tasks to a taskset (fast, re-run on every task change)
hud eval <taskset-name> --remote --full
```

**Iteration loop:** `hud deploy` is the slow step — run it once. After that, edit `tasks.py` and re-run `hud sync tasks` (takes seconds). Only redeploy when `env.py` or the Dockerfile changes.

See [Deploy & Go Remote](https://docs.hud.ai/building/running-at-scale) for deploy flags, secrets, and auto-deploy options.

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

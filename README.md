# Browser Environment

Visual browser automation with multiple web apps (2048 game, todo app, etc.).

## 1. Deploy to Platform

If you haven't already, connect this repo to hud.ai:

1. Push to GitHub
2. Go to [hud.ai](https://hud.ai) → **New** → **Environment**
3. Connect your GitHub repo
4. Your environment builds automatically on each push

Once deployed, your environment is accessible by its slug (e.g., `my-org/browser`).

## 2. Define Tools and Scenarios

Tools are functions agents can call. Scenarios define the evaluation lifecycle.

### Tools (in `tools/`)

```python
# tools/browser.py - Playwright and computer tools
router.tool(playwright)
router.tool(HudComputerTool(display_num=1))

# tools/apps.py - App management
@router.tool
async def launch_app(app_name: str) -> str:
    """Launch a specific application (e.g., 'todo', '2048')."""
    ...
```

### Scenarios (in `scenarios/`)

Scenarios define the evaluation lifecycle:

```python
# scenarios/game_2048.py
@env.scenario("2048-reach-tile")
async def reach_tile(target: int = 512) -> Any:
    # Setup: Launch 2048 and initialize game
    await http_client.post("/apps/launch", json={"app_name": "2048"})
    
    # Yield prompt
    _ = yield f"Play 2048 and reach the {target} tile."
    
    # Evaluate: Check highest tile
    state = await http_client.get(f"http://localhost:{port}/api/game/state")
    yield min(1.0, math.log(highest) / math.log(target))
```

## 3. Create Tasks from Scenarios

Tasks are scenario instances with specific arguments.

**In Code:**

```python
from env import env

task = env("2048-reach-tile", target=512)
task = env("todo-complete", expected_count=3)
```

**From JSON (`remote_tasks.json`):**

```json
{
  "env": {"name": "my-org/browser"},
  "scenario": "2048-reach-tile",
  "args": {"target": 512}
}
```

**On Platform:**

After deploying, create tasks from your scenarios on hud.ai. Access them by slug:

```python
from hud.datasets import load_tasks
tasks = load_tasks("my-org/browser-tasks")
```

## 4. Run Evaluations

Run tasks and see results on hud.ai. You have three options:

**On Platform:**
Run evaluations at scale directly on [hud.ai](https://hud.ai) with parallel execution and automatic tracing.

**CLI:**

```bash
# From local JSON file
hud eval ./remote_tasks.json --model gpt-4o --remote  # https://hud.ai/models

# From platform dataset
hud eval my-org/browser --model gpt-4o --remote --group 5
```

**Python:**

```python
import hud
from hud.agents import OpenAIChatAgent

task = env("2048-reach-tile", target=256)

async with hud.eval(task) as ctx:
    agent = OpenAIChatAgent.create(model="gpt-4o")  # https://hud.ai/models
    await agent.run(ctx)
```

**With Variants (A/B Testing):**

```python
tasks = [env("2048-reach-tile", target=256), env("todo-complete", expected_count=2)]
variants = {"model": ["gpt-4o-mini", "gpt-4o"]}

async with hud.eval(tasks, variants=variants, group=2) as ctx:
    agent = OpenAIChatAgent.create(model=ctx.variants["model"])
    await agent.run(ctx, max_steps=20)
```

## Local Development

This environment requires Docker (for X11/VNC). Use `hud dev` with hot-reload:

```bash
# 1. Build the Docker image (first time only)
hud build

# 2. Start with hot-reload on scenarios
hud dev -w scenarios -w tools --port 8765

# 3. Test locally
python local_test.py
```

### Hot-Reload

| Component | Reloaded? |
|-----------|-----------|
| `scenarios/*.py` | ✅ Yes |
| `tools/*.py` | ✅ Yes (if watched) |
| `backend/` | ❌ No (has frontend builds) |
| X11/VNC services | ❌ No (persist) |

**When to rebuild:** Dockerfile changes, backend apps, frontend builds.

## Structure

```
hud-browser/
├── env.py                  # Main environment entry point
├── tools/
│   ├── __init__.py
│   ├── browser.py          # Playwright, computer tools
│   └── apps.py             # launch_app, api_request
├── scenarios/
│   ├── __init__.py
│   ├── game_2048.py        # 2048-reach-tile, 2048-custom-board, 2048-score
│   └── todo.py             # todo-complete, todo-create, todo-completion-rate
├── backend/
│   ├── server.py           # FastAPI managing X11/VNC/apps
│   ├── 2048/               # 2048 game (backend + frontend)
│   └── todo/               # Todo app (backend + frontend)
├── local_test.py
├── remote_test.py
├── remote_tasks.json
├── Dockerfile.hud
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Available Scenarios

| Scenario | Args | Description |
|----------|------|-------------|
| `2048-reach-tile` | `target` (int) | Play until reaching target tile |
| `2048-custom-board` | `board`, `goal_tile`, `prompt?` | Start from custom board state |
| `2048-score` | `target_score` (int) | Play until reaching score |
| `todo-complete` | `expected_count` (int) | Complete N todos |
| `todo-create` | `title` (str) | Create todo with specific title |
| `todo-completion-rate` | `target_rate` (float) | Complete percentage of todos |

### Custom Board Example

```python
# Start from a specific board configuration
task = env("2048-custom-board",
    board=[[256, 128, 64, 32], [128, 64, 32, 16], [64, 32, 16, 8], [0, 0, 4, 2]],
    goal_tile=512,
    prompt="Merge tiles to reach 512. The 256 is in the corner."
)
```

## Documentation

Full documentation: [docs.hud.ai](https://docs.hud.ai)

# Browser Environment

Browser automation environment with GUI access for testing web applications. Includes sample apps (2048, Todo) and supports hot-reload development.

## Quick Start

```bash
# Build the Docker image
hud build

# Start hot-reload development server
hud dev

# Run the sample tasks
hud eval tasks.json
```

This environment **requires Docker** due to X11/VNC dependencies.

## Deploy

When you're ready to use this environment in production:

1. Push your code to GitHub
2. Connect your repo at [hud.ai](https://hud.ai/environments/new)
3. Builds will trigger automatically on each push

## Architecture

- **`environment/`** - FastAPI backend with X11/VNC services, manages web apps
- **`server/`** - MCP tools for browser automation (Playwright, computer vision)

## Tools

### Browser Automation
- **playwright** - Browser automation (navigate, click, type, screenshot, etc.)
- **computer** - Computer use tools (HUD, Anthropic, OpenAI variants)
- **launch_app(app_name)** - Launch an app (e.g., "2048", "todo")
- **api_request(url, method, data)** - Make HTTP requests

### Setup (dispatched via `setup` tool)
- **game_2048_board** / **game_2048_set_board** / **game_2048_near_win** / **game_2048_reset**
- **todo_seed** / **todo_reset** / **todo_custom_seed**

### Evaluate (dispatched via `evaluate` tool)
- **game_2048_max_number** / **game_2048_efficiency** / **game_2048_score_reached** / **game_2048_game_won**
- **todo_completed** / **todo_exists** / **todo_completion_rate** / **todo_total_count**

## Learn More

For complete documentation on building environments and running evaluations, visit [docs.hud.ai](https://docs.hud.ai).

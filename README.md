# hud-browser

A HUD **v6** environment for **browser agents**: a 2048 game and a todo app the agent plays in a real
Chromium. The *same* browser is published **two ways**, so any agent can drive it:

- **`cdp`** — Chromium's DevTools endpoint (DOM + key events), for browser-native agents
- **`rfb`** — the same browser on a VNC desktop, for computer-use (CUA) agents

Tasks grade server-side by reading each app's own state over HTTP — never the agent's self-report.

## Layout

```
env.py            Environment: @env.initialize launches the desktop (Xvfb · x11vnc · BrowserOS) and
                  both apps directly, publishes the cdp + rfb capabilities; the task templates live here
tasks.py          task instances (prompt + target + slug) collected into the public `tasks` list
backend/          the two apps — 2048 and todo, each a FastAPI backend + a Next.js frontend
Dockerfile.hud    image: browser-base + BrowserOS + the Next.js app builds + the v6 control channel
```

The substrate is launched from `env.py` (one path for the image and a Linux `hud eval`) and runs as the
unprivileged `ubuntu` user, so an agent can't read the `chmod 700` grading code via `file://`.

## Run

Run it on the platform — `hud deploy` builds the image on hud's (amd64) infra and runs everything
hosted, so it works from any machine (BrowserOS is amd64-only, so the desktop can't run on macOS):

```bash
cp .env.example .env                                # HUD_API_KEY
hud deploy .                                         # build + deploy the env
hud eval tasks.py claude --runtime hud --full        # all 10 tasks (--full = 100 steps each), hosted
```

`hud eval` prints a job link (`hud.ai/jobs/<id>`) — open it to watch each rollout live and inspect the
rewards, steps, and recordings. Drop `--full` to run the first task only, or pass `--task-ids <slug>`.

**Local iteration** (a Linux/amd64 host — the X11 desktop can't run on macOS): build the image, run a
container that serves the env, and attach an agent over `tcp://` (the container needs no key — grading
is over HTTP). The noVNC viewer is the local stand-in for the job page:

```bash
docker build -f Dockerfile.hud -t hud-browser:dev .
docker run -d -p 8765:8765 -p 8080:8080 hud-browser:dev
hud eval tasks.py claude --runtime tcp://127.0.0.1:8765 --task-ids 2048-reach-256 -y
# watch the container desktop at http://localhost:8080/vnc.html
```

## Tasks

| Slug | App | Grading |
|------|-----|---------|
| `2048-reach-256`, `2048-reach-512` | 2048 | reach a tile — logarithmic partial credit |
| `2048-near-win`, `2048-near-win-1024` | 2048 | finish a near-won board — binary |
| `2048-score-5000` | 2048 | reach a score — linear partial credit |
| `todo-complete-3` | todo | complete N items — count-based partial credit |
| `todo-create-groceries`, `todo-create-meeting` | todo | create an exact-title item — binary |
| `todo-rate-50`, `todo-rate-80` | todo | complete a fraction of items — rate-based |

Adding a task needs **no redeploy** — it reuses the env templates, so a new prompt/target travels at eval
time. Redeploy only when `env.py`, the `backend/` substrate, or the `Dockerfile` changes.

## Tests

```bash
uv sync
uv run pytest tests/ -q
```

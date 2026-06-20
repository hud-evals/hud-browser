"""Browser environment (HUD v6) — a 2048 game and a todo app, driven through a real Chromium on a
virtual display.

ONE browser is published TWO ways so any agent can drive it:
  * ``cdp``  — Chromium's DevTools endpoint (DOM + key events), for browser-native agents
  * ``rfb``  — the same browser on an Xvfb desktop served over VNC, for computer-use agents

``@env.initialize`` launches the whole substrate as subprocesses — the desktop (Xvfb :1 + x11vnc +
BrowserOS-with-CDP) and each app (a FastAPI backend + a Next.js frontend) — then publishes both
capabilities; ``@env.shutdown`` tears it down. One self-contained launch path: no init system and no
control server. Each task seeds its app's state over HTTP, prompts the agent, then grades by reading
the app's own state back — never the self-report.

In the image the substrate runs as the unprivileged ``ubuntu`` user, so an agent who points the
browser at ``file://`` cannot read the ``chmod 700`` grading code; the control channel stays root.
"""

# NOTE: do NOT add `from __future__ import annotations` — under it a typed @env.template param
# crashes the sync/deploy manifest path (TypeAdapter on a string forward-ref). (porting notes 15.E)
import asyncio
import logging
import math
import os
import pwd
import shutil
import socket
import sys

import httpx

from hud import Environment
from hud.capabilities import Capability

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s | %(name)s | %(message)s",
    force=True,
)
for _noisy in ("httpx", "httpcore"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

env = Environment(name="browser")  # literal name — `hud deploy` static-parses it (15.J)

# ── substrate layout ─────────────────────────────────────────────────────────
_HOST = "127.0.0.1"
_VNC_PORT = 5900   # x11vnc serves the :1 desktop here (-rfbport 5900 -> rfb display 0)
_CDP_PORT = 9222   # BrowserOS remote-debugging port -> the cdp capability

# Each app is (name, frontend_port, backend_port). The frontends derive their backend as
# window.location.port + 1, so each backend is its frontend + 1 (consecutive); the CORS origin is
# the frontend port.
_APPS = (("2048", 3001, 3002), ("todo", 3003, 3004))
_APP_2048_URL = "http://localhost:3001"   # frontend the agent sees
_APP_2048_API = "http://localhost:3002"   # backend the grader reads
_APP_TODO_URL = "http://localhost:3003"
_APP_TODO_API = "http://localhost:3004"

_BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
_DESKTOP_USER = "ubuntu"
_http = httpx.AsyncClient(timeout=60.0)
_procs: "list[asyncio.subprocess.Process]" = []


# ── substrate lifecycle ──────────────────────────────────────────────────────
def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


async def _listening(host: str, port: int, what: str, timeout: float = 60.0) -> None:
    """Block until host:port accepts a connection."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if _port_open(host, port):
            return
        await asyncio.sleep(0.3)
    raise RuntimeError(f"{what} never came up on {host}:{port}")


def _drop_to_ubuntu() -> bool:
    """Run the substrate as the unprivileged ``ubuntu`` user when we can (root in the image and the
    user exists). Locally on a non-root dev box we run as ourselves."""
    if os.geteuid() != 0:
        return False
    try:
        pwd.getpwnam(_DESKTOP_USER)
    except KeyError:
        return False
    return True


async def _spawn(*cmd: str, cwd: "str | None" = None, quiet: bool = True) -> asyncio.subprocess.Process:
    """Spawn one substrate process, dropped to ``ubuntu`` in the image.

    A CLEAN system PATH (not root's) is used: root's PATH leaks /root/.local/bin (uv), which ubuntu
    finds but cannot execute (/root is 0700) — raising a PermissionError the app launcher would not
    survive — and every desktop/app binary we need is in /usr/bin anyway. ``quiet=False`` lets a
    process's stderr flow to ours (used for the apps, so a launch failure is visible)."""
    drop = _drop_to_ubuntu()
    keep = {
        "HOME": "/home/ubuntu" if drop else os.environ.get("HOME", "/root"),
        "DISPLAY": ":1",
        "BROWSEROS_BIN": os.environ.get("BROWSEROS_BIN", "/usr/bin/browseros"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }
    argv = (
        ["sudo", "-u", _DESKTOP_USER, "env", *[f"{k}={v}" for k, v in keep.items()], *cmd]
        if drop
        else list(cmd)
    )
    return await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        env={**os.environ, **keep},
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL if quiet else None,
    )


async def _start_substrate() -> None:
    """Launch the desktop + both apps as subprocesses (cua-template style), then block until every
    port is up. ``python3 -m uvicorn`` puts the backend's cwd on sys.path, so ``main`` / ``game``
    import with no PYTHONPATH; the Next.js frontends are served from their pre-built ``.next``."""
    _procs.append(await _spawn("Xvfb", ":1", "-screen", "0", "1280x800x24"))
    await asyncio.sleep(0.8)  # let the X server come up before clients attach
    _procs.append(
        await _spawn("x11vnc", "-display", ":1", "-rfbport", str(_VNC_PORT),
                     "-forever", "-shared", "-nopw", "-localhost")
    )
    if shutil.which("websockify"):  # optional noVNC viewer on :8080
        _procs.append(
            await _spawn("websockify", "--web", "/usr/share/novnc", "8080", f"localhost:{_VNC_PORT}")
        )
    _procs.append(
        await _spawn("browseros", f"--remote-debugging-port={_CDP_PORT}", "--no-sandbox",
                     "--disable-gpu", "--disable-dev-shm-usage", "--disable-web-security",
                     "--no-first-run", "--window-size=1280,800", "about:blank")
    )
    for name, fe, be in _APPS:
        app = os.path.join(_BACKEND_DIR, name)
        # backend: system python (no uv); frontend: the pre-built production Next.js server.
        _procs.append(
            await _spawn("python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0",
                         "--port", str(be), cwd=os.path.join(app, "backend"), quiet=False)
        )
        _procs.append(
            await _spawn("npm", "run", "start", "--", "--port", str(fe), "--hostname", "0.0.0.0",
                         cwd=os.path.join(app, "frontend"), quiet=False)
        )
    await _listening(_HOST, _VNC_PORT, "x11vnc")
    await _listening(_HOST, _CDP_PORT, "BrowserOS CDP")
    for name, fe, be in _APPS:
        await _listening(_HOST, be, f"{name} backend")
        await _listening(_HOST, fe, f"{name} frontend")


async def _navigate(url: str) -> None:
    """Point the shared browser at ``url`` (env-side) so the agent starts on the app. Best-effort:
    the prompt also names the URL, so if this fails the agent simply navigates there itself."""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://{_HOST}:{_CDP_PORT}")
            try:
                ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
                page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            finally:
                await browser.close()  # detaches; the external BrowserOS keeps running
    except Exception as e:
        logger.warning("pre-navigation to %s failed (agent will navigate): %s", url, e)


@env.initialize
async def _up() -> None:
    """Launch the substrate (idempotent — skip if a desktop already serves) and publish both browser
    capabilities. The desktop + apps boot in a few seconds, well under the startup probe."""
    if not _port_open(_HOST, _VNC_PORT):
        logger.info("launching browser substrate")
        await _start_substrate()
    else:
        await _listening(_HOST, _VNC_PORT, "x11vnc")
    # Publish the SAME browser two ways: rfb (display 0 -> VNC 5900) + cdp (DevTools on 9222).
    env.add_capability(Capability.rfb(name="screen", url=f"rfb://{_HOST}", display=0))
    env.add_capability(Capability.cdp(name="browser", url=f"http://{_HOST}:{_CDP_PORT}"))


@env.shutdown
async def _down() -> None:
    logger.info("browser env shutting down")
    for proc in reversed(_procs):
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
    _procs.clear()
    await _http.aclose()


# ── 2048 game tasks ──────────────────────────────────────────────────────────
@env.template(id="2048-reach-tile")
async def reach_tile(target: int = 512, board_size: int = 4):
    """Play 2048 toward a target tile — logarithmic partial credit."""
    await _http.post(
        f"{_APP_2048_API}/api/game/new", json={"board_size": board_size, "target_tile": target}
    )
    await _navigate(_APP_2048_URL)
    prompt = (
        f"Play the 2048 game in the browser and reach the {target} tile.\n\n"
        f"The game is open at {_APP_2048_URL}. Move the tiles with the arrow keys "
        f"(up / down / left / right); two tiles with the same number merge into one. Keep your "
        f"highest tile in a corner and keep going until you reach {target} or no moves remain."
    )
    _ = yield prompt
    try:
        state = (await _http.get(f"{_APP_2048_API}/api/game/state")).json()
        highest, score = state.get("highest_tile", 0), state.get("score", 0)
        if score == 0 or highest <= 1 or target <= 1:
            reward = 0.0
        else:
            reward = min(1.0, math.log(highest) / math.log(target))
        logger.info("2048-reach-tile: highest=%d target=%d reward=%.2f", highest, target, reward)
        yield reward
    except Exception as e:
        logger.error("2048-reach-tile grading failed: %s", e)
        yield 0.0


@env.template(id="2048-near-win")
async def near_win(target: int = 2048):
    """Start one merge away from the target and finish the game — binary reward."""
    target = int(target)
    if target == 2048:
        board = [[1024, 1024, 256, 128], [512, 256, 64, 32], [128, 64, 16, 8], [32, 16, 4, 2]]
    elif target == 1024:
        board = [[512, 512, 128, 64], [256, 128, 32, 16], [64, 32, 8, 4], [16, 8, 2, 0]]
    else:
        half, quarter = target // 2, target // 4
        board = [
            [half, half, quarter, quarter // 2],
            [quarter, quarter // 2, 16, 8],
            [16, 8, 4, 2],
            [4, 2, 0, 0],
        ]
    await _http.post(
        f"{_APP_2048_API}/api/eval/set_board",
        json={"board": board, "score": sum(sum(row) for row in board) * 2, "moves": 150},
    )
    await _navigate(_APP_2048_URL)
    prompt = (
        f"You are one move away from winning! Reach the {target} tile.\n\n"
        f"The game is open at {_APP_2048_URL} with two {target // 2} tiles ready to merge. "
        f"Make the winning move with the arrow keys."
    )
    _ = yield prompt
    try:
        state = (await _http.get(f"{_APP_2048_API}/api/game/state")).json()
        won = state.get("won", False) or state.get("highest_tile", 0) >= target
        yield 1.0 if won else 0.0
    except Exception as e:
        logger.error("2048-near-win grading failed: %s", e)
        yield 0.0


@env.template(id="2048-score")
async def reach_score(target_score: int = 5000):
    """Play 2048 toward a target score — linear partial credit."""
    await _http.post(f"{_APP_2048_API}/api/game/new", json={})
    await _navigate(_APP_2048_URL)
    prompt = (
        f"Play 2048 and reach a score of {target_score}.\n\n"
        f"The game is open at {_APP_2048_URL}. Move with the arrow keys and merge tiles "
        f"efficiently to raise your score as high as you can."
    )
    _ = yield prompt
    try:
        state = (await _http.get(f"{_APP_2048_API}/api/game/state")).json()
        score = state.get("score", 0)
        yield min(1.0, score / target_score) if target_score > 0 else 0.0
    except Exception as e:
        logger.error("2048-score grading failed: %s", e)
        yield 0.0


# ── todo app tasks ───────────────────────────────────────────────────────────
@env.template(id="todo-complete")
async def complete_todos(expected_count: int = 3):
    """Mark a number of seeded todos complete — count-based partial credit."""
    await _http.post(f"{_APP_TODO_API}/api/eval/seed")
    await _navigate(_APP_TODO_URL)
    prompt = (
        f"Mark {expected_count} todo items as complete.\n\n"
        f"The todo app is open at {_APP_TODO_URL}. Click a todo's checkbox to complete it; "
        f"keep going until {expected_count} items are done."
    )
    _ = yield prompt
    try:
        stats = (await _http.get(f"{_APP_TODO_API}/api/eval/stats")).json()
        completed = stats.get("completed_items", 0)
        if completed >= expected_count:
            reward = 1.0
        elif expected_count > 0:
            reward = completed / expected_count
        else:
            reward = 0.0
        logger.info("todo-complete: completed=%d expected=%d reward=%.2f",
                    completed, expected_count, reward)
        yield reward
    except Exception as e:
        logger.error("todo-complete grading failed: %s", e)
        yield 0.0


@env.template(id="todo-create")
async def create_todo(title: str):
    """Create a new todo with an exact title — binary reward."""
    await _http.delete(f"{_APP_TODO_API}/api/eval/reset")
    await _navigate(_APP_TODO_URL)
    prompt = (
        f'Create a new todo item with the title: "{title}"\n\n'
        f"The todo app is open at {_APP_TODO_URL}. Type the title into the new-todo input and "
        f"submit it. The title must be exactly: {title}"
    )
    _ = yield prompt
    try:
        todos = (await _http.get(f"{_APP_TODO_API}/api/eval/todos")).json()
        exists = any(todo.get("title") == title for todo in todos)
        yield 1.0 if exists else 0.0
    except Exception as e:
        logger.error("todo-create grading failed: %s", e)
        yield 0.0


@env.template(id="todo-completion-rate")
async def completion_rate(target_rate: float = 0.5):
    """Complete a fraction of the seeded todos — ratio-based partial credit."""
    await _http.post(f"{_APP_TODO_API}/api/eval/seed")
    await _navigate(_APP_TODO_URL)
    pct = int(target_rate * 100)
    prompt = (
        f"Complete at least {pct}% of the todo items.\n\n"
        f"The todo app is open at {_APP_TODO_URL}. Mark enough items done to reach {pct}% "
        f"completion of the list."
    )
    _ = yield prompt
    try:
        stats = (await _http.get(f"{_APP_TODO_API}/api/eval/stats")).json()
        total, completed = stats.get("total_items", 0), stats.get("completed_items", 0)
        actual = completed / total if total > 0 else 0.0
        yield min(1.0, actual / target_rate) if target_rate > 0 else 1.0
    except Exception as e:
        logger.error("todo-completion-rate grading failed: %s", e)
        yield 0.0

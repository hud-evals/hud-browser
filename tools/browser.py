"""Browser interaction tools - Playwright and computer tools."""
import contextlib
import logging
import sys
import time

import httpx

from hud.server import MCPRouter
from hud.tools import PlaywrightTool, HudComputerTool, AnthropicComputerTool, OpenAIComputerTool

logger = logging.getLogger(__name__)

router = MCPRouter()

# Backend connection
BACKEND_URL = "http://localhost:8000"
http_client = httpx.AsyncClient(
    base_url=BACKEND_URL, timeout=30.0, headers={"User-Agent": "HUD-Browser/1.0"}
)


def _discover_cdp_url(timeout_sec: float = 60.0, poll_interval_sec: float = 0.5) -> str | None:
    """Synchronously poll the backend for a CDP websocket URL."""
    deadline = time.time() + timeout_sec
    with contextlib.redirect_stdout(sys.stderr):
        try:
            with httpx.Client(base_url=BACKEND_URL, timeout=5.0) as client:
                while time.time() < deadline:
                    try:
                        resp = client.get("/cdp")
                        if resp.status_code == 200:
                            ws = resp.json().get("ws")
                            if ws:
                                return ws
                    except Exception:
                        pass
                    time.sleep(poll_interval_sec)
                    logger.info("Polling for CDP URL...")
        except Exception:
            raise
    return None


# Playwright tool with CDP connection
playwright = PlaywrightTool(cdp_url=_discover_cdp_url())

# Register tools with router
router.tool(playwright)
router.tool(HudComputerTool(display_num=1))
router.tool(AnthropicComputerTool(display_num=1))
router.tool(OpenAIComputerTool(display_num=1))

__all__ = ["router", "http_client", "BACKEND_URL", "playwright"]

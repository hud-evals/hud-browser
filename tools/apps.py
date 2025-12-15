"""App management tools - launching and interacting with apps."""
import asyncio
import logging

import httpx

from hud.server import MCPRouter
from tools.browser import http_client, BACKEND_URL, playwright

logger = logging.getLogger(__name__)

router = MCPRouter()


@router.tool
async def launch_app(app_name: str) -> str:
    """Launch a specific application dynamically and navigate to it.

    Args:
        app_name: Name of the app to launch (e.g., 'todo', '2048')

    Returns:
        Success message with app URL
    """
    try:
        response = await http_client.post(
            "/apps/launch",
            json={"app_name": app_name},
            timeout=60.0,
        )

        if response.status_code == 404:
            return f"App '{app_name}' not found"
        elif response.status_code != 200:
            return f"Failed to launch app: {response.text}"
    except httpx.ReadTimeout:
        return f"Timeout launching app '{app_name}'. Try again in a few seconds."
    except httpx.ConnectError:
        return f"Could not connect to backend at {BACKEND_URL}"
    except Exception as e:
        return f"Error launching app '{app_name}': {str(e)}"

    app_info = response.json()
    app_url = app_info["url"]

    # Navigate to the app
    try:
        await playwright(action="navigate", url=app_url, wait_for_load_state="networkidle")
        await asyncio.sleep(1)
        return f"Launched {app_name} at {app_url}"
    except Exception as e:
        logger.warning("Could not auto-navigate to app: %s", e)
        return f"Launched {app_name} at {app_url} (navigation failed: {e})"


@router.tool
async def api_request(url: str, method: str = "GET", data: dict | None = None) -> dict:
    """Make HTTP API requests.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, etc.)
        data: Optional JSON data for POST/PUT requests

    Returns:
        Response data as dict
    """
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, json=data)
        return {
            "status": response.status_code,
            "data": response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text,
        }


__all__ = ["router", "launch_app", "api_request"]

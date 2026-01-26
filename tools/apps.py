"""App management tools - launching and interacting with apps."""
import asyncio
import logging

import httpx

from hud.server import MCPRouter
from tools.browser import http_client, BACKEND_URL, playwright

logger = logging.getLogger(__name__)

router = MCPRouter()


async def _launch_app_internal(app_name: str) -> dict:
    """Internal function to launch an app and navigate to it.

    Args:
        app_name: Name of the app to launch (e.g., 'todo', '2048')

    Returns:
        Dict with app info (name, url, frontend_port, backend_port)

    Raises:
        ValueError: If app not found
        RuntimeError: If launch fails
        TimeoutError: If launch times out
        ConnectionError: If cannot connect to backend
    """
    try:
        response = await http_client.post(
            "/apps/launch",
            json={"app_name": app_name},
            timeout=60.0,
        )

        if response.status_code == 404:
            raise ValueError(f"App '{app_name}' not found")
        elif response.status_code != 200:
            raise RuntimeError(f"Failed to launch app: {response.text}")
    except httpx.ReadTimeout:
        raise TimeoutError(f"Timeout launching app '{app_name}'. Try again in a few seconds.")
    except httpx.ConnectError:
        raise ConnectionError(f"Could not connect to backend at {BACKEND_URL}")

    app_info = response.json()
    app_url = app_info["url"]

    # Navigate to the app
    try:
        await playwright(action="navigate", url=app_url, wait_for_load_state="networkidle")
        await asyncio.sleep(1)
    except Exception as e:
        logger.warning("Could not auto-navigate to app: %s", e)

    return app_info


@router.tool
async def launch_app(app_name: str) -> str:
    """Launch a specific application dynamically and navigate to it.

    Args:
        app_name: Name of the app to launch (e.g., 'todo', '2048')

    Returns:
        Success message with app URL
    """
    try:
        app_info = await _launch_app_internal(app_name)
        return f"Launched {app_name} at {app_info['url']}"
    except (ValueError, RuntimeError, TimeoutError, ConnectionError) as e:
        return str(e)
    except Exception as e:
        return f"Error launching app '{app_name}': {str(e)}"


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


__all__ = ["router", "launch_app", "_launch_app_internal", "api_request"]

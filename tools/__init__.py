"""Browser environment tools.

Each module exports a router that can be included in the main env.
"""
from tools.browser import router as browser_router
from tools.apps import router as apps_router

__all__ = ["browser_router", "apps_router"]

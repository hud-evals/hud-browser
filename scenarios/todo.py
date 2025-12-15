"""Todo app scenarios - create, complete, and manage todos."""
import logging
from typing import Any

from tools.browser import http_client

logger = logging.getLogger(__name__)


def register_scenarios(env: Any) -> None:
    """Register todo app scenarios with the environment."""
    
    @env.scenario("todo-complete")
    async def complete_todos(expected_count: int = 3) -> Any:
        """Mark todos as complete.
        
        Args:
            expected_count: Number of todos that should be completed
        """
        # Setup: Launch app and seed with todos
        response = await http_client.post("/apps/launch", json={"app_name": "todo"})
        if response.status_code != 200:
            logger.error("Failed to launch todo: %s", response.text)
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5000)
        
        # Seed with test todos
        await http_client.post(f"http://localhost:{backend_port}/api/eval/seed")
        
        logger.info("Todo scenario started: complete %d todos", expected_count)
        
        prompt = f"""Complete {expected_count} todo items in the list.

Use the browser to:
1. Take a screenshot to see the todo list
2. Click on todo items to mark them as complete
3. Continue until {expected_count} items are marked done

Start by taking a screenshot."""
        
        _ = yield prompt
        
        # Evaluate
        try:
            stats_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/stats")
            stats = stats_response.json()
            completed = stats.get("completed_items", 0)
            
            if completed >= expected_count:
                reward = 1.0
            elif expected_count > 0:
                reward = completed / expected_count
            else:
                reward = 0.0
                
            logger.info("Todo result: completed=%d, expected=%d, reward=%.2f", completed, expected_count, reward)
            yield reward
        except Exception as e:
            logger.error("Todo evaluation failed: %s", e)
            yield 0.0
    
    @env.scenario("todo-create")
    async def create_todo(title: str) -> Any:
        """Create a new todo item with a specific title.
        
        Args:
            title: The exact title the new todo should have
        """
        # Setup: Launch app with empty state
        response = await http_client.post("/apps/launch", json={"app_name": "todo"})
        if response.status_code != 200:
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5000)
        
        # Reset to empty
        await http_client.delete(f"http://localhost:{backend_port}/api/eval/reset")
        
        logger.info("Todo create scenario: title='%s'", title)
        
        prompt = f"""Create a new todo item with the title: "{title}"

Use the browser to:
1. Take a screenshot to see the todo app
2. Find the input field for new todos
3. Type the title and submit

The todo title must be exactly: {title}"""
        
        _ = yield prompt
        
        # Evaluate
        try:
            todos_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/todos")
            todos = todos_response.json()
            exists = any(todo.get("title") == title for todo in todos)
            yield 1.0 if exists else 0.0
        except Exception:
            yield 0.0
    
    @env.scenario("todo-completion-rate")
    async def completion_rate(target_rate: float = 0.5) -> Any:
        """Complete a percentage of seeded todos.
        
        Args:
            target_rate: Target completion rate (0.0 to 1.0)
        """
        # Setup
        response = await http_client.post("/apps/launch", json={"app_name": "todo"})
        if response.status_code != 200:
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5000)
        
        await http_client.post(f"http://localhost:{backend_port}/api/eval/seed")
        
        pct = int(target_rate * 100)
        prompt = f"""Complete at least {pct}% of the todo items in the list.

Use the browser to view and complete todo items.
You need to mark enough items as done to reach {pct}% completion."""
        
        _ = yield prompt
        
        # Evaluate
        try:
            stats_response = await http_client.get(f"http://localhost:{backend_port}/api/eval/stats")
            stats = stats_response.json()
            total = stats.get("total_items", 0)
            completed = stats.get("completed_items", 0)
            
            actual_rate = completed / total if total > 0 else 0.0
            reward = min(1.0, actual_rate / target_rate) if target_rate > 0 else 1.0
            yield reward
        except Exception:
            yield 0.0

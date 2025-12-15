"""2048 game scenarios - reach target tiles, achieve scores, etc."""
import logging
import math
from typing import Any

from tools.browser import http_client

logger = logging.getLogger(__name__)

# System prompt for 2048 game agents
GAME_2048_SYSTEM_PROMPT = """You are an expert 2048 game player using a browser interface.

HOW 2048 WORKS:
- 4x4 grid with numbered tiles (2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048...)
- When you move, all tiles slide in that direction
- When two tiles with SAME number touch, they merge (2+2=4, 4+4=8, etc.)
- After each move, a new tile (2 or 4) appears randomly
- Game ends when grid is full and no merges possible

BROWSER INTERACTION:
1. First, take a screenshot to see the board
2. Make moves using arrow keys: up, down, left, right
3. Continue until you reach the target or game ends

Strategy: keep highest tiles in a corner; maintain order; avoid random moves."""


def register_scenarios(env: Any) -> None:
    """Register 2048 game scenarios with the environment."""
    
    @env.scenario("2048-reach-tile")
    async def reach_tile(target: int = 512, board_size: int = 4) -> Any:
        """Play 2048 and try to reach the target tile.
        
        Args:
            target: Target tile value to reach (e.g., 512, 1024, 2048)
            board_size: Size of the game board (default: 4)
        """
        # Setup: Launch app and initialize game
        response = await http_client.post("/apps/launch", json={"app_name": "2048"})
        if response.status_code != 200:
            logger.error("Failed to launch 2048: %s", response.text)
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5001)
        
        # Initialize new game
        await http_client.post(
            f"http://localhost:{backend_port}/api/game/new",
            json={"board_size": board_size, "target_tile": target}
        )
        
        logger.info("2048 scenario started: target=%d, board=%dx%d", target, board_size, board_size)
        
        # Yield prompt
        prompt = f"""Play the 2048 game and try to reach the {target} tile.

Use the computer tool to:
1. Take a screenshot to see the current board
2. Press arrow keys (up, down, left, right) to make moves
3. Continue until you reach {target} or the game ends

Start by taking a screenshot."""
        
        _ = yield prompt
        
        # Evaluate: Check highest tile reached
        try:
            state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
            state_response.raise_for_status()
            game_state = state_response.json()
            
            highest_tile = game_state.get("highest_tile", 0)
            score = game_state.get("score", 0)
            
            # Logarithmic reward scaling
            if score == 0:
                reward = 0.0
            elif target > 1 and highest_tile > 1:
                reward = min(1.0, math.log(highest_tile) / math.log(target))
            else:
                reward = 0.0
                
            logger.info("2048 result: highest=%d, target=%d, reward=%.2f", highest_tile, target, reward)
            yield reward
            
        except Exception as e:
            logger.error("2048 evaluation failed: %s", e)
            yield 0.0
    
    @env.scenario("2048-near-win")
    async def near_win(target: int = 2048) -> Any:
        """Start with a near-winning board and finish the game.
        
        Args:
            target: Target tile to reach (board is set up one merge away)
        """
        # Setup: Launch app
        response = await http_client.post("/apps/launch", json={"app_name": "2048"})
        if response.status_code != 200:
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5001)
        
        # Create near-win board
        if target == 2048:
            board = [[1024, 1024, 256, 128], [512, 256, 64, 32], [128, 64, 16, 8], [32, 16, 4, 2]]
        elif target == 1024:
            board = [[512, 512, 128, 64], [256, 128, 32, 16], [64, 32, 8, 4], [16, 8, 2, 0]]
        else:
            half = target // 2
            quarter = target // 4
            board = [
                [half, half, quarter, quarter // 2],
                [quarter, quarter // 2, 16, 8],
                [16, 8, 4, 2],
                [4, 2, 0, 0],
            ]
        
        await http_client.post(
            f"http://localhost:{backend_port}/api/eval/set_board",
            json={"board": board, "score": sum(sum(row) for row in board) * 2, "moves": 150}
        )
        
        logger.info("2048 near-win scenario: target=%d", target)
        
        prompt = f"""You're one move away from winning! Reach the {target} tile.

The board is set up with two {target // 2} tiles ready to merge.
Use arrow keys to make the winning move.

Take a screenshot first to see the board."""
        
        _ = yield prompt
        
        # Evaluate
        try:
            state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
            game_state = state_response.json()
            won = game_state.get("won", False) or game_state.get("highest_tile", 0) >= target
            yield 1.0 if won else 0.0
        except Exception:
            yield 0.0
    
    @env.scenario("2048-score")
    async def reach_score(target_score: int = 5000) -> Any:
        """Play 2048 and try to reach a target score.
        
        Args:
            target_score: Target score to reach
        """
        # Setup
        response = await http_client.post("/apps/launch", json={"app_name": "2048"})
        if response.status_code != 200:
            yield 0.0
            return
            
        app_info = response.json()
        backend_port = app_info.get("backend_port", 5001)
        
        await http_client.post(f"http://localhost:{backend_port}/api/game/new", json={})
        
        prompt = f"""Play 2048 and try to reach a score of {target_score}.

Use the computer tool to take screenshots and make moves with arrow keys.
Focus on efficient tile merging to maximize your score."""
        
        _ = yield prompt
        
        # Evaluate
        try:
            state_response = await http_client.get(f"http://localhost:{backend_port}/api/game/state")
            game_state = state_response.json()
            score = game_state.get("score", 0)
            reward = min(1.0, score / target_score) if target_score > 0 else 0.0
            yield reward
        except Exception:
            yield 0.0

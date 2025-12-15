"""Local test script for the browser environment.

Development workflow (Docker with hot-reload):
1. Build: hud build
2. Start: hud dev -w scenarios -w tools --port 8765
3. Test: python local_test.py

The container runs the environment with tools/scenarios.
This script connects to it and runs agent evaluations.
"""
import asyncio
import os

import hud
from hud import Environment
from hud.agents import OpenAIChatAgent
from hud.settings import settings
from openai import AsyncOpenAI

# Use HUD inference gateway - see all models at https://hud.ai/models
client = AsyncOpenAI(base_url="https://inference.hud.ai", api_key=settings.api_key)

# Connect to running container (scenarios/tools are defined there)
DEV_URL = os.getenv("HUD_DEV_URL", "http://localhost:8765/mcp")

env = Environment("browser")
env.connect_url(DEV_URL)


async def test_tools_standalone():
    """Test environment tools directly."""
    print("=== Test 1: Standalone Tools ===")

    async with env:
        print(f"Tools: {[t.name for t in env.as_tools()]}")
        # Note: Most tools require the backend to be running


async def test_2048_scenario():
    """Test 2048 scenario with manual OpenAI calls."""
    print("\n=== Test 2: 2048 Scenario (Manual Agent Loop) ===")

    task = env("2048-reach-tile", target=64)

    async with hud.eval(task) as ctx:
        messages = [{"role": "user", "content": ctx.prompt}]

        while True:
            response = await client.chat.completions.create(
                model="gpt-4o",  # https://hud.ai/models
                messages=messages,
                tools=ctx.as_openai_chat_tools(),
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                break

            messages.append(msg)
            for tc in msg.tool_calls:
                result = await ctx.call_tool(tc)
                messages.append(result)


async def test_todo_scenario():
    """Test todo scenario with OpenAIChatAgent."""
    print("\n=== Test 3: Todo Scenario ===")

    task = env("todo-complete", expected_count=2)

    async with hud.eval(task) as ctx:
        agent = OpenAIChatAgent.create(model="gpt-4o")  # https://hud.ai/models
        await agent.run(ctx)


async def test_custom_board():
    """Test 2048 with custom board state."""
    print("\n=== Test 4: Custom Board Scenario ===")

    # Start with a board that has 256 in the corner
    task = env("2048-custom-board",
        board=[[256, 128, 64, 32], [128, 64, 32, 16], [64, 32, 16, 8], [0, 0, 4, 2]],
        goal_tile=512,
    )

    async with hud.eval(task) as ctx:
        agent = OpenAIChatAgent.create(model="gpt-4o")  # https://hud.ai/models
        await agent.run(ctx, max_steps=15)


async def test_distribution():
    """Test multiple tasks with variants and groups for A/B testing."""
    print("\n=== Test 5: Distribution (Variants + Groups) ===")

    tasks = [
        env("2048-reach-tile", target=64),
        env("todo-complete", expected_count=2),
    ]
    variants = {"model": ["gpt-4o-mini", "gpt-4o"]}
    group = 2

    async with hud.eval(tasks, variants=variants, group=group) as ctx:
        agent = OpenAIChatAgent.create(model=ctx.variants["model"])
        await agent.run(ctx, max_steps=20)


async def main():
    print("Browser Environment - Local Test")
    print("=" * 50)
    print(f"Container URL: {DEV_URL}")
    print("Make sure the container is running:")
    print("  hud dev -w scenarios -w tools --port 8765")
    print("=" * 50)
    print()

    await test_tools_standalone()
    # Uncomment to run scenarios:
    # await test_2048_scenario()
    # await test_todo_scenario()
    # await test_custom_board()
    # await test_distribution()


if __name__ == "__main__":
    asyncio.run(main())

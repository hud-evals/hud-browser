"""Local test script for the browser environment.

Prerequisites:
1. Run the backend: python -m uvicorn backend.server:app --port 8000
2. Run this script: python local_test.py

Note: The backend manages X11/VNC services and app launching.
"""
import asyncio

import hud
from hud.agents import OpenAIChatAgent
from hud.settings import settings
from openai import AsyncOpenAI

from env import env

# Use HUD inference gateway - see all models at https://hud.ai/models
client = AsyncOpenAI(base_url="https://inference.hud.ai", api_key=settings.api_key)


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


async def test_distribution():
    """Test multiple tasks with variants and groups for A/B testing."""
    print("\n=== Test 4: Distribution (Variants + Groups) ===")

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
    await test_tools_standalone()
    # Uncomment to run with backend:
    # await test_2048_scenario()
    # await test_todo_scenario()
    # await test_distribution()


if __name__ == "__main__":
    asyncio.run(main())

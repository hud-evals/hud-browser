"""Remote test script - Working with tasks from JSON and the platform.

This demonstrates the full workflow for remote evaluations:

1. Deploy your environment to hud.ai (New → Environment → Connect GitHub repo)
2. Create tasks from your scenarios on the platform
3. Run evaluations locally or at scale

## Option A: Run on Platform

Run evaluations at scale directly on hud.ai with parallel execution and automatic tracing.

## Option B: CLI Evaluation

Run evaluations with the HUD CLI:

    # From local JSON file
    hud eval ./remote_tasks.json --model gpt-4o --remote

    # From platform dataset
    hud eval my-org/browser --model gpt-4o --remote --group 5


## Option C: Python Script (this file)

    python remote_test.py

"""
import asyncio

import hud
from hud.agents import OpenAIChatAgent  # See all models: https://hud.ai/models
from hud.datasets import load_tasks, save_tasks

from env import env


async def test_from_json():
    """Load tasks from JSON and run locally."""
    print("=== Load from JSON ===")

    tasks = load_tasks("remote_tasks.json")

    # Bind to local environment and run
    bound_tasks = [env(t.scenario, **t.args) for t in tasks]

    async with hud.eval(bound_tasks) as ctx:
        agent = OpenAIChatAgent.create(model="gpt-4o")  # https://hud.ai/models
        await agent.run(ctx)


async def test_from_platform(slug: str = "my-org/browser"):
    """Load and run tasks from the HUD platform.
    
    After deploying your environment:
    1. Go to hud.ai → Environments → Your Environment
    2. Create tasks from your scenarios
    3. Use the dataset slug here
    """
    print(f"=== Load from Platform: {slug} ===")

    tasks = load_tasks(slug)

    async with hud.eval(tasks) as ctx:
        agent = OpenAIChatAgent.create(model="gpt-4o")  # https://hud.ai/models
        await agent.run(ctx)


async def upload_to_platform(slug: str = "my-org/browser"):
    """Upload local tasks to the platform.
    
    This creates a dataset on hud.ai that you can run at scale.
    """
    print(f"=== Upload to Platform: {slug} ===")

    tasks = load_tasks("remote_tasks.json")
    bound_tasks = [env(t.scenario, **t.args) for t in tasks]

    await save_tasks(slug, bound_tasks)
    print(f"Saved {len(tasks)} tasks → hud eval {slug} --model gpt-4o --remote")


async def main():
    # Run local JSON test by default
    await test_from_json()

    # Uncomment to test platform features:
    # await upload_to_platform("my-org/browser")
    # await test_from_platform("my-org/browser")


if __name__ == "__main__":
    asyncio.run(main())

"""
Verify the turn-based approach end-to-end.

Prerequisites:
  - ANTHROPIC_API_KEY (or your LLM key) set in environment
  - Temporal running: docker compose up -d
  - Worker running:   uv run python -m exoclaw_temporal.turn_based --worker

Run:
  uv run python examples/test_turn_based.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from exoclaw.agent.tools.registry import ToolRegistry
from exoclaw_temporal.config import LLMConfig, TurnInput, WorkspaceConfig
from exoclaw_temporal.turn_based.worker import TASK_QUEUE
from exoclaw_temporal.turn_based.workflows.agent_turn import AgentTurnWorkflow
from exoclaw_tools_workspace.filesystem import ListDirTool, ReadFileTool, WriteFileTool
from temporalio.client import Client


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workspace = Path("/tmp/exoclaw-temporal-example")
    workspace.mkdir(exist_ok=True)

    registry = ToolRegistry()
    for tool in [
        WriteFileTool(workspace=workspace),
        ReadFileTool(workspace=workspace),
        ListDirTool(workspace=workspace),
    ]:
        registry.register(tool)

    llm = LLMConfig(model="anthropic/claude-haiku-4-5-20251001")
    ws = WorkspaceConfig(path=str(workspace))

    async def turn(session_id: str, message: str, run_id: str) -> str | None:
        result = await client.execute_workflow(
            AgentTurnWorkflow.run,
            TurnInput(
                session_id=session_id,
                message=message,
                channel="cli",
                chat_id="direct",
                llm=llm,
                workspace=ws,
                tool_definitions_json=json.dumps(registry.get_definitions()),
            ),
            id=f"example-turn-{run_id}",
            task_queue=TASK_QUEUE,
        )
        return result.final_content

    print("\n=== Test 1: plain LLM call (no tools) ===")
    r = await turn("ex:1", "Say hello in exactly 5 words.", "1a")
    print("Response:", r)

    print("\n=== Test 2: tool call — write a file ===")
    r = await turn("ex:2", 'Write a file called greeting.txt containing "Hello from Temporal!"', "2a")
    print("Response:", r)
    print("File contents:", (workspace / "greeting.txt").read_text())

    print("\n=== Test 3: multi-turn memory ===")
    session = "ex:multiturn"
    r1 = await turn(session, "My favourite number is 42. Remember that.", "3a")
    print("Turn 1:", r1)
    r2 = await turn(session, "What is my favourite number?", "3b")
    print("Turn 2:", r2)
    assert "42" in (r2 or ""), f"Expected 42 in response, got: {r2}"
    print("✓ Memory persisted across workflow runs")

    print("\n=== All tests passed ===\n")


if __name__ == "__main__":
    asyncio.run(main())

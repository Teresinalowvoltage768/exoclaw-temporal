"""
Verify the session-based approach end-to-end.

Prerequisites:
  - ANTHROPIC_API_KEY (or your LLM key) set in environment
  - Temporal running: docker compose up -d
  - Worker running:   uv run python -m exoclaw_temporal.session_based --worker

Run:
  uv run python examples/test_session_based.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from exoclaw.agent.tools.registry import ToolRegistry
from exoclaw_temporal.config import LLMConfig, SessionInput, WorkspaceConfig
from exoclaw_temporal.session_based.worker import TASK_QUEUE
from exoclaw_temporal.session_based.workflows.agent_session import AgentSessionWorkflow
from exoclaw_tools_workspace.filesystem import ReadFileTool, WriteFileTool
from temporalio.client import Client


async def main() -> None:
    client = await Client.connect("localhost:7233")

    workspace = Path("/tmp/exoclaw-temporal-example")
    workspace.mkdir(exist_ok=True)

    registry = ToolRegistry()
    for tool in [WriteFileTool(workspace=workspace), ReadFileTool(workspace=workspace)]:
        registry.register(tool)

    llm = LLMConfig(model="anthropic/claude-haiku-4-5-20251001")
    ws = WorkspaceConfig(path=str(workspace))
    session_id = "session-example:1"

    # Start one long-running session workflow
    handle = await client.start_workflow(
        AgentSessionWorkflow.run,
        SessionInput(
            session_id=session_id,
            channel="cli",
            chat_id="direct",
            llm=llm,
            workspace=ws,
            tool_definitions_json=json.dumps(registry.get_definitions()),
        ),
        id=f"session-{session_id}",
        task_queue=TASK_QUEUE,
    )
    print(f"\nSession workflow started: {handle.id}")
    print("(Both turns signal the SAME workflow — no new workflow runs)\n")

    async def signal_and_wait(message: str) -> str | None:
        await handle.signal(AgentSessionWorkflow.send_message, message)
        await asyncio.sleep(1)
        while await handle.query(AgentSessionWorkflow.is_processing):
            await asyncio.sleep(0.5)
        return await handle.query(AgentSessionWorkflow.get_last_response)

    print("=== Turn 1: set context ===")
    r1 = await signal_and_wait("My favourite colour is blue. Remember it.")
    print("Response:", r1)

    print("\n=== Turn 2: recall from same workflow ===")
    r2 = await signal_and_wait("What is my favourite colour?")
    print("Response:", r2)
    assert "blue" in (r2 or "").lower(), f"Expected 'blue' in response, got: {r2}"
    print("✓ Context maintained within the session workflow")

    print("\n=== All tests passed ===\n")

    # Clean up — terminate the session workflow so it doesn't linger
    await handle.terminate(reason="example complete")


if __name__ == "__main__":
    asyncio.run(main())

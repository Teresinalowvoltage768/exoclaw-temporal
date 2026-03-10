"""Session-based app — one long-running workflow per session.

The CLI opens a session workflow and signals each message into it.
Responses are read back via workflow queries.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from loguru import logger
from temporalio.client import Client
from temporalio.service import RPCError

from exoclaw.agent.tools.registry import ToolRegistry
from exoclaw_nanobot import Config, load_config
from exoclaw_temporal.config import LLMConfig, SessionInput, WorkspaceConfig
from exoclaw_temporal.session_based.worker import TASK_QUEUE
from exoclaw_temporal.session_based.workflows.agent_session import AgentSessionWorkflow
from exoclaw_temporal.turn_based.app import (
    _build_tool_registry,
    _llm_config,
    _workspace_config,
)


class ExoclawTemporalSession:
    """Session-based durable agent. One workflow per session, messages as signals."""

    def __init__(
        self,
        client: Client,
        llm: LLMConfig,
        workspace: WorkspaceConfig,
        tool_definitions_json: str,
    ) -> None:
        self._client = client
        self._llm = llm
        self._workspace = workspace
        self._tool_definitions_json = tool_definitions_json

    async def _get_or_start_session(
        self, session_id: str, channel: str = "cli", chat_id: str = "direct"
    ) -> object:
        """Return handle to existing session workflow, or start a new one."""
        workflow_id = f"session-{session_id}"
        try:
            handle = self._client.get_workflow_handle(workflow_id)
            # Check it's still running
            await handle.describe()
            return handle
        except RPCError:
            pass

        # Start new session workflow
        handle = await self._client.start_workflow(
            AgentSessionWorkflow.run,
            SessionInput(
                session_id=session_id,
                channel=channel,
                chat_id=chat_id,
                llm=self._llm,
                workspace=self._workspace,
                tool_definitions_json=self._tool_definitions_json,
            ),
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )
        logger.info("Started session workflow {}", workflow_id)
        return handle

    async def chat(
        self,
        message: str,
        *,
        session_id: str,
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str | None:
        """Signal a message to the session workflow and wait for the response."""
        handle = await self._get_or_start_session(session_id, channel, chat_id)

        await handle.signal(AgentSessionWorkflow.send_message, message)  # type: ignore[attr-defined]

        # Poll until the workflow finishes processing
        while True:
            is_proc = await handle.query(AgentSessionWorkflow.is_processing)  # type: ignore[attr-defined]
            if not is_proc:
                break
            await asyncio.sleep(0.5)

        return await handle.query(AgentSessionWorkflow.get_last_response)  # type: ignore[attr-defined]

    async def run_cli(self) -> None:
        """Interactive REPL — messages signal the session workflow."""
        session_id = f"cli:{uuid.uuid4().hex[:8]}"
        logger.info("Session: {}  (Ctrl+C to exit)", session_id)
        print(f"\nExoclaw Temporal (session-based) — session {session_id}\n")

        while True:
            try:
                message = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not message:
                continue
            if message in ("/new", "/clear"):
                session_id = f"cli:{uuid.uuid4().hex[:8]}"
                print(f"New session: {session_id}\n")
                continue

            try:
                response = await self.chat(message, session_id=session_id)
                print(f"\nAgent: {response}\n")
            except Exception as exc:
                logger.error("Error: {}", exc)
                print(f"\nError: {exc}\n")


async def create(
    config: Config | None = None,
    *,
    config_path: Path | None = None,
    temporal_url: str = "localhost:7233",
) -> ExoclawTemporalSession:
    if config is None:
        config = load_config(config_path)

    client = await Client.connect(temporal_url)
    registry = _build_tool_registry(config)
    tool_definitions_json = json.dumps(registry.get_definitions())

    return ExoclawTemporalSession(
        client=client,
        llm=_llm_config(config),
        workspace=_workspace_config(config),
        tool_definitions_json=tool_definitions_json,
    )

"""Temporal worker for the session-based approach."""

from __future__ import annotations

import asyncio

from loguru import logger
from temporalio.client import Client
from temporalio.worker import Worker

from exoclaw_temporal.activities.conversation import build_prompt, record_turn
from exoclaw_temporal.activities.llm import llm_chat
from exoclaw_temporal.activities.tools import execute_tool
from exoclaw_temporal.session_based.workflows.agent_session import AgentSessionWorkflow

TASK_QUEUE = "exoclaw-session-based"


async def run_worker(temporal_url: str = "localhost:7233") -> None:
    logger.info("Connecting to Temporal at {}", temporal_url)
    client = await Client.connect(temporal_url)

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[AgentSessionWorkflow],
        activities=[build_prompt, llm_chat, execute_tool, record_turn],
    )

    logger.info("Worker started on task queue '{}'", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())

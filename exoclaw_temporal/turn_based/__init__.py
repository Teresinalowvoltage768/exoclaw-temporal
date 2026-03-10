"""Turn-based approach: one Temporal workflow per conversation turn.

Each user message triggers a fresh AgentTurnWorkflow. The workflow runs
the agent loop — LLM calls and tool calls — as Temporal activities. If any
worker pod dies mid-execution, Temporal retries that activity on any other
available worker. Workflow history acts as the checkpoint.

Conversation state persists between turns via the shared workspace volume
(PVC in k8s, local path in development). The JSONL session files written
by record_turn are available to any worker that mounts the volume.
"""

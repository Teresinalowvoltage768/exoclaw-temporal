# exoclaw-temporal

Exoclaw on [Temporal](https://temporal.io) — feature-complete AI agent with durable execution.

Everything [exoclaw-nanobot](https://github.com/Clause-Logic/exoclaw) can do, now unbreakable. Kill a worker pod mid-tool-call. Temporal reschedules on a surviving pod. The agent continues exactly where it left off.

## What's durable

| Operation | In nanobot | In exoclaw-temporal |
|---|---|---|
| LLM call | In-process, lost if process dies | Temporal activity, retried on any worker |
| Tool execution | In-process, lost if process dies | Temporal activity with heartbeat |
| Conversation history | JSONL on local disk | JSONL on shared PVC (any worker can read/write) |
| Cron jobs | File-backed, lost if process dies | Temporal Schedules (future) |
| Subagent spawn | Nested in-process loop | Child workflow (future) |

## Two approaches

### `turn_based/` — one workflow per message turn

Simplest mental model. Each user message starts a fresh `AgentTurnWorkflow`. The workflow runs the agent loop — LLM calls and tool calls — as activities. Conversation history is loaded from disk at the start of each turn and saved at the end.

```
User message → AgentTurnWorkflow → activities (LLM, tools) → response
```

Good for: most production use cases. Easy to reason about, easy to scale.

### `session_based/` — one long-running workflow per session

One `AgentSessionWorkflow` per conversation. New messages arrive as Temporal **Signals**. The workflow accumulates state across turns. After 50 turns it calls `continue_as_new` to keep workflow history bounded while conversation history stays in the external store.

```
User message → Signal → AgentSessionWorkflow → activities → Query for response
```

Good for: showing Temporal's Signal/Query/continue_as_new primitives. Sessions that receive messages from multiple sources (CLI + scheduled heartbeat + Slack) can all signal the same workflow ID.

## Running locally (no k8s)

```bash
# Start Temporal dev server (requires temporal CLI)
temporal server start-dev

# In another terminal — start a worker
mise run demo-turn --worker

# In another terminal — start the CLI
mise run demo-turn
```

## Running on kind (worker-bounce demo)

```bash
# Create 3-node cluster
mise run cluster-up

# Install Temporal
mise run temporal-up

# Build and deploy workers (2 replicas across 2 nodes)
mise run worker-deploy

# Run the bounce demo: kill a worker mid-execution, watch it resume
mise run bounce-demo
```

The bounce demo submits a turn with a slow shell command (`sleep 20`), then kills one worker pod. Temporal detects the heartbeat timeout (30s) and reschedules the tool activity on the surviving worker. The agent completes normally.

## Workspace durability

All state lives in the shared workspace volume:

```
/workspace/
├── sessions/           ← JSONL conversation history (read/write by any worker)
├── cron.json           ← Cron job state
└── history/            ← CLI REPL history
```

In kind: `hostPath` or `local-path-provisioner` (single-node access). For multi-node, use an NFS or EFS CSI driver with `ReadWriteMany`.

In production: replace `storageClassName: standard` in `k8s/worker/pvc.yaml` with your EFS provisioner.

## Architecture

```
                    ┌──────────────────────────────┐
                    │  Temporal Worker (2 replicas)  │
                    │  - AgentTurnWorkflow           │
                    │  - activities: llm_chat        │
                    │               execute_tool     │
                    │               build_prompt     │
                    │               record_turn      │
                    └──────────┬───────────────────┘
                               │ mount
                               ▼
                    ┌──────────────────────────────┐
                    │  Shared PVC (workspace)        │
                    │  sessions/, cron.json, etc.    │
                    └──────────────────────────────┘
```

## Config

Uses the same `~/.nanobot/config.json` as exoclaw-nanobot. No new config format.

```bash
# Point to a different config
exoclaw-temporal-turn --config /path/to/config.json

# Point to a non-local Temporal cluster
exoclaw-temporal-turn --temporal-url my-temporal.example.com:7233
```

"""Session-based approach: one long-running Temporal workflow per session.

New messages arrive as Temporal Signals. The workflow accumulates state
(messages, turn count) across multiple turns. When the history gets large,
the workflow calls continue_as_new to start fresh with a clean history
while persisting conversation state to the external store.

This approach shows Temporal's Signal and continue_as_new primitives.
The session workflow can accept messages concurrently from multiple
channels (CLI, Slack, heartbeat) all signaling the same workflow ID.
"""

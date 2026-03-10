"""Exoclaw on Temporal — durable AI agent execution.

Two approaches, same feature set as exoclaw-nanobot:

  turn_based/   — one Temporal workflow per message turn
                  simple, stateless workflows, easy to reason about

  session_based/ — one long-running workflow per session, new messages
                   arrive as Temporal signals, state lives in workflow history
"""

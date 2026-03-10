#!/usr/bin/env bash
# Demonstrate Temporal worker-bounce durability.
#
# 1. Start the agent with a long-running task (shell command with sleep)
# 2. Delete one worker pod mid-execution
# 3. Watch Temporal reschedule the activity on the surviving worker
# 4. Agent completes as if nothing happened
set -euo pipefail

echo "=== Exoclaw Temporal — Worker Bounce Demo ==="
echo ""

# Find the two worker pods
PODS=($(kubectl get pods -l app=exoclaw-temporal-worker -o name))
if [[ ${#PODS[@]} -lt 2 ]]; then
  echo "Error: need at least 2 worker pods running" >&2
  exit 1
fi

POD_TO_KILL="${PODS[0]#pod/}"
echo "Worker pods: ${PODS[*]}"
echo "Will kill: $POD_TO_KILL"
echo ""

# Submit a workflow that runs a slow shell command
echo "Submitting a turn that runs: sleep 20 && echo 'done'"
WORKFLOW_ID="bounce-demo-$(date +%s)"
temporal workflow start \
  --workflow-type AgentTurnWorkflow \
  --task-queue exoclaw-turn-based \
  --workflow-id "$WORKFLOW_ID" \
  --input '{
    "session_id": "bounce-demo",
    "message": "Run the shell command: sleep 20 && echo task complete",
    "channel": "cli",
    "chat_id": "demo"
  }'

echo ""
echo "Workflow started: $WORKFLOW_ID"
echo "Waiting 5s for activity to start on $POD_TO_KILL..."
sleep 5

echo ""
echo "Killing pod $POD_TO_KILL now..."
kubectl delete pod "$POD_TO_KILL" --grace-period=0 --force

echo ""
echo "Pod killed. Temporal will detect heartbeat loss within 30s and reschedule."
echo "Watching workflow until completion..."
echo ""

temporal workflow show --workflow-id "$WORKFLOW_ID" --follow

echo ""
echo "=== Demo complete. Workflow survived the worker bounce. ==="

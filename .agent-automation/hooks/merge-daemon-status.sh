#!/usr/bin/env bash
set -euo pipefail

command -v gh >/dev/null 2>&1 || {
  echo "Missing required command: gh" >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "Missing required command: jq" >&2
  exit 1
}

state_dir="${COORDINATOR_STATE_DIR:-${HOME}/.agent-automation/coordinator}"
echo "Agent Automation merge daemon status"
echo "State dir: ${state_dir}"
echo
echo "Open worker PRs:"
gh pr list --state open --json number,title,headRefName,url | jq '[.[] | select(.headRefName | startswith("agent/issue-"))]'
echo
echo "Blocker issues:"
gh issue list --state open --limit 100 --json number,title,labels,url | jq '[.[] | select(any(.labels[]?; .name == "needs-decision"))]'
echo
echo "Next launch candidates:"
"./.agent-automation/hooks/merge-daemon-launch-next.sh" --json | jq '.selected'

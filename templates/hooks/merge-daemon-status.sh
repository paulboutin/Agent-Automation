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
echo "=== Open worker PRs ==="
gh pr list --state open --json number,title,headRefName,url,createdAt,updatedAt | jq '[.[] | select(.headRefName | startswith("{{WORKER_BRANCH_PREFIX}}"))]'
echo
echo "=== Blocker issues ==="
gh issue list --state open --limit 100 --json number,title,labels,url | jq '[.[] | select(any(.labels[]?; .name == "{{NEEDS_DECISION_LABEL}}"))]'
echo
echo "=== Next launch candidates ==="
"./{{AUTOMATION_ROOT}}/hooks/merge-daemon-launch-next.sh" --json | jq '.selected'
echo
echo "=== PR Dependencies ==="
open_prs="$(gh pr list --state open --json number,title,headRefName,baseRefName,body,url,createdAt,updatedAt --limit 100 2>/dev/null || echo '[]')"
jq -n \
  --argjson prs "${open_prs}" '
  def extract_deps:
    .body // "" | capture("(?i)depends on:?\\s*(#|PR:?\\s*)(?<deps>[0-9a-zA-Z/-]+)") | .deps // "";
  {
    dependencies: ([
      $prs[] | select(.headRefName | startswith("{{WORKER_BRANCH_PREFIX}}")) | {
        number: .number,
        title: .title,
        branch: .headRefName,
        base: .baseRefName,
        depends_on: (extract_deps | select(length > 0))
      }
    ] | map(select(.depends_on != "")))
  }' | jq -c '.dependencies[]' 2>/dev/null || echo "  (none detected)"
echo
echo "=== Worker Heartbeat Status ==="
current_time_unix=$(date +%s)
jq -n \
  --argjson prs "${open_prs}" \
  --argjson now "${current_time_unix}" '
  def heartbeat_status:
    .updatedAt as $updated |
    (($updated | fromdateiso8601) | if . > 0 then . else 0 end) as $updated_epoch |
    (($now - $updated_epoch) | if . > 0 then . else 0 end) as $seconds |
    if $seconds < 3600 then "active"
    elif $seconds < 7200 then "recent"
    elif $seconds < 86400 then "stale"
    else "very-stale"
    end;
  {
    workers: ([
      $prs[] | select(.headRefName | startswith("{{WORKER_BRANCH_PREFIX}}")) | {
        number: .number,
        title: .title,
        branch: .headRefName,
        last_update: .updatedAt,
        status: heartbeat_status,
        seconds_idle: (($now - (.updatedAt | fromdateiso8601)) | if . > 0 then . else 0 end)
      }
    ])
  }' | jq '.workers[]' 2>/dev/null || echo "  (none active)"
echo
echo "=== Stale PR Detection (no activity > 48h) ==="
current_time_unix=$(date +%s)
jq -n \
  --argjson prs "${open_prs}" \
  --argjson now "${current_time_unix}" '
  def is_stale:
    .updatedAt as $updated |
    (($updated | fromdateiso8601) | if . > 0 then . else 0 end) as $updated_epoch |
    (($now - $updated_epoch) | if . > 0 then . else 0 end) > 172800;
  {
    stale: ([
      $prs[] | select(.headRefName | startswith("{{WORKER_BRANCH_PREFIX}}")) | select(is_stale) | {
        number: .number,
        title: .title,
        branch: .headRefName,
        last_update: .updatedAt,
        hours_idle: (((($now - (.updatedAt | fromdateiso8601)) | if . > 0 then . else 0 end) / 3600) | floor)
      }
    ])
  }' | jq '.stale[]' 2>/dev/null || echo "  (none detected)"
echo
echo "=== Local Worker Stale Detection ==="
"./{{AUTOMATION_ROOT}}/hooks/worker-stale-detect.sh"

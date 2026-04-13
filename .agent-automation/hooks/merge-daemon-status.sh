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

format_hours() {
  local total_seconds="${1:-0}"
  local hours=$((total_seconds / 3600))
  local minutes=$(((total_seconds % 3600) / 60))
  printf "%dh %02dm" "${hours}" "${minutes}"
}

print_widget_header() {
  local title="$1"
  echo "[$title]"
}

state_dir="${COORDINATOR_STATE_DIR:-${HOME}/.agent-automation/coordinator}"
run_dir="./.agent-automation/runs"
current_time_unix=$(date +%s)
stale_threshold_hours="${STALE_THRESHOLD_HOURS:-48}"
warning_threshold_hours="${WARNING_THRESHOLD_HOURS:-24}"

open_prs="$(gh pr list --state open --json number,title,headRefName,baseRefName,body,url,createdAt,updatedAt --limit 100 2>/dev/null || echo '[]')"
open_issues="$(gh issue list --state open --limit 200 --json number,title,labels,updatedAt,url 2>/dev/null || echo '[]')"
launch_plan="$("./.agent-automation/hooks/merge-daemon-launch-next.sh" --json 2>/dev/null || echo '{"selected":[],"candidates":[],"occupiedLanes":[]}')"

ready_issues="$(jq \
  '[.[] | select(any(.labels[]?; .name == "ready"))] | length' \
  <<< "${open_issues}")"
blocked_issues="$(jq \
  '[.[] | select(any(.labels[]?; .name == "needs-decision"))] | length' \
  <<< "${open_issues}")"
launch_candidates="$(jq '.selected | length' <<< "${launch_plan}")"
active_pr_count="$(jq \
  '[.[] | select(.headRefName | startswith("agent/issue-"))] | length' \
  <<< "${open_prs}")"

pr_dependency_rows="$(jq -r '
  def dependency_tokens:
    (.body // "")
    | [scan("(?i)depends on:?\\s*(?:#|PR:?\\s*)?([0-9]+|[A-Za-z0-9._/-]+)")[]];
  [
    .[]
    | select(.headRefName | startswith("agent/issue-"))
    | . as $pr
    | dependency_tokens[]
    | "\($pr.number)|\($pr.headRefName)|\(.)"
  ] | .[]?' <<< "${open_prs}")"
dependency_count="$(printf '%s\n' "${pr_dependency_rows}" | sed '/^$/d' | wc -l | tr -d ' ')"

heartbeat_rows=""
if [[ -d "${run_dir}" ]]; then
  for heartbeat_file in "${run_dir}"/heartbeat-*.json; do
    [[ -f "${heartbeat_file}" ]] || continue

    issue_number=$(jq -r '.issue // empty' "${heartbeat_file}" 2>/dev/null || true)
    branch=$(jq -r '.branch // empty' "${heartbeat_file}" 2>/dev/null || true)
    last_timestamp=$(jq -r '.timestamp // empty' "${heartbeat_file}" 2>/dev/null || true)
    last_status=$(jq -r '.status // "unknown"' "${heartbeat_file}" 2>/dev/null || true)

    [[ -n "${issue_number}" && -n "${last_timestamp}" ]] || continue

    last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${last_timestamp}" +%s 2>/dev/null || echo "0")
    if [[ "${last_epoch}" == "0" ]]; then
      last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp}" +%s 2>/dev/null || echo "0")
    fi
    [[ "${last_epoch}" != "0" ]] || continue

    idle_seconds=$((current_time_unix - last_epoch))
    idle_seconds=$((idle_seconds > 0 ? idle_seconds : 0))
    idle_hours=$((idle_seconds / 3600))

    severity="ok"
    if [[ "${last_status}" == "running" ]]; then
      if [[ ${idle_hours} -ge ${stale_threshold_hours} ]]; then
        severity="stale"
      elif [[ ${idle_hours} -ge ${warning_threshold_hours} ]]; then
        severity="warning"
      fi
    elif [[ "${last_status}" != "complete" && "${last_status}" != "completed" && "${last_status}" != "done" ]]; then
      severity="finished"
    fi

    heartbeat_rows+="${issue_number}|${branch}|${last_status}|${idle_seconds}|${last_timestamp}|${severity}"$'\n'
  done
fi

heartbeat_count="$(printf '%s\n' "${heartbeat_rows}" | sed '/^$/d' | wc -l | tr -d ' ')"
running_heartbeat_count="$(printf '%s\n' "${heartbeat_rows}" | awk -F'|' '$3 == "running" {count++} END {print count+0}')"
warning_heartbeat_count="$(printf '%s\n' "${heartbeat_rows}" | awk -F'|' '$6 == "warning" {count++} END {print count+0}')"
stale_heartbeat_count="$(printf '%s\n' "${heartbeat_rows}" | awk -F'|' '$6 == "stale" {count++} END {print count+0}')"
recent_heartbeat_count="$(printf '%s\n' "${heartbeat_rows}" | awk -F'|' '$3 == "running" && $4 < 3600 {count++} END {print count+0}')"

stale_pr_rows="$(jq -r \
  --argjson now "${current_time_unix}" \
  '[.[] | select(.headRefName | startswith("agent/issue-")) | . as $pr
    | (($now - (.updatedAt | fromdateiso8601)) | if . > 0 then . else 0 end) as $seconds
    | select($seconds > 172800)
    | "\($pr.number)|\($pr.headRefName)|\($seconds)|\($pr.updatedAt)"] | .[]?' \
  <<< "${open_prs}")"
stale_pr_count="$(printf '%s\n' "${stale_pr_rows}" | sed '/^$/d' | wc -l | tr -d ' ')"

echo "Agent Automation merge daemon status"
echo "State dir: ${state_dir}"
echo
echo "=== Daemon Dashboard ==="
print_widget_header "Queue Status"
echo "Ready issues: ${ready_issues}"
echo "Launch candidates: ${launch_candidates}"
echo "Blocked issues: ${blocked_issues}"
echo "Active worker PRs: ${active_pr_count}"
echo
print_widget_header "Active Workers"
if [[ "${running_heartbeat_count}" -gt 0 ]]; then
  while IFS='|' read -r issue_number branch status idle_seconds last_timestamp severity; do
    [[ "${status}" == "running" ]] || continue
    echo "- Issue #${issue_number} (${branch})"
    echo "  heartbeat: ${last_timestamp} | idle $(format_hours "${idle_seconds}")"
  done < <(printf '%s\n' "${heartbeat_rows}" | sort -t'|' -k4,4n)
else
  echo "No running worker heartbeats found."
fi
echo
print_widget_header "Stale Worker Detection"
echo "Warnings (>=${warning_threshold_hours}h): ${warning_heartbeat_count}"
echo "Stale heartbeats (>=${stale_threshold_hours}h): ${stale_heartbeat_count}"
echo "Stale PRs (>48h without updates): ${stale_pr_count}"
echo
print_widget_header "PR Dependency Graph"
if [[ "${dependency_count}" -gt 0 ]]; then
  while IFS='|' read -r pr_number branch dependency; do
    [[ -n "${pr_number}" ]] || continue
    echo "- PR #${pr_number} (${branch}) -> ${dependency}"
  done <<< "${pr_dependency_rows}"
else
  echo "No PR dependencies detected."
fi
echo
print_widget_header "Worker Heartbeat Summary"
echo "Tracked heartbeat files: ${heartbeat_count}"
echo "Running workers: ${running_heartbeat_count}"
echo "Healthy (<1h idle): ${recent_heartbeat_count}"
echo "Attention needed: $((warning_heartbeat_count + stale_heartbeat_count))"
echo
echo "=== Open worker PRs ==="
jq '[.[] | select(.headRefName | startswith("agent/issue-"))]' <<< "${open_prs}"
echo
echo "=== Blocker issues ==="
jq '[.[] | select(any(.labels[]?; .name == "needs-decision"))]' <<< "${open_issues}"
echo
echo "=== Next launch candidates ==="
jq '.selected' <<< "${launch_plan}"
echo
echo "=== PR Dependencies ==="
jq -n \
  --argjson prs "${open_prs}" '
  def extract_deps:
    .body // "" | capture("(?i)depends on:?\\s*(#|PR:?\\s*)(?<deps>[0-9a-zA-Z/-]+)") | .deps // "";
  {
    dependencies: ([
      $prs[] | select(.headRefName | startswith("agent/issue-")) | {
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
      $prs[] | select(.headRefName | startswith("agent/issue-")) | {
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
jq -n \
  --argjson prs "${open_prs}" \
  --argjson now "${current_time_unix}" '
  def is_stale:
    .updatedAt as $updated |
    (($updated | fromdateiso8601) | if . > 0 then . else 0 end) as $updated_epoch |
    (($now - $updated_epoch) | if . > 0 then . else 0 end) > 172800;
  {
    stale: ([
      $prs[] | select(.headRefName | startswith("agent/issue-")) | select(is_stale) | {
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
"./.agent-automation/hooks/worker-stale-detect.sh"

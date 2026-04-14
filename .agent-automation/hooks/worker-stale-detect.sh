#!/usr/bin/env bash
set -euo pipefail

source "./.agent-automation/hooks/agent-automation-common.sh"

format_duration() {
  local total_seconds="${1:-0}"
  local hours=$((total_seconds / 3600))
  local minutes=$(((total_seconds % 3600) / 60))
  local seconds=$((total_seconds % 60))
  if [[ ${hours} -gt 0 ]]; then
    printf "%dh %02dm" "${hours}" "${minutes}"
  else
    printf "%dm %02ds" "${minutes}" "${seconds}"
  fi
}

stale_threshold_hours="${STALE_THRESHOLD_HOURS:-48}"
warning_threshold_hours="${WARNING_THRESHOLD_HOURS:-24}"

echo "=== Worker Stale Detection ==="
echo "Stale threshold: ${stale_threshold_hours}h"
echo "Warning threshold: ${warning_threshold_hours}h"
echo

run_dir="./.agent-automation/runs"
if [[ ! -d "${run_dir}" ]]; then
  echo "No runs directory found: ${run_dir}"
  exit 0
fi

current_time=$(date +%s)

for heartbeat_file in "${run_dir}"/heartbeat-*.json; do
  [[ -f "${heartbeat_file}" ]] || continue
  
  issue_number=$(jq -r '.issue' "${heartbeat_file}" 2>/dev/null || echo "")
  branch=$(jq -r '.branch' "${heartbeat_file}" 2>/dev/null || echo "")
  last_timestamp=$(jq -r '.timestamp' "${heartbeat_file}" 2>/dev/null || echo "")
  last_status=$(jq -r '.status' "${heartbeat_file}" 2>/dev/null || echo "")
  started_at=$(jq -r '.started_at // empty' "${heartbeat_file}" 2>/dev/null || echo "")
  
  if [[ -z "${issue_number}" || -z "${last_timestamp}" ]]; then
    continue
  fi
  
  last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${last_timestamp}" +%s 2>/dev/null || echo "0")
  if [[ "${last_epoch}" == "0" ]]; then
    last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp}" +%s 2>/dev/null || echo "0")
  fi
  
  if [[ "${last_epoch}" == "0" ]]; then
    continue
  fi

  started_epoch=0
  if [[ -n "${started_at}" ]]; then
    started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${started_at}" +%s 2>/dev/null || echo "0")
    if [[ "${started_epoch}" == "0" ]]; then
      started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${started_at}" +%s 2>/dev/null || echo "0")
    fi
  fi
  if [[ "${started_epoch}" == "0" ]]; then
    started_epoch="${last_epoch}"
  fi

  duration_seconds=$((current_time - started_epoch))
  idle_seconds=$((current_time - last_epoch))
  idle_hours=$((idle_seconds / 3600))
  
  if [[ "${last_status}" == "running" ]]; then
    if [[ ${idle_hours} -ge ${stale_threshold_hours} ]]; then
      echo "STALE: Issue #${issue_number} (${branch}) - duration $(format_duration "${duration_seconds}")"
    elif [[ ${idle_hours} -ge ${warning_threshold_hours} ]]; then
      echo "WARNING: Issue #${issue_number} (${branch}) - duration $(format_duration "${duration_seconds}")"
    fi
  else
    echo "COMPLETED: Issue #${issue_number} (${branch}) - total $(format_duration "${duration_seconds}") - status: ${last_status}"
  fi
done

echo
echo "=== Active Workers (> 1h) ==="
for heartbeat_file in "${run_dir}"/heartbeat-*.json; do
  [[ -f "${heartbeat_file}" ]] || continue
  
  issue_number=$(jq -r '.issue' "${heartbeat_file}" 2>/dev/null || echo "")
  branch=$(jq -r '.branch' "${heartbeat_file}" 2>/dev/null || echo "")
  last_timestamp=$(jq -r '.timestamp' "${heartbeat_file}" 2>/dev/null || echo "")
  last_status=$(jq -r '.status' "${heartbeat_file}" 2>/dev/null || echo "")
  started_at=$(jq -r '.started_at // empty' "${heartbeat_file}" 2>/dev/null || echo "")
  
  if [[ -z "${issue_number}" || -z "${last_timestamp}" || "${last_status}" != "running" ]]; then
    continue
  fi
  
  last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${last_timestamp}" +%s 2>/dev/null || echo "0")
  if [[ "${last_epoch}" == "0" ]]; then
    last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp}" +%s 2>/dev/null || echo "0")
  fi
  
  if [[ "${last_epoch}" == "0" ]]; then
    continue
  fi

  started_epoch=0
  if [[ -n "${started_at}" ]]; then
    started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${started_at}" +%s 2>/dev/null || echo "0")
    if [[ "${started_epoch}" == "0" ]]; then
      started_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${started_at}" +%s 2>/dev/null || echo "0")
    fi
  fi
  if [[ "${started_epoch}" == "0" ]]; then
    started_epoch="${last_epoch}"
  fi

  duration_seconds=$((current_time - started_epoch))
  idle_seconds=$((current_time - last_epoch))
  idle_hours=$((idle_seconds / 3600))
  
  if [[ ${idle_hours} -lt 1 ]]; then
    echo "ACTIVE: Issue #${issue_number} (${branch}) - duration $(format_duration "${duration_seconds}")"
  fi
done

echo
echo "=== Summary ==="
total_heartbeats=$(ls -1 "${run_dir}"/heartbeat-*.json 2>/dev/null | wc -l | tr -d ' ')
running_workers=$(grep -l '"status": "running"' "${run_dir}"/heartbeat-*.json 2>/dev/null | wc -l | tr -d ' ')
stale_workers=$(for f in "${run_dir}"/heartbeat-*.json; do
  [[ -f "${f}" ]] || continue
  last_status=$(jq -r '.status' "${f}" 2>/dev/null || echo "")
  last_timestamp=$(jq -r '.timestamp' "${f}" 2>/dev/null || echo "")
  if [[ "${last_status}" == "running" && -n "${last_timestamp}" ]]; then
    last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "${last_timestamp}" +%s 2>/dev/null || echo "0")
    if [[ "${last_epoch}" == "0" ]]; then
      last_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${last_timestamp}" +%s 2>/dev/null || echo "0")
    fi
    if [[ "${last_epoch}" != "0" ]]; then
      idle_seconds=$((current_time - last_epoch))
      idle_hours=$((idle_seconds / 3600))
      if [[ ${idle_hours} -ge ${stale_threshold_hours} ]]; then
        echo "1"
      fi
    fi
  fi
done | wc -l | tr -d ' ')

echo "Total tracked: ${total_heartbeats:-0}"
echo "Running: ${running_workers:-0}"
echo "Stale (>$((stale_threshold_hours))h): ${stale_workers:-0}"

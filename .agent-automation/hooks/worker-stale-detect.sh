#!/usr/bin/env bash
set -euo pipefail

source "./.agent-automation/hooks/agent-automation-common.sh"

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
  
  idle_seconds=$((current_time - last_epoch))
  idle_hours=$((idle_seconds / 3600))
  
  if [[ "${last_status}" == "running" ]]; then
    if [[ ${idle_hours} -ge ${stale_threshold_hours} ]]; then
      echo "STALE: Issue #${issue_number} (${branch}) - ${idle_hours}h idle"
    elif [[ ${idle_hours} -ge ${warning_threshold_hours} ]]; then
      echo "WARNING: Issue #${issue_number} (${branch}) - ${idle_hours}h idle"
    fi
  else
    echo "COMPLETED: Issue #${issue_number} (${branch}) - status: ${last_status}"
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
  
  idle_seconds=$((current_time - last_epoch))
  idle_hours=$((idle_seconds / 3600))
  
  if [[ ${idle_hours} -lt 1 ]]; then
    echo "ACTIVE: Issue #${issue_number} (${branch}) - running"
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

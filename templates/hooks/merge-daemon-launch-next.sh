#!/usr/bin/env bash
set -euo pipefail

json_mode="false"
launch_mode="false"
session_name="${TMUX_SESSION_NAME:-agent-workers}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      json_mode="true"
      shift
      ;;
    --launch)
      launch_mode="true"
      shift
      ;;
    --session)
      session_name="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--json] [--launch] [--session <name>]" >&2
      exit 1
      ;;
  esac
done

command -v gh >/dev/null 2>&1 || {
  echo "Missing required command: gh" >&2
  exit 1
}
command -v jq >/dev/null 2>&1 || {
  echo "Missing required command: jq" >&2
  exit 1
}

ready_label="{{READY_LABEL}}"
active_label="{{ACTIVE_LABEL}}"
lane_prefix="{{LANE_PREFIX}}"
branch_prefix="{{WORKER_BRANCH_PREFIX}}"

open_prs="$(gh pr list --state open --json headRefName 2>/dev/null || echo '[]')"
open_issues="$(gh issue list --state open --limit 200 --json number,title,labels,updatedAt,url 2>/dev/null || echo '[]')"

plan="$(jq -n \
  --arg ready_label "${ready_label}" \
  --arg active_label "${active_label}" \
  --arg lane_prefix "${lane_prefix}" \
  --arg branch_prefix "${branch_prefix}" \
  --argjson prs "${open_prs}" \
  --argjson issues "${open_issues}" '
  def lane_from_pr:
    if (.headRefName // "" | startswith($branch_prefix)) then
      (.headRefName | split("-") | .[-1])
    else empty end;
  def lane_from_issue:
    (.labels // [] | map(.name) | map(select(startswith($lane_prefix))) | .[0] // "" | sub("^" + $lane_prefix; ""));
  {
    occupiedLanes: (($prs | map(lane_from_pr)) + ($issues | map(select((.labels | map(.name) | index($ready_label)) or (.labels | map(.name) | index($active_label))) | lane_from_issue))) | map(select(length > 0)) | unique,
    candidates: ($issues | map(select((.labels | map(.name) | index($ready_label)) | not) | select((.labels | map(.name) | index($active_label)) | not)) | map(. + {lane: lane_from_issue}) | map(select(.lane != ""))),
    selected: []
  } |
  .selected = (.candidates | map(select((.lane as $lane | (. as $dummy | $lane)) as $lane | (.occupiedLanes | index($lane) | not))) )
  ')"

selected_numbers=($(jq -r '.selected[].number' <<< "${plan}"))
if [[ "${launch_mode}" == "true" ]]; then
  for issue_number in "${selected_numbers[@]}"; do
    gh issue edit "${issue_number}" --add-label "${ready_label}" >/dev/null 2>&1 || true
  done
fi

if [[ "${json_mode}" == "true" ]]; then
  jq '.' <<< "${plan}"
else
  jq -r '.selected[] | "#\(.number) [\(.lane)] \(.title)"' <<< "${plan}"
fi

#!/usr/bin/env bash
set -euo pipefail

session_name="${TMUX_SESSION_NAME:-agent-qa}"
usage() {
  echo "Usage: $0 [--session <name>] <issue-number> [issue-number ...]" >&2
  exit 1
}

issues=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)
      session_name="$2"
      shift 2
      ;;
    *)
      issues+=("$1")
      shift
      ;;
  esac
done

[[ ${#issues[@]} -gt 0 ]] || usage
command -v tmux >/dev/null 2>&1 || {
  echo "Missing required command: tmux" >&2
  exit 1
}

created=0
for issue in "${issues[@]}"; do
  name="qa-${issue}"
  cmd="bash -lc './.agent-automation/hooks/local-qa-proof-run.sh --issue ${issue}; echo; echo \"QA session complete\"; exec bash -l'"
  if [[ ${created} -eq 0 ]]; then
    tmux new-session -d -s "${session_name}" -n "${name}" "${cmd}" 2>/dev/null || tmux new-window -t "${session_name}" -n "${name}" "${cmd}"
  else
    tmux new-window -t "${session_name}" -n "${name}" "${cmd}"
  fi
  created=$((created + 1))
done

echo "tmux session: ${session_name}"

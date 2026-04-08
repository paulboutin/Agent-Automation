#!/usr/bin/env bash
set -euo pipefail

source "./.agent-automation/hooks/agent-automation-common.sh"

session_name="${TMUX_SESSION_NAME:-agent-workers}"
run_agent="false"
dry_run="false"
auto_finish="true"

usage() {
  cat >&2 <<USAGE
Usage: $0 [--session <name>] [--run-agent] [--no-auto-finish] [--dry-run] <issue-number> [issue-number ...]
USAGE
  exit 1
}

issue_numbers=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --session)
      [[ $# -ge 2 ]] || usage
      session_name="$2"
      shift 2
      ;;
    --run-agent)
      run_agent="true"
      shift
      ;;
    --no-auto-finish)
      auto_finish="false"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      issue_numbers+=("$1")
      shift
      ;;
  esac
done

[[ ${#issue_numbers[@]} -gt 0 ]] || usage
agent_automation_require_command jq
if [[ "${dry_run}" != "true" ]]; then
  agent_automation_require_command tmux
fi

repo_root="$(agent_automation_repo_root)"
cd "${repo_root}"

session_exists="false"
if [[ "${dry_run}" != "true" ]] && tmux has-session -t "${session_name}" 2>/dev/null; then
  session_exists="true"
fi

created_count=0
for issue in "${issue_numbers[@]}"; do
  start_args=(--json)
  if [[ "${dry_run}" == "true" ]]; then
    start_args+=(--no-claim-active)
  fi
  start_args+=("${issue}")
  info_json="$(./.agent-automation/hooks/local-worker-start.sh "${start_args[@]}")"
  branch="$(jq -r '.branch' <<< "${info_json}")"
  worktree="$(jq -r '.worktree' <<< "${info_json}")"
  prompt="$(jq -r '.prompt' <<< "${info_json}")"
  lane_slug="$(jq -r '.lane_slug' <<< "${info_json}")"
  cost_profile="$(jq -r '.cost_profile' <<< "${info_json}")"
  reasoning_effort="$(jq -r '.reasoning_effort' <<< "${info_json}")"
  worker_model="$(jq -r '.worker_model' <<< "${info_json}")"
  variant="$(jq -r '.variant' <<< "${info_json}")"
  host="$(jq -r '.host' <<< "${info_json}")"
  window_name="i${issue}-${lane_slug}"

  if [[ "${run_agent}" == "true" ]]; then
    auto_finish_arg=""
    if [[ "${auto_finish}" == "false" ]]; then
      auto_finish_arg="--no-auto-finish"
    fi
    window_cmd="bash -lc 'cd \"${worktree}\" && ./.agent-automation/hooks/local-worker-run-and-route.sh --issue \"${issue}\" --branch \"${branch}\" --prompt \"${prompt}\" --host \"${host}\" --cost-profile \"${cost_profile}\" --reasoning-effort \"${reasoning_effort}\" --model \"${worker_model}\" --variant \"${variant}\" ${auto_finish_arg}; echo; echo \"Session complete\"; exec bash -l'"
  else
    window_cmd="bash -lc 'cd \"${worktree}\" && echo \"Host: ${host}\" && echo \"Prompt: ${prompt}\" && echo \"Run: ./.agent-automation/hooks/local-worker-run-and-route.sh --issue ${issue} --branch ${branch} --prompt ${prompt} --host ${host} --cost-profile ${cost_profile} --reasoning-effort ${reasoning_effort} --model ${worker_model} --variant ${variant}\"; exec bash -l'"
  fi

  if [[ "${dry_run}" == "true" ]]; then
    echo "[dry-run] issue #${issue}"
    echo "  window: ${window_name}"
    echo "  host: ${host}"
    echo "  branch: ${branch}"
    echo "  worktree: ${worktree}"
    echo "  cmd: ${window_cmd}"
  else
    if tmux list-windows -t "${session_name}" -F '#W' 2>/dev/null | rg -qx "${window_name}"; then
      tmux kill-window -t "${session_name}:${window_name}"
    fi
    if [[ "${session_exists}" == "false" && ${created_count} -eq 0 ]]; then
      tmux new-session -d -s "${session_name}" -n "${window_name}" "${window_cmd}"
      session_exists="true"
    else
      tmux new-window -t "${session_name}" -n "${window_name}" "${window_cmd}"
    fi
  fi
  created_count=$((created_count + 1))
done

if [[ "${dry_run}" == "true" ]]; then
  exit 0
fi

echo "tmux session: ${session_name}"
echo "attach with: tmux attach -t ${session_name}"

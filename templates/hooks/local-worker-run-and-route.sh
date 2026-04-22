#!/usr/bin/env bash
set -euo pipefail

source "./{{COMMON_HOOK_PATH}}"

usage() {
  cat >&2 <<USAGE
Usage: $0 --issue <number> --branch <branch> --prompt <file> --host <name> [options]

Options:
  --cost-profile <name>
  --reasoning-effort <level>
  --model <name>
  --variant <name>
  --no-auto-finish
USAGE
  exit 1
}

issue_number=""
expected_branch=""
prompt_file=""
host_name=""
reasoning_effort=""
model_name=""
variant=""
cost_profile=""
auto_finish="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      issue_number="$2"
      shift 2
      ;;
    --branch)
      expected_branch="$2"
      shift 2
      ;;
    --prompt)
      prompt_file="$2"
      shift 2
      ;;
    --host)
      host_name="$2"
      shift 2
      ;;
    --cost-profile)
      cost_profile="$2"
      shift 2
      ;;
    --reasoning-effort)
      reasoning_effort="$2"
      shift 2
      ;;
    --model)
      model_name="$2"
      shift 2
      ;;
    --variant)
      variant="$2"
      shift 2
      ;;
    --no-auto-finish)
      auto_finish="false"
      shift
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "${issue_number}" && -n "${expected_branch}" && -n "${prompt_file}" && -n "${host_name}" ]] || usage
[[ -f "${prompt_file}" ]] || {
  echo "Prompt file not found: ${prompt_file}" >&2
  exit 1
}

agent_automation_require_command git
agent_automation_require_command tee

current_branch="$(git branch --show-current)"
[[ "${current_branch}" == "${expected_branch}" ]] || {
  echo "Current branch ${current_branch} does not match expected ${expected_branch}" >&2
  exit 1
}

run_dir="./{{AUTOMATION_ROOT}}/runs"
mkdir -p "${run_dir}"
run_id="issue-${issue_number}-$(date +%Y%m%d-%H%M%S)"
raw_log="${run_dir}/${run_id}.raw.log"
clean_log="${run_dir}/${run_id}.clean.log"
message_file="${run_dir}/${run_id}.message.txt"
heartbeat_file="${run_dir}/heartbeat-${issue_number}.json"
prompt_text="$(cat "${prompt_file}")"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

jq -n \
  --arg branch "${expected_branch}" \
  --arg issue "${issue_number}" \
  --arg timestamp "${started_at}" \
  --arg started_at "${started_at}" \
  '{branch: $branch, issue: ($issue | tonumber), timestamp: $timestamp, started_at: $started_at, status: "running"}' > "${heartbeat_file}"

case "${host_name}" in
  codex)
    agent_automation_require_command codex
    cmd=(codex exec --skip-git-repo-check --sandbox workspace-write --cd "$(pwd)")
    if [[ -n "${model_name}" ]]; then
      cmd+=(--model "${model_name}")
    fi
    if [[ -n "${reasoning_effort}" ]]; then
      cmd+=(-c "model_reasoning_effort=${reasoning_effort}")
    fi
    set +e
    "${cmd[@]}" < "${prompt_file}" 2>&1 | tee "${raw_log}"
    runner_exit=${PIPESTATUS[0]}
    set -e
    ;;
  claude)
    agent_automation_require_command claude
    cmd=(claude -p "${prompt_text}")
    if [[ -n "${model_name}" ]]; then
      cmd+=(--model "${model_name}")
    fi
    set +e
    "${cmd[@]}" 2>&1 | tee "${raw_log}"
    runner_exit=${PIPESTATUS[0]}
    set -e
    ;;
  opencode)
    agent_automation_require_command opencode
    cmd=(opencode run --dir "$(pwd)" --dangerously-skip-permissions)
    if [[ -n "${model_name}" ]]; then
      cmd+=(--model "${model_name}")
    fi
    if [[ -n "${variant}" ]]; then
      cmd+=(--variant "${variant}")
    fi
    cmd+=("${prompt_text}")
    set +e
    "${cmd[@]}" 2>&1 | tee "${raw_log}"
    runner_exit=${PIPESTATUS[0]}
    set -e
    ;;
  *)
    echo "Unsupported host: ${host_name}" >&2
    exit 1
    ;;
esac

sed -E $'s/\x1B\\[[0-9;]*[[:alpha:]]//g' "${raw_log}" > "${clean_log}" || cp "${raw_log}" "${clean_log}"
status="$(grep -Eo 'STATUS:[[:space:]]*(DONE|BLOCKED|NEEDS_INFO|FAILED)' "${clean_log}" | tail -n1 | awk -F':' '{gsub(/[[:space:]]/, "", $2); print $2}')"
if [[ -z "${status}" ]]; then
  status="FAILED"
fi

if grep -Eq '^STATUS:[[:space:]]*(DONE|BLOCKED|NEEDS_INFO|FAILED)' "${clean_log}"; then
  start_line="$(grep -nE '^STATUS:[[:space:]]*(DONE|BLOCKED|NEEDS_INFO|FAILED)' "${clean_log}" | tail -n1 | cut -d: -f1)"
  sed -n "${start_line},\$p" "${clean_log}" > "${message_file}"
else
  {
    printf 'STATUS: %s\n\n' "${status}"
    printf 'Worker exited with code %s and did not provide a terminal status line.\n\n' "${runner_exit}"
    echo "Last 40 log lines:"
    tail -n 40 "${clean_log}"
  } > "${message_file}"
fi

echo "Detected worker status: ${status}"
echo "Run log: ${clean_log}"

jq -n \
  --arg branch "${expected_branch}" \
  --arg issue "${issue_number}" \
  --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg status "${status}" \
  --arg started_at "${started_at}" \
  '{branch: $branch, issue: ($issue | tonumber), timestamp: $timestamp, started_at: $started_at, status: $status}' > "${heartbeat_file}"

if [[ "${auto_finish}" == "true" ]]; then
  "./{{AUTOMATION_ROOT}}/hooks/local-worker-finish.sh" "${issue_number}" "${status}" "${message_file}"
fi

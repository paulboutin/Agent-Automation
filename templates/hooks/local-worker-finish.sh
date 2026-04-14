#!/usr/bin/env bash
set -euo pipefail

source "./{{COMMON_HOOK_PATH}}"

issue_number="${1:-}"
status_input="${2:-}"
message_file="${3:-}"

if [[ -z "${issue_number}" || -z "${status_input}" ]]; then
  echo "Usage: $0 <issue-number> <DONE|BLOCKED|NEEDS_INFO|FAILED> [message-file]" >&2
  exit 1
fi

status="$(tr '[:lower:]' '[:upper:]' <<< "${status_input}")"
case "${status}" in
  DONE|BLOCKED|NEEDS_INFO|FAILED) ;;
  *)
    echo "Unsupported status '${status_input}'." >&2
    exit 1
    ;;
esac

agent_automation_require_command git
agent_automation_require_command gh
agent_automation_require_command jq
agent_automation_require_command python3

repo_root="$(agent_automation_repo_root)"
cd "${repo_root}"
policy_json="$(agent_automation_resolve_policy_json)"
ready_label="$(jq -r '.readyLabel' <<< "${policy_json}")"
active_label="$(jq -r '.activeLabel' <<< "${policy_json}")"
done_label="$(jq -r '.doneLabel' <<< "${policy_json}")"
needs_decision_label="$(jq -r '.needsDecisionLabel' <<< "${policy_json}")"
decision_proposed_label="$(jq -r '.decisionProposedLabel' <<< "${policy_json}")"
failed_label="$(jq -r '.agentFailedLabel' <<< "${policy_json}")"
default_base_branch="$(jq -r '.defaultBaseBranch' <<< "${policy_json}")"

current_branch="$(git branch --show-current)"
issue_json="$(gh issue view "${issue_number}" --json title,body,url)"
issue_title="$(jq -r '.title' <<< "${issue_json}")"

comment_body=""
if [[ -n "${message_file}" && -f "${message_file}" ]]; then
  comment_body="$(cat "${message_file}")"
fi

pr_url=""
if [[ "${status}" == "DONE" ]]; then
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "agent: ${issue_title} (#${issue_number})" >/dev/null
  fi
  git push -u origin "${current_branch}" >/dev/null 2>&1 || true

  pr_body_file="$(agent_automation_make_tempfile "pr-body.")"
  worker_log_file=""
  trap 'rm -f "${pr_body_file}"' EXIT
  if [[ -n "${message_file}" ]]; then
    for candidate in \
      "${message_file%.message.txt}.clean.log" \
      "${message_file%.message.txt}.raw.log"; do
      if [[ -f "${candidate}" ]]; then
        worker_log_file="${candidate}"
        break
      fi
    done
  fi
  pr_body_args=(--mode autofill --head-ref "${current_branch}" --base-ref "${default_base_branch}")
  if [[ -n "${worker_log_file}" ]]; then
    pr_body_args+=(--worker-log "${worker_log_file}")
  fi
  agent_automation_render_pr_body "${pr_body_args[@]}" > "${pr_body_file}"

  pr_json="$(gh pr list --head "${current_branch}" --json url --limit 1 2>/dev/null || echo '[]')"
  pr_url="$(jq -r '.[0].url // ""' <<< "${pr_json}")"
  if [[ -z "${pr_url}" ]]; then
    gh pr create --base "${default_base_branch}" --head "${current_branch}" --title "${issue_title}" --body-file "${pr_body_file}" >/dev/null 2>&1 || true
    pr_json="$(gh pr list --head "${current_branch}" --json url --limit 1 2>/dev/null || echo '[]')"
    pr_url="$(jq -r '.[0].url // ""' <<< "${pr_json}")"
  else
    gh pr edit "${current_branch}" --body-file "${pr_body_file}" >/dev/null 2>&1 || true
  fi

  if [[ -z "${comment_body}" ]]; then
    comment_body="$(agent_automation_render_message worker-done.md)"
  fi
  if [[ -n "${pr_url}" ]]; then
    comment_body="${comment_body}"$'\n\n'"PR: ${pr_url}"
  fi
  gh issue comment "${issue_number}" --body "${comment_body}" >/dev/null
  gh issue edit "${issue_number}" --remove-label "${active_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --remove-label "${needs_decision_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --remove-label "${failed_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --add-label "${done_label}" >/dev/null 2>&1 || true
  exit 0
fi

if [[ -z "${comment_body}" ]]; then
  case "${status}" in
    BLOCKED|NEEDS_INFO)
      comment_body="$(agent_automation_render_message worker-blocked.md --var question="Decision required to continue.")"
      ;;
    FAILED)
      comment_body="$(agent_automation_render_message worker-failed.md --var ready_label="${ready_label}")"
      ;;
  esac
fi

gh issue comment "${issue_number}" --body "${comment_body}" >/dev/null

if [[ "${status}" == "BLOCKED" || "${status}" == "NEEDS_INFO" ]]; then
  gh issue edit "${issue_number}" --add-label "${needs_decision_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --remove-label "${decision_proposed_label}" >/dev/null 2>&1 || true
else
  gh issue edit "${issue_number}" --remove-label "${active_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --add-label "${failed_label}" >/dev/null 2>&1 || true
fi

repo_root="$(agent_automation_repo_root)"
run_dir="${repo_root}/.agent-automation/runs"
heartbeat_file="${run_dir}/heartbeat-${issue_number}.json"
if [[ -f "${heartbeat_file}" ]]; then
  jq -n \
    --arg branch "${current_branch}" \
    --arg issue "${issue_number}" \
    --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg status "${status}" \
    '{branch: $branch, issue: ($issue | tonumber), timestamp: $timestamp, status: $status}' > "${heartbeat_file}"
fi

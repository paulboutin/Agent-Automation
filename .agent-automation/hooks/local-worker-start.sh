#!/usr/bin/env bash
set -euo pipefail

source "./.agent-automation/hooks/agent-automation-common.sh"

json_mode="false"
claim_active="true"
launch_dashboard="false"
if [[ "${1:-}" == "--json" ]]; then
  json_mode="true"
  shift
fi

if [[ "${1:-}" == "--no-claim-active" ]]; then
  claim_active="false"
  shift
fi

if [[ "${1:-}" == "--dashboard" ]]; then
  launch_dashboard="true"
  shift
fi

issue_number="${1:-}"
if [[ -z "${issue_number}" ]]; then
  echo "Usage: $0 [--json] [--no-claim-active] [--dashboard] <issue-number>" >&2
  exit 1
fi

agent_automation_require_command git
agent_automation_require_command gh
agent_automation_require_command jq
agent_automation_require_command python3

repo_root="$(agent_automation_repo_root)"
cd "${repo_root}"

policy_json="$(agent_automation_resolve_policy_json)"
ready_label="$(jq -r '.readyLabel' <<< "${policy_json}")"
active_label="$(jq -r '.activeLabel' <<< "${policy_json}")"
failed_label="$(jq -r '.agentFailedLabel' <<< "${policy_json}")"

issue_json="$(gh issue view "${issue_number}" --json number,title,body,labels,url,state)"
issue_state="$(jq -r '.state' <<< "${issue_json}")"
if [[ "${issue_state}" != "OPEN" ]]; then
  echo "Issue #${issue_number} is not OPEN (state=${issue_state})." >&2
  exit 1
fi

body_file="$(agent_automation_make_tempfile "issue-body.")"
labels_file="$(agent_automation_make_tempfile "issue-labels.")"
trap 'rm -f "${body_file}" "${labels_file}"' EXIT
jq -r '.body // ""' <<< "${issue_json}" > "${body_file}"
jq -r '[.labels[].name]' <<< "${issue_json}" > "${labels_file}"
meta_json="$(agent_automation_resolve_task_metadata "${body_file}" "${labels_file}" local)"

lane="$(jq -r '.lane' <<< "${meta_json}")"
cost_profile="$(jq -r '.costProfile' <<< "${meta_json}")"
reasoning_effort="$(jq -r '.reasoningEffort' <<< "${meta_json}")"
host_name="$(jq -r '.defaultHost' <<< "${meta_json}")"
host_display_name="$(jq -r '.hostDisplayName' <<< "${meta_json}")"
model_env_var="$(jq -r '.modelEnvVar // ""' <<< "${meta_json}")"
variant="$(jq -r '.variant // ""' <<< "${meta_json}")"
base_branch="$(jq -r '.baseBranch' <<< "${meta_json}")"
scope="$(jq -r '.scope // ""' <<< "${meta_json}")"

model_name=""
if [[ -n "${model_env_var}" ]]; then
  model_name="${!model_env_var:-}"
fi

lane_slug="$(tr '[:upper:]' '[:lower:]' <<< "${lane}" | sed -E 's/[^a-z0-9-]+/-/g; s/-+/-/g; s/^-|-$//g')"
[[ -n "${lane_slug}" ]] || lane_slug="general"
branch="$(agent_automation_branch_name "${issue_number}" "${lane_slug}")"

worktree_root="${WORKTREE_ROOT:-/tmp/agent-automation-worktrees}"
worktree="${worktree_root}/issue-${issue_number}-${lane_slug}"
mkdir -p "${worktree_root}"

if git worktree list --porcelain | grep -Fqx "worktree ${worktree}"; then
  git worktree remove --force "${worktree}" >/dev/null 2>&1 || true
fi

git fetch origin --prune >/dev/null 2>&1 || true
if git show-ref --verify --quiet "refs/remotes/origin/${base_branch}"; then
  start_ref="origin/${base_branch}"
elif git show-ref --verify --quiet "refs/heads/${base_branch}"; then
  start_ref="${base_branch}"
else
  start_ref="HEAD"
fi
git worktree add -B "${branch}" "${worktree}" "${start_ref}" >/dev/null

prompt_dir="${worktree}/.agent-automation/prompts"
mkdir -p "${prompt_dir}"
prompt_file="${prompt_dir}/issue-${issue_number}.md"

cat > "${prompt_file}" <<EOF
You are the assigned automation worker for issue #${issue_number}.

Execution host: ${host_display_name} (${host_name})
Cost profile: ${cost_profile}
Reasoning effort: ${reasoning_effort}
Base branch: ${base_branch}
Worker branch: ${branch}
Automation scope: ${scope:-"(none specified)"}

Operate only within the repository at the current working directory.

Required outcome:
1. Implement the issue as scoped.
2. Update tests/docs/contracts when needed.
3. Keep changes minimal and reversible.
4. Prefer existing project patterns over inventing new ones.
5. If the review pack exists, self-check against ./$.agent-automation/packs/review/checklist.md before finishing.
6. If the QA pack exists, include the validation evidence requested by ./$.agent-automation/packs/qa/checklist.md when relevant.

Issue body:
$(cat "${body_file}")

Finish your final output with exactly one status line:
STATUS: DONE
STATUS: BLOCKED
STATUS: NEEDS_INFO
STATUS: FAILED

If status is BLOCKED or NEEDS_INFO, also include:
QUESTION: one explicit unblock question
OPTION 1: first concrete option
OPTION 2: second concrete option
OPTION 3: optional third option
EOF

if [[ "${claim_active}" == "true" ]]; then
  gh issue edit "${issue_number}" --add-label "${active_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --remove-label "${ready_label}" >/dev/null 2>&1 || true
  gh issue edit "${issue_number}" --remove-label "${failed_label}" >/dev/null 2>&1 || true
fi

if [[ "${json_mode}" == "true" ]]; then
  jq -n \
    --arg branch "${branch}" \
    --arg worktree "${worktree}" \
    --arg prompt "${prompt_file}" \
    --arg lane_slug "${lane_slug}" \
    --arg cost_profile "${cost_profile}" \
    --arg reasoning_effort "${reasoning_effort}" \
    --arg worker_model "${model_name}" \
    --arg variant "${variant}" \
    --arg host "${host_name}" \
    '{branch: $branch, worktree: $worktree, prompt: $prompt, lane_slug: $lane_slug, cost_profile: $cost_profile, reasoning_effort: $reasoning_effort, worker_model: $worker_model, variant: $variant, host: $host}'
else
  cat <<EOF
Prepared issue #${issue_number}
  host: ${host_display_name}
  branch: ${branch}
  worktree: ${worktree}
  prompt: ${prompt_file}
EOF
fi

if [[ "${launch_dashboard}" == "true" ]]; then
  dashboard_session="worker-dashboard"
  if command -v tmux >/dev/null 2>&1; then
    if tmux has-session -t "${dashboard_session}" 2>/dev/null; then
      tmux select-window -t "${dashboard_session}:0" 2>/dev/null || true
      tmux select-pane -t "${dashboard_session}:0" 2>/dev/null || true
    else
      tmux new-session -d -s "${dashboard_session}" "python -m worker_dashboard"
      sleep 1
    fi
  elif command -v itermus >/dev/null 2>&1 || command -v iterm2 >/dev/null 2>&1; then
    osascript -e 'tell application "iTerm" to activate' 2>/dev/null || true
  else
    echo "Dashboard not running. Start with: python -m worker_dashboard" >&2
  fi
fi

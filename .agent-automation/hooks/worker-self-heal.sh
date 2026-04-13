#!/usr/bin/env bash
set -euo pipefail

source "./.agent-automation/hooks/agent-automation-common.sh"

json_mode="false"
dry_run="false"
max_restarts="${SELF_HEAL_MAX_RESTARTS:-3}"
max_age_hours="${SELF_HEAL_MAX_AGE_HOURS:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      json_mode="true"
      shift
      ;;
    --dry-run)
      dry_run="true"
      shift
      ;;
    --max-restarts)
      max_restarts="$2"
      shift 2
      ;;
    --max-age-hours)
      max_age_hours="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--json] [--dry-run] [--max-restarts <n>] [--max-age-hours <hours>]" >&2
      exit 1
      ;;
  esac
done

agent_automation_require_command gh
agent_automation_require_command jq

repo_root="$(agent_automation_repo_root)"
cd "${repo_root}"

policy_json="$(agent_automation_resolve_policy_json)"
ready_label="$(jq -r '.readyLabel' <<< "${policy_json}")"
active_label="$(jq -r '.activeLabel' <<< "${policy_json}")"
failed_label="$(jq -r '.agentFailedLabel' <<< "${policy_json}")"

stuck_threshold="$(date -v-${max_age_hours}H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -d "${max_age_hours} hours ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -d "@$(( $(date +%s) - max_age_hours * 3600 ))" +%Y-%m-%dT%H:%M:%S)"
active_issues="$(gh issue list --state open --label "${active_label}" --json number,title,updatedAt,labels,url 2>/dev/null || echo '[]')"

stuck_count=0
restart_count=0
healed=()

for issue in $(jq -r '.[] | @json' <<< "${active_issues}"); do
  issue_number=$(jq -r '.number' <<< "${issue}")
  updated_at=$(jq -r '.updatedAt' <<< "${issue}")
  
  if [[ "${updated_at}" < "${stuck_threshold}" ]]; then
    ((stuck_count++)) || true
    
    restart_label="${active_label}-restart"
    existing_restarts=$(gh issue list --state open --label "${restart_label}" --json number 2>/dev/null | jq "[.[] | select(.number == ${issue_number})] | length" || echo "0")
    current_restarts=$((${existing_restarts:-0}))
    
    if [[ ${current_restarts} -ge ${max_restarts} ]]; then
      comment_body="$(agent_automation_render_message worker-failed.md --var ready_label="${ready_label}")"
      comment_body="${comment_body}"$'\n\n'"Self-heal: worker exceeded restart limit (${max_restarts})."
      gh issue comment "${issue_number}" --body "${comment_body}" >/dev/null 2>&1 || true
      gh issue edit "${issue_number}" --remove-label "${active_label}" >/dev/null 2>&1 || true
      gh issue edit "${issue_number}" --add-label "${failed_label}" >/dev/null 2>&1 || true
      continue
    fi
    
    if [[ "${dry_run}" != "true" ]]; then
      gh issue edit "${issue_number}" --remove-label "${active_label}" >/dev/null 2>&1 || true
      gh issue edit "${issue_number}" --add-label "${restart_label}" >/dev/null 2>&1 || true
      gh issue edit "${issue_number}" --add-label "${ready_label}" >/dev/null 2>&1 || true
      
      gh issue comment "${issue_number}" --body "Self-heal: worker detected stuck (no updates since ${updated_at}). Restarting (attempt $((current_restarts + 1))/${max_restarts})." >/dev/null 2>&1 || true
    fi
    
    ((restart_count++)) || true
    healed+=("${issue_number}")
  fi
done

if [[ "${json_mode}" == "true" ]]; then
  jq -n \
    --argjson stuck_count "${stuck_count}" \
    --argjson restart_count "${restart_count}" \
    --argjson healed "$(printf '%s\n' "${healed[@]}" | jq -R . | jq -s .)" \
    --arg threshold "${stuck_threshold}" \
    '{stuckWorkers: $stuck_count, restartedWorkers: $restart_count, healedIssues: $healed, threshold: $threshold}'
else
  echo "Self-healing check complete"
  echo "Stuck workers detected: ${stuck_count}"
  echo "Workers restarted: ${restart_count}"
  if [[ ${#healed[@]} -gt 0 ]]; then
    echo "Healed issues: ${healed[*]}"
  fi
fi
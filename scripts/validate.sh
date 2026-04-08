#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: validate.sh [--repo-root <path>] [--profile <path>]
USAGE
  exit 1
}

package_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="$(pwd)"
profile_path="${repo_root}/agent-factory.profile.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-root)
      [[ $# -ge 2 ]] || usage
      repo_root="$2"
      shift 2
      ;;
    --profile)
      [[ $# -ge 2 ]] || usage
      profile_path="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

python3 - <<'PY' "${package_root}/contracts/repo-profile.v2.schema.json" \
  "${package_root}/contracts/worker-pr-wake.v1.schema.json" \
  "${package_root}/contracts/worker-status.v1.schema.json"
import json
import sys

for path in sys.argv[1:]:
    with open(path, "r", encoding="utf-8") as handle:
        json.load(handle)
    print(f"JSON OK: {path}")
PY

if [[ ! -f "${profile_path}" ]]; then
  profile_path="${package_root}/examples/upstream-selftest.repo-profile.json"
fi

python3 "${package_root}/scripts/validate-profile.py" "${repo_root}" "${profile_path}"
python3 "${package_root}/scripts/render-templates.py" --repo-root "${repo_root}" --profile "${profile_path}"

for path in \
  "${package_root}/README.md" \
  "${package_root}/docs/OPERATING_MODEL.md" \
  "${package_root}/docs/ADOPTION_GUIDE.md" \
  "${package_root}/docs/MIGRATIONS.md" \
  "${package_root}/docs/BOOTSTRAP_PLAN.md" \
  "${package_root}/docs/HOST_MODEL.md" \
  "${package_root}/docs/PACK_MODEL.md" \
  "${package_root}/docs/QUICKSTART.md" \
  "${package_root}/docs/PROFILE_REFERENCE.md" \
  "${package_root}/docs/OPERATIONS.md" \
  "${package_root}/templates/agent-task.yml" \
  "${package_root}/templates/pull-request-template.md" \
  "${package_root}/templates/review/checklist.md" \
  "${package_root}/templates/review/prompt.md" \
  "${package_root}/templates/qa/checklist.md" \
  "${package_root}/templates/qa/prompt.md" \
  "${package_root}/templates/messages/coordinator-wake-comment.md" \
  "${package_root}/templates/messages/unblocker-recommendation.md" \
  "${package_root}/templates/messages/worker-blocked.md" \
  "${package_root}/templates/messages/worker-done.md" \
  "${package_root}/templates/messages/worker-dispatch-skipped.md" \
  "${package_root}/templates/messages/worker-failed.md" \
  "${package_root}/templates/hooks/agent-automation-common.sh" \
  "${package_root}/templates/hooks/local-worker-start.sh" \
  "${package_root}/templates/hooks/local-worker-finish.sh" \
  "${package_root}/templates/hooks/local-worker-launch-tmux.sh" \
  "${package_root}/templates/hooks/local-worker-run-and-route.sh" \
  "${package_root}/templates/hooks/local-qa-proof-launch-tmux.sh" \
  "${package_root}/templates/hooks/local-qa-proof-run.sh" \
  "${package_root}/templates/hooks/coordinator-relay-handle.sh" \
  "${package_root}/templates/hooks/coordinator-relay-poll.sh" \
  "${package_root}/templates/hooks/merge-daemon-launch-next.sh" \
  "${package_root}/templates/hooks/merge-daemon-status.sh" \
  "${package_root}/templates/workflows/agent-task-worker.yml" \
  "${package_root}/templates/workflows/agent-unblocker.yml" \
  "${package_root}/templates/workflows/agent-pr-wake.yml" \
  "${package_root}/scripts/agent_factory_profile.py" \
  "${package_root}/scripts/automation-scope-env.sh" \
  "${package_root}/scripts/render-message-template.py" \
  "${package_root}/scripts/render-pr-body.py" \
  "${package_root}/scripts/render-templates.py" \
  "${package_root}/scripts/resolve-promotion-policy.py" \
  "${package_root}/scripts/resolve-repo-policy.py" \
  "${package_root}/scripts/resolve-task-metadata.py" \
  "${package_root}/scripts/install.sh" \
  "${package_root}/scripts/update.sh" \
  "${package_root}/scripts/render.sh" \
  "${package_root}/scripts/smoke.sh" \
  "${package_root}/examples/scaffold.repo-profile.json" \
  "${package_root}/examples/upstream-selftest.repo-profile.json" \
  "${package_root}/examples/codex.repo-profile.json" \
  "${package_root}/examples/claude.repo-profile.json" \
  "${package_root}/examples/opencode.repo-profile.json"; do
  [[ -f "${path}" ]] || {
    echo "Missing expected file: ${path}" >&2
    exit 1
  }
  echo "File OK: ${path}"
done

legacy_name_a="P""higure"
legacy_name_b="P""higure-app"
legacy_pattern="${legacy_name_a}|${legacy_name_b}"

if rg -n "${legacy_pattern}" "${package_root}/README.md" "${package_root}/docs" "${package_root}/examples" "${package_root}/templates" "${package_root}/contracts" "${package_root}/scripts" --glob '!validate.sh' >/dev/null; then
  echo "Forbidden legacy strings detected in shipped repo." >&2
  exit 1
fi

if find "${package_root}/templates/workflows" -maxdepth 1 -name 'codex-*' | grep -q .; then
  echo "Legacy codex-* workflow filenames still exist." >&2
  exit 1
fi

legacy_branch_prefix="co""dex/issue-"
if rg -n "${legacy_branch_prefix}" "${package_root}/README.md" "${package_root}/docs" "${package_root}/examples" "${package_root}/templates" "${package_root}/scripts" --glob '!validate.sh' >/dev/null; then
  echo "Legacy codex/issue-* branch defaults still exist." >&2
  exit 1
fi

echo "Portable agent factory validation complete."

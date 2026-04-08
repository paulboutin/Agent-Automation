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

python3 - <<'PY' "${package_root}/contracts/repo-profile.v1.schema.json" \
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
  "${package_root}/docs/PHIGURE_MAPPING.md" \
  "${package_root}/templates/agent-task.yml" \
  "${package_root}/templates/messages/coordinator-wake-comment.md" \
  "${package_root}/templates/messages/unblocker-recommendation.md" \
  "${package_root}/templates/messages/worker-blocked.md" \
  "${package_root}/templates/messages/worker-done.md" \
  "${package_root}/templates/messages/worker-dispatch-skipped.md" \
  "${package_root}/templates/messages/worker-failed.md" \
  "${package_root}/templates/pull-request-template.md" \
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
  "${package_root}/examples/scaffold.repo-profile.json" \
  "${package_root}/examples/upstream-selftest.repo-profile.json" \
  "${package_root}/templates/hooks/local-worker-start.sh" \
  "${package_root}/templates/hooks/local-worker-finish.sh" \
  "${package_root}/templates/hooks/local-worker-launch-tmux.sh" \
  "${package_root}/templates/hooks/local-worker-run-and-route.sh" \
  "${package_root}/templates/hooks/coordinator-relay-handle.sh" \
  "${package_root}/templates/hooks/coordinator-relay-poll.sh" \
  "${package_root}/templates/hooks/merge-daemon-launch-next.sh" \
  "${package_root}/templates/hooks/merge-daemon-status.sh" \
  "${package_root}/templates/hooks/local-qa-proof-launch-tmux.sh" \
  "${package_root}/templates/hooks/local-qa-proof-run.sh" \
  "${package_root}/templates/workflows/codex-task-worker.yml" \
  "${package_root}/templates/workflows/codex-unblocker.yml" \
  "${package_root}/templates/workflows/codex-coordinator-pr-wake.yml"; do
  [[ -f "${path}" ]] || {
    echo "Missing expected file: ${path}" >&2
    exit 1
  }
  echo "File OK: ${path}"
done

echo "Portable agent factory validation complete."

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: smoke.sh [--repo-root <path>] [--profile <path>]
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

if [[ ! -f "${profile_path}" ]]; then
  profile_path="${package_root}/examples/upstream-selftest.repo-profile.json"
fi

echo "Smoke: validating package repo"
"${package_root}/scripts/validate.sh" --repo-root "${repo_root}" --profile "${profile_path}"

echo "Smoke: profile summary"
python3 - <<'PY' "${profile_path}"
import json
import sys

profile = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print("Repo:", profile["repo"]["name"])
print("Platform:", profile["platform"]["name"])
print("Development branch:", profile["branches"]["development"])
print("Worker branch format:", profile["branches"]["workerBranchFormat"])
print("Default host:", profile["execution"]["defaultHost"])
print("Enabled hosts:", ", ".join(profile["execution"]["enabledHosts"]))
print("Enabled packs:", ", ".join(name for name, enabled in profile["packs"].items() if enabled))
PY

echo "Smoke: scratch installs"
scratch_root="$(mktemp -d "${TMPDIR:-/tmp}/agent-automation-smoke.XXXXXX")"
trap 'rm -rf "${scratch_root}"' EXIT

for example in scaffold codex claude opencode; do
  target="${scratch_root}/${example}"
  mkdir -p "${target}"
  printf '# %s\n' "${example}" > "${target}/README.md"
  "${package_root}/scripts/install.sh" --target "${target}" --force-profile >/dev/null
  cp "${package_root}/examples/${example}.repo-profile.json" "${target}/agent-factory.profile.json"
  "${target}/tools/agent-factory/scripts/render.sh" --repo-root "${target}" --profile "${target}/agent-factory.profile.json" >/dev/null
  "${target}/tools/agent-factory/scripts/validate.sh" --repo-root "${target}" --profile "${target}/agent-factory.profile.json" >/dev/null
  echo "Scratch OK: ${example}"
done

echo "Portable agent factory smoke complete."

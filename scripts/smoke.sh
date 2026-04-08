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

echo "Smoke: validating portable package"
"${package_root}/scripts/validate.sh" --repo-root "${repo_root}" --profile "${profile_path}"

echo "Smoke: loading profile summary"
python3 - <<'PY' "${profile_path}"
import json
import sys

profile = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print("Repo:", profile["repo"]["name"])
print("Development branch:", profile["branches"]["development"])
print("Promotion branches:", ", ".join(profile["branches"]["promotion"]))
print("Worker branch format:", profile["branches"]["workerBranchFormat"])
print("Queue labels:", ", ".join(profile["labels"][key] for key in ("ready", "active", "needsDecision", "decisionProposed", "agentFailed")))
print("Roles:", ", ".join(item["name"] for item in profile["roles"]))
print("Lanes:", ", ".join(item["name"] for item in profile["lanes"]))
print("Worker status protocol:", profile["protocols"]["workerStatus"])
print("PR wake protocol:", profile["protocols"]["workerPrWake"])
if "concurrency" in profile:
    print("Concurrency helper:", profile["concurrency"]["envHelperScript"])
PY

echo "Portable agent factory smoke complete."

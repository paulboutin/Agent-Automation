#!/usr/bin/env bash
set -euo pipefail

issue_number=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue)
      issue_number="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 --issue <number>" >&2
      exit 1
      ;;
  esac
done

[[ -n "${issue_number}" ]] || {
  echo "Usage: $0 --issue <number>" >&2
  exit 1
}

command -v gh >/dev/null 2>&1 || {
  echo "Missing required command: gh" >&2
  exit 1
}

echo "Operator-proof QA task for issue #${issue_number}"
echo
echo "Checklist:"
echo "  - Review ./{{AUTOMATION_ROOT}}/packs/qa/checklist.md"
echo "  - Validate the requested real-world/device/runtime proof"
echo "  - Comment evidence back on the issue"
echo
if [[ -n "${QA_PROOF_COMMAND:-}" ]]; then
  echo "Running QA_PROOF_COMMAND"
  bash -lc "${QA_PROOF_COMMAND}"
else
  echo "No QA_PROOF_COMMAND configured. Complete the proof manually, then comment DONE or FAILED on the issue."
fi

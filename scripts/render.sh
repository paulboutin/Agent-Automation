#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: render.sh [--repo-root <path>] [--profile <path>]
USAGE
  exit 1
}

repo_root="$(pwd)"
profile_path=""

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

cmd=(python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/render-templates.py" --repo-root "${repo_root}" --write)
if [[ -n "${profile_path}" ]]; then
  cmd+=(--profile "${profile_path}")
fi
"${cmd[@]}"

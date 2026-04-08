#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: update.sh --target <repo-root> [--package-dir <path>] [--profile-name <filename>]
USAGE
  exit 1
}

args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target|--package-dir|--profile-name)
      [[ $# -ge 2 ]] || usage
      args+=("$1" "$2")
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install.sh" "${args[@]}"

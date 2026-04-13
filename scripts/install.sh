#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: install.sh --target <repo-root> [--package-dir <path>] [--profile-name ] [--force-profile] [--host <host>]
USAGE
  exit 1
}

src_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_root=""
package_dir="tools/agent-factory"
profile_name="agent-factory.profile.json"
force_profile=0
host=""

detect_host() {
  local detected=""
  if command -v codex >/dev/null 2>&1; then
    detected="codex"
  elif command -v claude >/dev/null 2>&1; then
    detected="claude"
  elif command -v opencode >/dev/null 2>&1; then
    detected="opencode"
  fi
  printf '%s' "${detected}"
}

prompt_host() {
  local default="$1"
  local options=("codex" "claude" "opencode")
  
  echo "Available agent frameworks:"
  for opt in "${options[@]}"; do
    if command -v "$opt" >/dev/null 2>&1; then
      echo "  - $opt (installed)"
    else
      echo "  - $opt"
    fi
  done
  echo ""
  
  if [[ -n "${default}" ]]; then
    read -r -p "Select default host [$default]: " host
    host="${host:-$default}"
  else
    read -r -p "Select default host: " host
  fi
  
  case "$host" in
    codex|claude|opencode) return 0 ;;
    *)
      echo "Invalid host: $host" >&2
      return 1
      ;;
  esac
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      [[ $# -ge 2 ]] || usage
      target_root="$2"
      shift 2
      ;;
    --package-dir)
      [[ $# -ge 2 ]] || usage
      package_dir="$2"
      shift 2
      ;;
    --profile-name)
      [[ $# -ge 2 ]] || usage
      profile_name="$2"
      shift 2
      ;;
    --force-profile)
      force_profile=1
      shift
      ;;
    --host)
      [[ $# -ge 2 ]] || usage
      host="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "${target_root}" ]] || usage
target_root="$(cd "${target_root}" && pwd)"
dest_pkg="${target_root}/${package_dir}"
dest_profile="${target_root}/${profile_name}"

mkdir -p "${dest_pkg}"
rsync -a --delete --exclude '.git' --exclude '.github' "${src_root}/" "${dest_pkg}/"

if [[ ! -f "${dest_profile}" || "${force_profile}" -eq 1 ]]; then
  detected_host="$(detect_host)"
  
  if [[ -n "${AGENT_FACTORY_HOST:-}" ]]; then
    host="${AGENT_FACTORY_HOST}"
  elif [[ -z "${host}" ]]; then
    if [[ -n "${detected_host}" ]]; then
      prompt_host "${detected_host}" || exit 1
    else
      prompt_host "" || exit 1
    fi
  fi
  
  cp "${src_root}/examples/scaffold.repo-profile.json" "${dest_profile}"
  
  if [[ -n "${host}" ]]; then
    python3 - <<PY
import json
with open("${dest_profile}", "r") as f:
    profile = json.load(f)
profile["execution"]["defaultHost"] = "${host}"
profile["execution"]["enabledHosts"] = ["${host}"]
with open("${dest_profile}", "w") as f:
    json.dump(profile, f, indent=2)
PY
  fi
fi

python3 "${dest_pkg}/scripts/render-templates.py" --repo-root "${target_root}" --profile "${dest_profile}" --write

echo "Installed Agent Automation Factory to ${dest_pkg}"
echo "Profile: ${dest_profile}"
echo "Host: ${host:-scaffold default}"
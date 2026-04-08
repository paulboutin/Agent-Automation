#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: install.sh --target <repo-root> [--package-dir <path>] [--profile-name <filename>] [--force-profile]
USAGE
  exit 1
}

src_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target_root=""
package_dir="tools/agent-factory"
profile_name="agent-factory.profile.json"
force_profile=0

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
  cp "${src_root}/examples/scaffold.repo-profile.json" "${dest_profile}"
fi

python3 "${dest_pkg}/scripts/render-templates.py" --repo-root "${target_root}" --profile "${dest_profile}" --write

echo "Installed Agent Automation Factory to ${dest_pkg}"
echo "Profile: ${dest_profile}"

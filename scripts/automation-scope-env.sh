#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: automation-scope-env.sh --base-branch <branch>
USAGE
  exit 1
}

base_branch=""
home_dir="${HOME}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-branch)
      [[ $# -ge 2 ]] || usage
      base_branch="$2"
      shift 2
      ;;
    --home)
      [[ $# -ge 2 ]] || usage
      home_dir="$2"
      shift 2
      ;;
    *)
      usage
      ;;
  esac
done

[[ -n "${base_branch}" ]] || usage

slug="$(printf '%s' "${base_branch}" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/-+/-/g; s/^-|-$//g')"
[[ -n "${slug}" ]] || slug="default"

cat <<EOF
export COORDINATOR_BASE_BRANCH='${base_branch}'
export WORKSTREAM_SCOPE_ID='${slug}'
export TMUX_SESSION_NAME='agent-factory-workers-${slug}'
export COORDINATOR_STATE_DIR='${home_dir}/.agent-factory/coordinator-${slug}'
export MERGE_DAEMON_LAUNCHD_LABEL='com.agent-factory.merge-daemon-${slug}'
export WORKTREE_ROOT='/tmp/agent-factory-worktrees-${slug}'
EOF

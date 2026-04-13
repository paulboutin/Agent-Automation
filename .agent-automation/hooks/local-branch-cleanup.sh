#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: local-branch-cleanup.sh [--dry-run] [--force]
USAGE
  exit 1
}

dry_run=0
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    *)
      usage
      ;;
  esac
done

echo "=== Local Branch Cleanup ==="

remote_branches=$(git branch -r --format='%(refname:short)' | grep '^origin/agent/')
if [[ -z "${remote_branches}" ]]; then
  echo "No remote agent branches found."
else
  echo "Remote agent branches:"
  echo "${remote_branches}"
fi

echo ""
echo "=== Local Orphaned Branches ==="
current_branch=$(git branch --show-current)

for branch in $(git branch --format='%(refname:short)'); do
  if [[ "$branch" == agent/* ]]; then
    merged=0
    if git branch --contains "$branch" 2>/dev/null | grep -q "development\|main"; then
      merged=1
    fi
    
    if [[ $merged -eq 1 ]]; then
      if [[ $dry_run -eq 1 ]]; then
        echo "[DRY-RUN] Would delete: $branch"
      else
        if [[ $force -eq 1 ]]; then
          git branch -D "$branch" 2>/dev/null && echo "Deleted: $branch" || true
        else
          git branch -d "$branch" 2>/dev/null && echo "Deleted: $branch" || echo "Skipped (not fully merged): $branch"
        fi
      fi
    else
      echo "Skipped (not merged): $branch"
    fi
  fi
done

echo ""
echo "=== Worktree Cleanup ==="
worktree_dir="${HOME}/.agent-automation/worktrees"
if [[ -d "${worktree_dir}" ]]; then
  for worktree in "${worktree_dir}"/*; do
    if [[ -d "$worktree" ]]; then
      branch_name=$(basename "$worktree")
      if ! git branch -r --format='%(refname:short)' | grep -q "origin/${branch_name}"; then
        if [[ $dry_run -eq 1 ]]; then
          echo "[DRY-RUN] Would remove worktree: $worktree"
        else
          rm -rf "$worktree" && echo "Removed worktree: $worktree" || true
        fi
      fi
    fi
  done
fi

echo ""
echo "Done."
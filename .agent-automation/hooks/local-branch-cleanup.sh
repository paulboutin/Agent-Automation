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

protected_branches=("main" "development" "stage")

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

is_protected() {
  local branch="$1"
  for protected in "${protected_branches[@]}"; do
    if [[ "$branch" == "$protected" ]]; then
      return 0
    fi
  done
  return 1
}

echo "=== Local Branch Cleanup ==="
echo "Protected branches: ${protected_branches[*]}"

remote_branches=$(git branch -r --format='%(refname:short)' | grep '^origin/agent/')
if [[ -z "${remote_branches}" ]]; then
  echo "No remote agent branches found."
else
  echo "Remote agent branches:"
  echo "${remote_branches}"
fi

echo ""
echo "=== Local Orphaned Branches ==="

for branch in $(git branch --format='%(refname:short}'); do
  if is_protected "$branch"; then
    echo "Skipped (protected): $branch"
    continue
  fi
  
  if [[ "$branch" == agent/* ]]; then
    merged=0
    for protected in "${protected_branches[@]}"; do
      if git branch --contains "$branch" 2>/dev/null | grep -q "$protected"; then
        merged=1
        break
      fi
    done
    
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
      echo "Skipped (not merged to protected): $branch"
    fi
  fi
done

echo ""
echo "=== Worktree Cleanup ==="
worktree_dirs=(
  "${HOME}/.agent-automation/worktrees"
  "/tmp/agent-automation-worktrees"
)

for worktree_dir in "${worktree_dirs[@]}"; do
  if [[ -d "${worktree_dir}" ]]; then
    for worktree in "${worktree_dir}"/*; do
      if [[ -d "$worktree" ]]; then
        branch_name=$(basename "$worktree")
        if is_protected "$branch_name"; then
          echo "Skipped (protected): $worktree"
          continue
        fi
        if ! git branch -r --format='%(refname:short}' | grep -q "origin/${branch_name}"; then
          if [[ $dry_run -eq 1 ]]; then
            echo "[DRY-RUN] Would remove worktree: $worktree"
          else
            rm -rf "$worktree" && echo "Removed worktree: $worktree" || true
          fi
        fi
      fi
    done
  fi
done

echo ""
echo "Done."
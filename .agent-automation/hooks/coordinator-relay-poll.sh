#!/usr/bin/env bash
set -euo pipefail

state_dir="${COORDINATOR_STATE_DIR:-${HOME}/.agent-automation/coordinator}"
mkdir -p "${state_dir}/inbox"

shopt -s nullglob
for payload in "${state_dir}"/inbox/*.json; do
  "./.agent-automation/hooks/coordinator-relay-handle.sh" --message-file "${payload}"
  rm -f "${payload}"
done
shopt -u nullglob

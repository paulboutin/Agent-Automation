#!/usr/bin/env bash
set -euo pipefail

message_file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --message-file)
      message_file="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 --message-file <path>" >&2
      exit 1
      ;;
  esac
done

[[ -n "${message_file}" && -f "${message_file}" ]] || {
  echo "Usage: $0 --message-file <path>" >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || {
  echo "Missing required command: jq" >&2
  exit 1
}

state_dir="${COORDINATOR_STATE_DIR:-${HOME}/.agent-automation/coordinator}"
mkdir -p "${state_dir}/handled" "${state_dir}/logs"
dedupe_key="$(jq -r '.dedupeKey // .payload.pr_url // "event"' "${message_file}")"
safe_key="$(printf '%s' "${dedupe_key}" | tr '/|: ' '_')"
cp "${message_file}" "${state_dir}/handled/${safe_key}.json"

jq -nc \
  --arg timestamp "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
  --arg dedupe_key "${dedupe_key}" \
  --arg payload_file "${state_dir}/handled/${safe_key}.json" \
  '{timestamp: $timestamp, dedupeKey: $dedupe_key, payload: $payload_file}' >> "${state_dir}/logs/relay-events.jsonl"

if [[ "${COORDINATOR_HANDLER_MODE:-log}" == "launch-next" ]]; then
  "./.agent-automation/hooks/merge-daemon-launch-next.sh" --json --launch || true
fi

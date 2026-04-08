#!/usr/bin/env bash
set -euo pipefail

agent_automation_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

agent_automation_factory_root() {
  printf '%s\n' "$(agent_automation_repo_root)/."
}

agent_automation_profile_path() {
  printf '%s\n' "${AGENT_FACTORY_PROFILE:-$(agent_automation_repo_root)/agent-factory.profile.json}"
}

agent_automation_require_command() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || {
    echo "Missing required command: ${cmd}" >&2
    exit 1
  }
}

agent_automation_make_tempfile() {
  local prefix="$1"
  python3 - "$prefix" <<'PY'
import sys
import tempfile

handle = tempfile.NamedTemporaryFile(prefix=sys.argv[1], delete=False)
handle.close()
print(handle.name)
PY
}

agent_automation_render_message() {
  local template_name="$1"
  shift
  python3 "$(agent_automation_factory_root)/scripts/render-message-template.py" \
    --template "$(agent_automation_factory_root)/templates/messages/${template_name}" \
    "$@"
}

agent_automation_resolve_policy_json() {
  python3 "$(agent_automation_factory_root)/scripts/resolve-repo-policy.py" \
    --repo-root "$(agent_automation_repo_root)" \
    --profile "$(agent_automation_profile_path)"
}

agent_automation_resolve_task_metadata() {
  local body_file="$1"
  local labels_file="$2"
  local mode="${3:-local}"
  python3 "$(agent_automation_factory_root)/scripts/resolve-task-metadata.py" \
    --repo-root "$(agent_automation_repo_root)" \
    --profile "$(agent_automation_profile_path)" \
    --issue-body-file "${body_file}" \
    --labels-json-file "${labels_file}" \
    --model-mode "${mode}"
}

agent_automation_branch_name() {
  local issue_number="$1"
  local lane="$2"
  python3 - "$(agent_automation_profile_path)" "${issue_number}" "${lane}" <<'PY'
import json
import sys
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
fmt = ((profile.get("branches") or {}).get("workerBranchFormat") or "agent/issue-{issue_number}-{lane}").strip()
print(fmt.replace("{issue_number}", sys.argv[2]).replace("{lane}", sys.argv[3]))
PY
}

agent_automation_render_pr_body() {
  python3 "$(agent_automation_factory_root)/scripts/render-pr-body.py" \
    --repo-root "$(agent_automation_repo_root)" \
    --profile "$(agent_automation_profile_path)" \
    "$@"
}

agent_automation_output_path() {
  local key="$1"
  python3 - "$(agent_automation_profile_path)" "${key}" <<'PY'
import json
import sys
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
automation_root = (((profile.get("execution") or {}).get("automationRoot")) or ".agent-automation").strip()
outputs = {
    "issueTemplate": ".github/ISSUE_TEMPLATE/agent-task.yml",
    "pullRequestTemplate": ".github/pull_request_template.md",
    "workflows": {
        "taskWorker": ".github/workflows/agent-task-worker.yml",
        "unblocker": ".github/workflows/agent-unblocker.yml",
        "prWake": ".github/workflows/agent-pr-wake.yml",
    },
    "hooks": {
        "common": f"{automation_root}/hooks/agent-automation-common.sh",
        "workerStart": f"{automation_root}/hooks/local-worker-start.sh",
        "workerFinish": f"{automation_root}/hooks/local-worker-finish.sh",
        "workerLaunchTmux": f"{automation_root}/hooks/local-worker-launch-tmux.sh",
        "workerRunAndRoute": f"{automation_root}/hooks/local-worker-run-and-route.sh",
        "qaLaunchTmux": f"{automation_root}/hooks/local-qa-proof-launch-tmux.sh",
        "qaRun": f"{automation_root}/hooks/local-qa-proof-run.sh",
        "relayHandle": f"{automation_root}/hooks/coordinator-relay-handle.sh",
        "relayPoll": f"{automation_root}/hooks/coordinator-relay-poll.sh",
        "mergeLaunchNext": f"{automation_root}/hooks/merge-daemon-launch-next.sh",
        "mergeStatus": f"{automation_root}/hooks/merge-daemon-status.sh",
    },
    "packs": {
        "review": {
            "checklist": f"{automation_root}/packs/review/checklist.md",
            "prompt": f"{automation_root}/packs/review/prompt.md",
        },
        "qa": {
            "checklist": f"{automation_root}/packs/qa/checklist.md",
            "prompt": f"{automation_root}/packs/qa/prompt.md",
        },
    },
}
value = outputs
for part in sys.argv[2].split("."):
    value = value[part]
print(value)
PY
}

agent_automation_default_host() {
  python3 - "$(agent_automation_profile_path)" <<'PY'
import json
import sys
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(((profile.get("execution") or {}).get("defaultHost") or "codex").strip())
PY
}

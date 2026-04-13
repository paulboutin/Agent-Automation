#!/usr/bin/env python3
import json
import os
import re
from copy import deepcopy
from pathlib import Path


PLACEHOLDER_PATTERNS = {
    "issue_number": r"(?P<issue_number>\d+)",
    "lane": r"(?P<lane>[a-z0-9-]+)",
}

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

HOST_DEFAULTS = {
    "codex": {
        "displayName": "OpenAI Codex CLI",
        "cliCommand": "codex",
        "cliAliases": ["agents"],
        "supportsHosted": True,
        "homeRoot": ".codex/agent-automation",
        "repoRoot": ".agents/agent-automation",
    },
    "claude": {
        "displayName": "Claude Code",
        "cliCommand": "claude",
        "cliAliases": [],
        "supportsHosted": False,
        "homeRoot": ".claude/agent-automation",
        "repoRoot": ".claude/agent-automation",
    },
    "opencode": {
        "displayName": "OpenCode",
        "cliCommand": "opencode",
        "cliAliases": [],
        "supportsHosted": False,
        "homeRoot": ".config/opencode/agent-automation",
        "repoRoot": ".opencode/agent-automation",
    },
}

PACK_DEFAULTS = {
    "automation": True,
    "governance": True,
    "review": True,
    "qa": True,
}


def load_profile(repo_root: Path, explicit_profile: str | None) -> tuple[dict, Path]:
    candidates = []
    if explicit_profile:
        candidates.append(Path(explicit_profile))
    env_profile = os.environ.get("AGENT_FACTORY_PROFILE", "").strip()
    if env_profile:
        candidates.append(Path(env_profile))
    candidates.append(repo_root / "agent-factory.profile.json")
    candidates.append(PACKAGE_ROOT / "examples/upstream-selftest.repo-profile.json")
    candidates.append(PACKAGE_ROOT / "examples/scaffold.repo-profile.json")

    for candidate in candidates:
        path = candidate if candidate.is_absolute() else (repo_root / candidate)
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8")), path

    raise FileNotFoundError("No agent factory profile found")


def resolve_default_base_branch(profile: dict, fallback: str = "development") -> str:
    branches = profile.get("branches") or {}
    return (branches.get("development") or fallback).strip()


def resolve_labels(profile: dict) -> dict[str, str]:
    labels = profile.get("labels") or {}
    return {
        "ready": (labels.get("ready") or "ready").strip(),
        "active": (labels.get("active") or "active").strip(),
        "needsDecision": (labels.get("needsDecision") or "needs-decision").strip(),
        "decisionProposed": (labels.get("decisionProposed") or "decision-proposed").strip(),
        "agentFailed": (labels.get("agentFailed") or "agent-failed").strip(),
        "mergeConflict": (labels.get("mergeConflict") or "merge-conflict").strip(),
        "lanePrefix": (labels.get("lanePrefix") or "agent:").strip(),
    }


def resolve_worker_branch_format(profile: dict) -> str:
    branches = profile.get("branches") or {}
    return (branches.get("workerBranchFormat") or "agent/issue-{issue_number}-{lane}").strip()


def worker_branch_name(worker_branch_format: str, issue_number: int | str, lane: str) -> str:
    return worker_branch_format.replace("{issue_number}", str(issue_number).strip()).replace("{lane}", lane.strip())


def worker_branch_prefix(worker_branch_format: str) -> str:
    return worker_branch_format.split("{", 1)[0]


def worker_branch_regex(worker_branch_format: str) -> str:
    pattern = re.escape(worker_branch_format)
    for placeholder, replacement in PLACEHOLDER_PATTERNS.items():
        pattern = pattern.replace(r"\{" + placeholder + r"\}", replacement)
    return f"^{pattern}$"


def resolve_execution(profile: dict) -> dict:
    execution = deepcopy(profile.get("execution") or {})
    enabled_hosts = list(execution.get("enabledHosts") or ["codex"])
    default_host = (execution.get("defaultHost") or enabled_hosts[0]).strip()
    execution["enabledHosts"] = enabled_hosts
    execution["defaultHost"] = default_host
    execution["hostedEnabled"] = bool(execution.get("hostedEnabled", True))
    execution["automationRoot"] = (execution.get("automationRoot") or ".agent-automation").strip()
    execution["costProfiles"] = execution.get("costProfiles") or {}
    return execution


def resolve_packs(profile: dict) -> dict[str, bool]:
    raw = profile.get("packs") or {}
    resolved = {}
    for name, default in PACK_DEFAULTS.items():
        value = raw.get(name, default)
        resolved[name] = bool(value)
    return resolved


def resolve_host(profile: dict, host_name: str | None = None) -> dict:
    execution = resolve_execution(profile)
    resolved_name = (host_name or execution["defaultHost"]).strip()
    if resolved_name not in HOST_DEFAULTS:
        raise KeyError(f"Unknown host: {resolved_name}")

    config = deepcopy(HOST_DEFAULTS[resolved_name])
    config.update((profile.get("hosts") or {}).get(resolved_name) or {})
    config["name"] = resolved_name
    return config


def resolve_enabled_hosts(profile: dict) -> list[dict]:
    execution = resolve_execution(profile)
    return [resolve_host(profile, host_name) for host_name in execution["enabledHosts"]]


def resolve_output_paths(profile: dict) -> dict:
    automation_root = resolve_execution(profile)["automationRoot"]
    return {
        "automationRoot": automation_root,
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


def resolve_policy(profile: dict, fallback_base_branch: str = "development") -> dict:
    labels = resolve_labels(profile)
    worker_branch_format = resolve_worker_branch_format(profile)
    execution = resolve_execution(profile)
    output_paths = resolve_output_paths(profile)
    default_host = resolve_host(profile, execution["defaultHost"])
    operator_proof = profile.get("operatorProof") or {}

    queue_state_labels = [
        labels["ready"],
        labels["active"],
        labels["needsDecision"],
        labels["decisionProposed"],
        labels["agentFailed"],
    ]

    return {
        "defaultBaseBranch": resolve_default_base_branch(profile, fallback=fallback_base_branch),
        "readyLabel": labels["ready"],
        "activeLabel": labels["active"],
        "needsDecisionLabel": labels["needsDecision"],
        "decisionProposedLabel": labels["decisionProposed"],
        "agentFailedLabel": labels["agentFailed"],
        "mergeConflictLabel": labels["mergeConflict"],
        "lanePrefix": labels["lanePrefix"],
        "queueStateLabels": queue_state_labels,
        "validationBlockingLabels": queue_state_labels,
        "workerBranchFormat": worker_branch_format,
        "workerBranchPrefix": worker_branch_prefix(worker_branch_format),
        "workerBranchRegex": worker_branch_regex(worker_branch_format),
        "defaultHost": default_host["name"],
        "defaultHostDisplayName": default_host["displayName"],
        "defaultHostSupportsHosted": bool(default_host.get("supportsHosted")),
        "hostedEnabled": execution["hostedEnabled"],
        "enabledHosts": execution["enabledHosts"],
        "automationRoot": output_paths["automationRoot"],
        "reviewPackEnabled": resolve_packs(profile)["review"],
        "qaPackEnabled": resolve_packs(profile)["qa"],
        "operatorProofLane": (operator_proof.get("lane") or "qa").strip(),
        "operatorProofLaunchScript": output_paths["hooks"]["qaLaunchTmux"],
        "operatorProofRunScript": f"{output_paths['hooks']['qaRun']} --issue <number>",
        "outputPaths": output_paths,
    }


def resolve_promotion(profile: dict) -> dict:
    promotion = profile.get("promotion") or {}
    transitions = promotion.get("transitions") or []
    integration_branches = promotion.get("integrationBranches") or []
    workstream_branch_map = ((profile.get("templates") or {}).get("pullRequest") or {}).get("workstreamBranchMap") or {}
    transition_by_target = {item["target"]: item for item in transitions}
    transition_by_base = {item["base"]: item for item in transitions}
    transition_by_pair = {(item["head"], item["base"]): item for item in transitions}
    return {
        "integrationBranches": integration_branches,
        "transitions": transitions,
        "transitionByTarget": transition_by_target,
        "transitionByBase": transition_by_base,
        "transitionByPair": transition_by_pair,
        "workstreamBranchMap": workstream_branch_map,
    }

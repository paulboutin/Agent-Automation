#!/usr/bin/env python3
import json
import os
import re
from pathlib import Path


PLACEHOLDER_PATTERNS = {
    "issue_number": r"(?P<issue_number>\d+)",
    "lane": r"(?P<lane>[a-z0-9-]+)",
}

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


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
    candidates.append(PACKAGE_ROOT / "examples/phigure.repo-profile.json")

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
        "lanePrefix": (labels.get("lanePrefix") or "agent:").strip(),
    }


def resolve_worker_branch_format(profile: dict) -> str:
    branches = profile.get("branches") or {}
    return (branches.get("workerBranchFormat") or "codex/issue-{issue_number}-{lane}").strip()


def worker_branch_name(worker_branch_format: str, issue_number: int | str, lane: str) -> str:
    return worker_branch_format.replace("{issue_number}", str(issue_number).strip()).replace("{lane}", lane.strip())


def worker_branch_prefix(worker_branch_format: str) -> str:
    return worker_branch_format.split("{", 1)[0]


def worker_branch_regex(worker_branch_format: str) -> str:
    pattern = re.escape(worker_branch_format)
    for placeholder, replacement in PLACEHOLDER_PATTERNS.items():
        pattern = pattern.replace(r"\{" + placeholder + r"\}", replacement)
    return f"^{pattern}$"


def resolve_policy(profile: dict, fallback_base_branch: str = "development") -> dict:
    labels = resolve_labels(profile)
    worker_branch_format = resolve_worker_branch_format(profile)
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
        "lanePrefix": labels["lanePrefix"],
        "queueStateLabels": queue_state_labels,
        "validationBlockingLabels": queue_state_labels,
        "workerBranchFormat": worker_branch_format,
        "workerBranchPrefix": worker_branch_prefix(worker_branch_format),
        "workerBranchRegex": worker_branch_regex(worker_branch_format),
        "operatorProofLane": (operator_proof.get("lane") or "qa").strip(),
        "operatorProofLaunchScript": (operator_proof.get("launchScript") or "").strip(),
        "operatorProofRunScript": (operator_proof.get("runScript") or "").strip(),
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

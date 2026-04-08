#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ALLOWED_COSTS = {"low", "standard", "high"}
ALLOWED_EFFORTS = {"low", "medium", "high"}


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) != 3:
        return fail("Usage: validate-profile.py <repo-root> <profile-json>")

    repo_root = Path(sys.argv[1]).resolve()
    profile_path = Path(sys.argv[2]).resolve()
    if not profile_path.is_file():
        return fail(f"profile not found: {profile_path}")

    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"invalid JSON in profile: {exc}")

    if profile.get("version") != "repo-profile.v1":
        return fail("profile version must be repo-profile.v1")

    repo = profile.get("repo") or {}
    if not repo.get("id") or not repo.get("name"):
        return fail("repo.id and repo.name are required")

    branches = profile.get("branches") or {}
    if not branches.get("development"):
        return fail("branches.development is required")
    if not isinstance(branches.get("promotion"), list) or not branches["promotion"]:
        return fail("branches.promotion must be a non-empty array")
    if "{issue_number}" not in branches.get("workerBranchFormat", "") or "{lane}" not in branches.get("workerBranchFormat", ""):
        return fail("branches.workerBranchFormat must include {issue_number} and {lane}")

    labels = profile.get("labels") or {}
    for key in ("ready", "active", "needsDecision", "decisionProposed", "agentFailed", "lanePrefix"):
        if not labels.get(key):
            return fail(f"labels.{key} is required")

    roles = profile.get("roles") or []
    if not roles:
        return fail("at least one role is required")
    seen_roles = set()
    for role in roles:
        name = role.get("name")
        if not name or name in seen_roles:
            return fail(f"invalid role: {name}")
        seen_roles.add(name)
        if role.get("defaultCost") not in ALLOWED_COSTS:
            return fail(f"role {name} has unsupported defaultCost")

    lanes = profile.get("lanes") or []
    if not lanes:
        return fail("at least one lane is required")
    seen_lanes = set()
    for lane in lanes:
        name = lane.get("name")
        if not name or name in seen_lanes:
            return fail(f"invalid lane: {name}")
        seen_lanes.add(name)
        if lane.get("defaultCost") not in ALLOWED_COSTS:
            return fail(f"lane {name} has unsupported defaultCost")

    for name in ("low", "standard", "high"):
        entry = (profile.get("costProfiles") or {}).get(name) or {}
        if entry.get("reasoningEffort") not in ALLOWED_EFFORTS:
            return fail(f"costProfiles.{name}.reasoningEffort is invalid")

    protocols = profile.get("protocols") or {}
    if protocols.get("workerStatus") != "worker-status.v1":
        return fail("protocols.workerStatus must be worker-status.v1")
    if protocols.get("workerPrWake") != "worker-pr-wake.v1":
        return fail("protocols.workerPrWake must be worker-pr-wake.v1")

    for rel_path in profile.get("requiredDocs") or []:
        if not (repo_root / rel_path).exists():
            return fail(f"required doc path does not exist: {rel_path}")

    for group_name in ("workflows", "localAutomation", "mergeDaemon"):
        group = profile.get(group_name) or {}
        if not group:
            return fail(f"{group_name} must contain at least one path")
        for rel_path in group.values():
            if not (repo_root / rel_path).exists():
                return fail(f"missing {group_name} path: {rel_path}")

    templates = profile.get("templates") or {}
    if not (templates.get("issueTask") and templates.get("pullRequest")):
        return fail("templates.issueTask and templates.pullRequest are required")

    promotion = profile.get("promotion") or {}
    integration = promotion.get("integrationBranches") or []
    transitions = promotion.get("transitions") or []
    if len(integration) < 2 or not transitions:
        return fail("promotion configuration is incomplete")

    concurrency = profile.get("concurrency") or {}
    helper = concurrency.get("envHelperScript", "")
    if helper and not (repo_root / helper).exists():
        return fail(f"concurrency.envHelperScript path does not exist: {helper}")

    operator = profile.get("operatorProof") or {}
    for key in ("launchScript", "runScript"):
        script = operator.get(key, "").split()[0]
        if script and not (repo_root / script).exists():
            return fail(f"operatorProof.{key} path does not exist: {script}")

    print(f"Profile OK: {profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

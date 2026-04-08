#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

from agent_factory_profile import HOST_DEFAULTS, PACK_DEFAULTS, resolve_output_paths


ALLOWED_COSTS = {"low", "standard", "high"}
ALLOWED_EFFORTS = {"low", "medium", "high"}
SAFE_COMMAND = re.compile(r"^[a-z][a-z0-9_-]*$")
SAFE_RELATIVE_PATH = re.compile(r"^(?!/)[A-Za-z0-9._/${}~/-]+$")
SAFE_HOST_NAME = re.compile(r"^[a-z][a-z0-9-]*$")


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

    if profile.get("version") != "repo-profile.v2":
        return fail("profile version must be repo-profile.v2")

    repo = profile.get("repo") or {}
    if not repo.get("id") or not repo.get("name"):
        return fail("repo.id and repo.name are required")

    platform = profile.get("platform") or {}
    if platform.get("name") != "github":
        return fail("platform.name must be github for v2")

    branches = profile.get("branches") or {}
    if not branches.get("development"):
        return fail("branches.development is required")
    if not isinstance(branches.get("promotion"), list) or not branches["promotion"]:
        return fail("branches.promotion must be a non-empty array")
    worker_branch_format = branches.get("workerBranchFormat", "")
    if "{issue_number}" not in worker_branch_format or "{lane}" not in worker_branch_format:
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

    execution = profile.get("execution") or {}
    enabled_hosts = execution.get("enabledHosts") or []
    if not enabled_hosts:
        return fail("execution.enabledHosts must contain at least one host")
    default_host = execution.get("defaultHost")
    if default_host not in enabled_hosts:
        return fail("execution.defaultHost must be present in execution.enabledHosts")
    automation_root = execution.get("automationRoot") or ""
    if not automation_root or not SAFE_RELATIVE_PATH.match(automation_root):
        return fail("execution.automationRoot must be a safe relative path")

    profile_hosts = profile.get("hosts") or {}
    seen_home_roots = set()
    seen_repo_roots = set()
    for host_name in enabled_hosts:
        if host_name not in HOST_DEFAULTS:
            return fail(f"unknown host in execution.enabledHosts: {host_name}")
        if host_name not in profile_hosts:
            return fail(f"hosts.{host_name} must be configured")
        if not SAFE_HOST_NAME.match(host_name):
            return fail(f"invalid host name: {host_name}")
        host = profile_hosts[host_name] or {}
        cli_command = host.get("cliCommand") or HOST_DEFAULTS[host_name]["cliCommand"]
        if not SAFE_COMMAND.match(cli_command):
            return fail(f"hosts.{host_name}.cliCommand is invalid")
        for alias in host.get("cliAliases", HOST_DEFAULTS[host_name]["cliAliases"]):
            if not SAFE_COMMAND.match(alias):
                return fail(f"hosts.{host_name}.cliAliases contains invalid command: {alias}")
        for key in ("homeRoot", "repoRoot"):
            value = host.get(key) or HOST_DEFAULTS[host_name][key]
            if not SAFE_RELATIVE_PATH.match(value):
                return fail(f"hosts.{host_name}.{key} must be a safe relative path")
        home_root = host.get("homeRoot") or HOST_DEFAULTS[host_name]["homeRoot"]
        repo_root_path = host.get("repoRoot") or HOST_DEFAULTS[host_name]["repoRoot"]
        if home_root in seen_home_roots:
            return fail(f"duplicate host homeRoot: {home_root}")
        if repo_root_path in seen_repo_roots:
            return fail(f"duplicate host repoRoot: {repo_root_path}")
        seen_home_roots.add(home_root)
        seen_repo_roots.add(repo_root_path)

    cost_profiles = execution.get("costProfiles") or {}
    for name in ("low", "standard", "high"):
        entry = cost_profiles.get(name) or {}
        if entry.get("reasoningEffort") not in ALLOWED_EFFORTS:
            return fail(f"execution.costProfiles.{name}.reasoningEffort is invalid")
        host_map = entry.get("hosts") or {}
        for host_name in enabled_hosts:
            host_entry = host_map.get(host_name) or {}
            if not host_entry.get("localModelEnvVar"):
                return fail(f"execution.costProfiles.{name}.hosts.{host_name}.localModelEnvVar is required")

    packs = profile.get("packs") or {}
    for pack_name in PACK_DEFAULTS:
        if pack_name not in packs:
            return fail(f"packs.{pack_name} must be declared")
        if not isinstance(packs[pack_name], bool):
            return fail(f"packs.{pack_name} must be a boolean")

    protocols = profile.get("protocols") or {}
    if protocols.get("workerStatus") != "worker-status.v1":
        return fail("protocols.workerStatus must be worker-status.v1")
    if protocols.get("workerPrWake") != "worker-pr-wake.v1":
        return fail("protocols.workerPrWake must be worker-pr-wake.v1")

    for rel_path in profile.get("requiredDocs") or []:
        if not (repo_root / rel_path).exists():
            return fail(f"required doc path does not exist: {rel_path}")

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

    outputs = resolve_output_paths(profile)
    if not outputs["issueTemplate"].startswith(".github/"):
        return fail("resolved issue template path must live under .github/")

    print(f"Profile OK: {profile_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

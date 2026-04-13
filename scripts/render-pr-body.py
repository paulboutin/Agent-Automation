#!/usr/bin/env python3
import argparse
import re
import subprocess
from pathlib import Path

from agent_factory_profile import (
    load_profile,
    resolve_default_base_branch,
    resolve_promotion,
)


def resolve_workstream(config: dict, head_ref: str) -> str:
    direct = (config.get("workstreamBranchMap") or {}).get(head_ref or "", "")
    if direct:
        return direct
    branch = head_ref or ""
    if branch.startswith("agent/issue-"):
        lane = branch.rsplit("-", 1)[-1]
        lane_map = {
            "backend": "Backend",
            "frontend": "Frontend",
            "infra": "Infra / CI",
            "docs": "Docs / DX",
            "qa": "QA / Release",
        }
        return lane_map.get(lane, "")
    return ""


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def is_test_path(path: str) -> bool:
    lowered = path.lower()
    name = Path(path).name.lower()
    return (
        "/test" in lowered
        or "/tests" in lowered
        or lowered.startswith("test/")
        or lowered.startswith("tests/")
        or "spec" in name
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


def collect_changed_files(repo_root: Path, base_ref: str, head_ref: str) -> list[tuple[str, str]]:
    try:
        output = run_git(repo_root, "diff", "--name-status", f"{base_ref}...{head_ref}")
    except subprocess.CalledProcessError:
        output = run_git(repo_root, "diff", "--name-status", head_ref)

    changed_files: list[tuple[str, str]] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        changed_files.append((status, path))
    return changed_files


def summarize_changes(changed_files: list[tuple[str, str]]) -> dict[str, list[str]]:
    summary = {"added": [], "modified": [], "deleted": [], "renamed": []}
    for status, path in changed_files:
        if status.startswith("A"):
            summary["added"].append(path)
        elif status.startswith("D"):
            summary["deleted"].append(path)
        elif status.startswith("R"):
            summary["renamed"].append(path)
        else:
            summary["modified"].append(path)
    return summary


def format_path_list(paths: list[str], empty_text: str) -> list[str]:
    if not paths:
        return [f"- {empty_text}"]
    return [f"- `{path}`" for path in paths]


def extract_validation_runs(worker_log: Path | None) -> list[dict[str, object]]:
    if not worker_log or not worker_log.is_file():
        return []

    lines = worker_log.read_text(encoding="utf-8", errors="replace").splitlines()
    command_pattern = re.compile(r"^(?:/bin/)?[a-z]+sh -lc ['\"](.+)['\"] in ")
    validation_commands = (
        r"\./scripts/validate\.sh",
        r"npm test",
        r"pnpm test",
        r"yarn test",
        r"pytest",
        r"python3 -m pytest",
        r"python3 -m unittest",
        r"go test",
        r"cargo test",
        r"vitest",
        r"jest",
        r"rspec",
        r"bundle exec rspec",
        r"mvn test",
        r"gradle test",
    )
    validation_hint = re.compile(
        r"(^|[;&| ])(" + "|".join(validation_commands) + r")($|[;&| ])",
        re.IGNORECASE,
    )

    runs: list[dict[str, object]] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() != "exec":
            i += 1
            continue

        if i + 2 >= len(lines):
            break

        command_line = lines[i + 1].strip()
        match = command_pattern.match(command_line)
        if not match:
            i += 1
            continue

        command = match.group(1)
        if not validation_hint.search(command):
            i += 1
            continue

        result_line = lines[i + 2].strip()
        status = "unknown"
        if "succeeded" in result_line:
            status = "passed"
        elif "failed" in result_line:
            status = "failed"

        evidence: list[str] = []
        j = i + 3
        while j < len(lines):
            next_line = lines[j]
            stripped = next_line.strip()
            if stripped == "exec":
                break
            if stripped.startswith("/bin/") and " in " in stripped:
                break
            if stripped.startswith("STATUS: "):
                break
            if stripped:
                evidence.append(stripped)
            j += 1

        runs.append(
            {
                "command": command,
                "status": status,
                "evidence": evidence[:8],
            }
        )
        i = j
    return runs


def render_validation_section(validation_runs: list[dict[str, object]]) -> list[str]:
    if not validation_runs:
        return ["- No validation command output was captured in the worker log."]

    lines: list[str] = []
    for run in validation_runs:
        lines.append(f"- `{run['command']}` ({run['status']})")
        evidence = run["evidence"]
        if evidence:
            lines.extend(f"  - {entry}" for entry in evidence)
    return lines


def render_test_coverage_section(changed_files: list[tuple[str, str]]) -> list[str]:
    added_tests = [path for status, path in changed_files if status.startswith("A") and is_test_path(path)]
    modified_tests = [path for status, path in changed_files if not status.startswith("A") and is_test_path(path)]

    if not added_tests and not modified_tests:
        return ["- No test files were added or updated in this change."]

    lines: list[str] = []
    if added_tests:
        lines.append("- Added test files:")
        lines.extend(f"  - `{path}`" for path in added_tests)
    if modified_tests:
        lines.append("- Updated existing test files:")
        lines.extend(f"  - `{path}`" for path in modified_tests)
    lines.append("- Coverage report: not captured automatically by the worker flow.")
    return lines


def render_breaking_changes_section(changed_files: list[tuple[str, str]]) -> list[str]:
    migration_paths = [
        path
        for _, path in changed_files
        if path.startswith("contracts/") or path.endswith("MIGRATIONS.md") or "migration" in path.lower()
    ]
    if not migration_paths:
        return ["- No breaking changes or migration notes were inferred from the changed files."]
    return [
        "- Review the following files for migration or compatibility impact:",
        *[f"  - `{path}`" for path in migration_paths],
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--mode", choices=["promotion", "autofill"], required=True)
    parser.add_argument("--target")
    parser.add_argument("--head-ref")
    parser.add_argument("--base-ref")
    parser.add_argument("--worker-log")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile, _ = load_profile(repo_root, args.profile)
    config = (profile.get("templates") or {}).get("pullRequest") or {}

    if args.mode == "promotion":
        promotion = resolve_promotion(profile)
        transition = promotion["transitionByTarget"].get(args.target or "")
        if not transition:
            raise SystemExit(f"Unknown promotion target: {args.target}")
        lines = [
            f"# {transition['title']}",
            "",
            transition["summary"],
            "",
            "## Checklist",
        ]
        lines.extend(f"- [ ] {item}" for item in transition.get("checklistItems", []))
        lines.extend(["", "## Promotion Gates"])
        lines.extend(f"- [ ] {item}" for item in transition.get("requiredPromotionGates", []))
        print("\n".join(lines))
        return 0

    head_ref = args.head_ref or "HEAD"
    base_ref = args.base_ref or resolve_default_base_branch(profile)
    workstream = resolve_workstream(config, head_ref)
    changed_files = collect_changed_files(repo_root, base_ref, head_ref)
    summarized_changes = summarize_changes(changed_files)
    validation_runs = extract_validation_runs(
        Path(args.worker_log).resolve() if args.worker_log else None
    )
    lines = [
        "## Summary",
        f"- Auto-generated from `git diff --name-status {base_ref}...{head_ref}`.",
        f"- Total files changed: {len(changed_files)}",
        "",
        "## Changes",
        "### Added",
        *format_path_list(summarized_changes["added"], "No files added."),
        "",
        "### Modified",
        *format_path_list(summarized_changes["modified"], "No files modified."),
        "",
        "### Deleted",
        *format_path_list(summarized_changes["deleted"], "No files deleted."),
        "",
        "### Renamed",
        *format_path_list(summarized_changes["renamed"], "No files renamed."),
        "",
        "## Validation",
        *render_validation_section(validation_runs),
        "",
        "## Test Coverage",
        *render_test_coverage_section(changed_files),
        "",
        "## Breaking Changes / Migration Notes",
        *render_breaking_changes_section(changed_files),
        "",
        "## Workstream",
    ]
    for item in config.get("workstreamOptions", []):
        marker = "x" if item == workstream else " "
        lines.append(f"- [{marker}] {item}")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

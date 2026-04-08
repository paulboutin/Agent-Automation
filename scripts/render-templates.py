#!/usr/bin/env python3
import argparse
import difflib
import os
from pathlib import Path

from agent_factory_profile import (
    PACKAGE_ROOT,
    resolve_default_base_branch,
    resolve_enabled_hosts,
    resolve_execution,
    resolve_host,
    resolve_labels,
    resolve_output_paths,
    resolve_packs,
    resolve_policy,
    load_profile,
)


def indent_lines(lines: list[str], spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" for line in lines)


def replace_tokens(template: str, replacements: dict[str, str]) -> str:
    rendered = template
    for token, value in replacements.items():
        rendered = rendered.replace(f"{{{{{token}}}}}", value)
    return rendered


def inline_value(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def check_or_write(path: Path, rendered: str, write: bool, executable: bool = False) -> list[str]:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    desired_mode = 0o755 if executable else 0o644
    current_mode = path.stat().st_mode & 0o777 if path.exists() else None
    mode_matches = current_mode == desired_mode if current_mode is not None else False

    if current == rendered and (not path.exists() or mode_matches):
        return []
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        os.chmod(path, desired_mode)
        return [f"Updated {path}"]
    diff = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            rendered.splitlines(),
            fromfile=str(path),
            tofile=f"{path} (rendered)",
            lineterm="",
        )
    )
    if current_mode is not None and not mode_matches:
        diff = (diff + "\n" if diff else "") + f"Mode mismatch for {path}: expected {oct(desired_mode)} got {oct(current_mode)}"
    return [diff or f"{path} differs from rendered output"]


def make_common_replacements(profile: dict, repo_root: Path) -> dict[str, str]:
    labels = resolve_labels(profile)
    execution = resolve_execution(profile)
    default_host = resolve_host(profile, execution["defaultHost"])
    enabled_host_names = [host["name"] for host in resolve_enabled_hosts(profile)]
    enabled_host_bullets = "\n".join(f"- `{host}`" for host in enabled_host_names)
    output_paths = resolve_output_paths(profile)
    factory_rel = os.path.relpath(PACKAGE_ROOT, repo_root).replace("\\", "/")
    worker_branch_format = (profile.get("branches") or {}).get("workerBranchFormat", "agent/issue-{issue_number}-{lane}")
    local_worker_launch = output_paths["hooks"]["workerLaunchTmux"]
    local_worker_run = output_paths["hooks"]["workerRunAndRoute"]
    common_hook = output_paths["hooks"]["common"]

    return {
        "FACTORY_PATH": inline_value(factory_rel),
        "AUTOMATION_ROOT": inline_value(output_paths["automationRoot"]),
        "COMMON_HOOK_PATH": inline_value(common_hook),
        "DEFAULT_BASE_BRANCH": inline_value(resolve_default_base_branch(profile)),
        "READY_LABEL": inline_value(labels["ready"]),
        "ACTIVE_LABEL": inline_value(labels["active"]),
        "NEEDS_DECISION_LABEL": inline_value(labels["needsDecision"]),
        "DECISION_PROPOSED_LABEL": inline_value(labels["decisionProposed"]),
        "AGENT_FAILED_LABEL": inline_value(labels["agentFailed"]),
        "LANE_PREFIX": inline_value(labels["lanePrefix"]),
        "DEFAULT_HOST": inline_value(default_host["name"]),
        "DEFAULT_HOST_DISPLAY_NAME": inline_value(default_host["displayName"]),
        "DEFAULT_HOST_SUPPORTS_HOSTED": "true" if default_host.get("supportsHosted") else "false",
        "HOSTED_ENABLED": "true" if execution["hostedEnabled"] else "false",
        "WORKER_BRANCH_FORMAT": inline_value(worker_branch_format),
        "WORKER_BRANCH_PREFIX": inline_value(resolve_policy(profile)["workerBranchPrefix"]),
        "LOCAL_WORKER_LAUNCH": inline_value(local_worker_launch),
        "LOCAL_WORKER_RUN": inline_value(local_worker_run),
        "ENABLED_HOSTS_BULLETS": enabled_host_bullets,
        "REVIEW_PACK_ENABLED": "true" if resolve_packs(profile)["review"] else "false",
        "QA_PACK_ENABLED": "true" if resolve_packs(profile)["qa"] else "false",
    }


def render_issue_template(profile: dict, template_text: str) -> str:
    labels = resolve_labels(profile)
    lane_prefix = labels["lanePrefix"]
    lanes = [f"- {lane_prefix}{lane['name']}" for lane in profile.get("lanes", [])]
    roles = [f"- {role['name']}" for role in profile.get("roles", [])]
    default_base_branch = resolve_default_base_branch(profile)
    config = (profile.get("templates") or {}).get("issueTask") or {}
    return replace_tokens(
        template_text,
        {
            "ISSUE_TEMPLATE_DESCRIPTION": inline_value(config["description"]),
            "READY_LABEL": inline_value(labels["ready"]),
            "ISSUE_TEMPLATE_INTRO": indent_lines(config["introLines"], 8),
            "ISSUE_LANE_OPTIONS": indent_lines(lanes, 8),
            "ISSUE_ROLE_OPTIONS": indent_lines(roles, 8),
            "DEFAULT_BASE_BRANCH": inline_value(default_base_branch),
            "AUTOMATION_SCOPE_PLACEHOLDER": inline_value(config["automationScopePlaceholder"]),
            "OUTCOME_PLACEHOLDER": inline_value(config["outcomePlaceholder"]),
            "SCOPE_PLACEHOLDER": inline_value(config["scopePlaceholder"]),
            "VALIDATION_PLACEHOLDER": indent_lines(config["validationPlaceholderLines"], 8),
            "VALIDATION_DEPENDENCIES_PLACEHOLDER": indent_lines(config["validationDependenciesPlaceholderLines"], 8),
            "BLOCKERS_PLACEHOLDER": inline_value(config["blockersPlaceholder"]),
        },
    )


def render_pr_template(profile: dict, template_text: str) -> str:
    config = (profile.get("templates") or {}).get("pullRequest") or {}
    return replace_tokens(
        template_text,
        {
            "PR_SUMMARY_PROMPTS": "\n".join(f"- {line}" for line in config["summaryPromptLines"]),
            "PR_WORKSTREAM_OPTIONS": "\n".join(f"- [ ] {item}" for item in config["workstreamOptions"]),
            "PR_CHECKLIST_ITEMS": "\n".join(f"- [ ] {item}" for item in config["checklistItems"]),
            "PR_PROMOTION_GATES": "\n".join(f"- [ ] {item}" for item in config["promotionGateItems"]),
        },
    )


def render_pack_markdown(title: str, lines: list[str]) -> str:
    return "\n".join([f"# {title}", "", *lines]).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile, _ = load_profile(repo_root, args.profile)
    output_paths = resolve_output_paths(profile)
    common = make_common_replacements(profile, repo_root)

    issue_template = (PACKAGE_ROOT / "templates/agent-task.yml").read_text(encoding="utf-8")
    pr_template = (PACKAGE_ROOT / "templates/pull-request-template.md").read_text(encoding="utf-8")
    review_prompt_template = (PACKAGE_ROOT / "templates/review/prompt.md").read_text(encoding="utf-8")
    review_checklist_template = (PACKAGE_ROOT / "templates/review/checklist.md").read_text(encoding="utf-8")
    qa_prompt_template = (PACKAGE_ROOT / "templates/qa/prompt.md").read_text(encoding="utf-8")
    qa_checklist_template = (PACKAGE_ROOT / "templates/qa/checklist.md").read_text(encoding="utf-8")

    rendered_issue = render_issue_template(profile, issue_template).rstrip() + "\n"
    rendered_pr = render_pr_template(profile, pr_template).rstrip() + "\n"

    messages = []
    messages.extend(check_or_write(repo_root / output_paths["issueTemplate"], rendered_issue, args.write))
    messages.extend(check_or_write(repo_root / output_paths["pullRequestTemplate"], rendered_pr, args.write))

    static_assets = [
        (PACKAGE_ROOT / "templates/workflows/agent-task-worker.yml", repo_root / output_paths["workflows"]["taskWorker"], False),
        (PACKAGE_ROOT / "templates/workflows/agent-unblocker.yml", repo_root / output_paths["workflows"]["unblocker"], False),
        (PACKAGE_ROOT / "templates/workflows/agent-pr-wake.yml", repo_root / output_paths["workflows"]["prWake"], False),
        (PACKAGE_ROOT / "templates/hooks/agent-automation-common.sh", repo_root / output_paths["hooks"]["common"], True),
        (PACKAGE_ROOT / "templates/hooks/local-worker-start.sh", repo_root / output_paths["hooks"]["workerStart"], True),
        (PACKAGE_ROOT / "templates/hooks/local-worker-finish.sh", repo_root / output_paths["hooks"]["workerFinish"], True),
        (PACKAGE_ROOT / "templates/hooks/local-worker-launch-tmux.sh", repo_root / output_paths["hooks"]["workerLaunchTmux"], True),
        (PACKAGE_ROOT / "templates/hooks/local-worker-run-and-route.sh", repo_root / output_paths["hooks"]["workerRunAndRoute"], True),
        (PACKAGE_ROOT / "templates/hooks/local-qa-proof-launch-tmux.sh", repo_root / output_paths["hooks"]["qaLaunchTmux"], True),
        (PACKAGE_ROOT / "templates/hooks/local-qa-proof-run.sh", repo_root / output_paths["hooks"]["qaRun"], True),
        (PACKAGE_ROOT / "templates/hooks/coordinator-relay-handle.sh", repo_root / output_paths["hooks"]["relayHandle"], True),
        (PACKAGE_ROOT / "templates/hooks/coordinator-relay-poll.sh", repo_root / output_paths["hooks"]["relayPoll"], True),
        (PACKAGE_ROOT / "templates/hooks/merge-daemon-launch-next.sh", repo_root / output_paths["hooks"]["mergeLaunchNext"], True),
        (PACKAGE_ROOT / "templates/hooks/merge-daemon-status.sh", repo_root / output_paths["hooks"]["mergeStatus"], True),
    ]

    for src, dest, executable in static_assets:
        rendered = replace_tokens(src.read_text(encoding="utf-8"), common).rstrip() + "\n"
        messages.extend(check_or_write(dest, rendered, args.write, executable=executable))

    packs = resolve_packs(profile)
    if packs["review"]:
        rendered = replace_tokens(review_prompt_template, common).rstrip() + "\n"
        messages.extend(check_or_write(repo_root / output_paths["packs"]["review"]["prompt"], rendered, args.write))
        rendered = replace_tokens(review_checklist_template, common).rstrip() + "\n"
        messages.extend(check_or_write(repo_root / output_paths["packs"]["review"]["checklist"], rendered, args.write))
    if packs["qa"]:
        rendered = replace_tokens(qa_prompt_template, common).rstrip() + "\n"
        messages.extend(check_or_write(repo_root / output_paths["packs"]["qa"]["prompt"], rendered, args.write))
        rendered = replace_tokens(qa_checklist_template, common).rstrip() + "\n"
        messages.extend(check_or_write(repo_root / output_paths["packs"]["qa"]["checklist"], rendered, args.write))

    if messages and not args.write:
        for message in messages:
            print(message)
        return 1

    for message in messages:
        print(message)
    if not messages:
        print("Templates match rendered output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

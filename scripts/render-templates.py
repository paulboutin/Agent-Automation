#!/usr/bin/env python3
import argparse
import difflib
from pathlib import Path

from agent_factory_profile import PACKAGE_ROOT, load_profile, resolve_default_base_branch, resolve_labels


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
            "BLOCKERS_PLACEHOLDER": inline_value(config["blockersPlaceholder"])
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


def check_or_write(path: Path, rendered: str, write: bool) -> list[str]:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == rendered:
        return []
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
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
    return [diff or f"{path} differs from rendered output"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile, _ = load_profile(repo_root, args.profile)

    issue_template = (PACKAGE_ROOT / "templates/agent-task.yml").read_text(encoding="utf-8")
    pr_template = (PACKAGE_ROOT / "templates/pull-request-template.md").read_text(encoding="utf-8")

    rendered_issue = render_issue_template(profile, issue_template).rstrip() + "\n"
    rendered_pr = render_pr_template(profile, pr_template).rstrip() + "\n"

    messages = []
    messages.extend(check_or_write(repo_root / ".github/ISSUE_TEMPLATE/agent-task.yml", rendered_issue, args.write))
    messages.extend(check_or_write(repo_root / ".github/pull_request_template.md", rendered_pr, args.write))

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

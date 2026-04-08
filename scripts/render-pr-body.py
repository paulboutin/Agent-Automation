#!/usr/bin/env python3
import argparse

from agent_factory_profile import load_profile, resolve_promotion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--mode", choices=["promotion", "autofill"], required=True)
    parser.add_argument("--target")
    parser.add_argument("--head-ref")
    args = parser.parse_args()

    profile, _ = load_profile(__import__("pathlib").Path(args.repo_root).resolve(), args.profile)
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

    workstream = (config.get("workstreamBranchMap") or {}).get(args.head_ref or "", "")
    lines = [
        "## Summary",
        *(f"- {item}" for item in config.get("summaryPromptLines", [])),
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

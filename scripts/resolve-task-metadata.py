#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

from agent_factory_profile import load_profile


def read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def parse_field(body: str, field_name: str) -> str:
    pattern = re.compile(rf"^###\s+{re.escape(field_name)}\s*$", re.MULTILINE)
    match = pattern.search(body)
    if not match:
        return ""
    start = match.end()
    tail = body[start:]
    next_header = re.search(r"^###\s+", tail, re.MULTILINE)
    value = tail[: next_header.start() if next_header else len(tail)].strip()
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--issue-body-file")
    parser.add_argument("--labels-json-file")
    parser.add_argument("--model-mode", choices=["hosted", "local"], default="local")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    profile, _ = load_profile(repo_root, args.profile)
    body = read_text(args.issue_body_file)
    labels = json.loads(read_text(args.labels_json_file) or "[]")
    label_names = set(labels)

    role = parse_field(body, "Agent role") or "implementer"
    lane = parse_field(body, "Lane")
    if lane.startswith("agent:"):
        lane = lane.split(":", 1)[1].strip()
    if not lane:
        lane = "backend"
        for label in label_names:
            if label.startswith((profile.get("labels") or {}).get("lanePrefix", "agent:")):
                lane = label.split(":", 1)[1]
                break

    explicit_cost = ""
    for label in label_names:
        if label.startswith("cost:"):
            explicit_cost = label.split(":", 1)[1].strip()
            break
    explicit_cost = explicit_cost or parse_field(body, "Cost profile")

    role_map = {item["name"]: item for item in profile.get("roles", [])}
    lane_map = {item["name"]: item for item in profile.get("lanes", [])}
    cost_name = explicit_cost or role_map.get(role, {}).get("defaultCost") or lane_map.get(lane, {}).get("defaultCost") or "standard"
    cost = (profile.get("costProfiles") or {}).get(cost_name, {})
    model_key = "hostedModelVar" if args.model_mode == "hosted" else "localModelVar"

    result = {
        "role": role,
        "lane": lane,
        "costProfile": cost_name,
        "reasoningEffort": cost.get("reasoningEffort", "medium"),
        "modelEnvVar": cost.get(model_key, ""),
        "baseBranch": parse_field(body, "Base branch") or (profile.get("branches") or {}).get("development", "development"),
        "scope": parse_field(body, "Automation scope"),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

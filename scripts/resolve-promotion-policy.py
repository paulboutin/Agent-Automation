#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from agent_factory_profile import load_profile, resolve_promotion


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    parser.add_argument("--target")
    args = parser.parse_args()

    profile, _ = load_profile(Path(args.repo_root).resolve(), args.profile)
    promotion = resolve_promotion(profile)
    if args.target:
        transition = promotion["transitionByTarget"].get(args.target)
        if not transition:
            raise SystemExit(f"Unknown target: {args.target}")
        print(json.dumps(transition, indent=2))
        return 0
    print(json.dumps(promotion, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

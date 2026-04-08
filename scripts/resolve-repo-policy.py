#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from agent_factory_profile import load_profile, resolve_policy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile")
    args = parser.parse_args()

    profile, _ = load_profile(Path(args.repo_root).resolve(), args.profile)
    print(json.dumps(resolve_policy(profile), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
import argparse
import os
import re
from pathlib import Path


TOKEN_RE = re.compile(r"{{([a-zA-Z0-9_]+)}}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True)
    parser.add_argument("--var", action="append", default=[])
    args = parser.parse_args()

    values: dict[str, str] = {}
    for entry in args.var:
        if "=" not in entry:
            raise SystemExit(f"Invalid --var value: {entry}")
        key, value = entry.split("=", 1)
        values[key] = value

    template = Path(args.template).read_text(encoding="utf-8")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in values:
            return values[key]
        if key in os.environ:
            return os.environ[key]
        return ""

    print(TOKEN_RE.sub(replace, template).rstrip() + "\n", end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

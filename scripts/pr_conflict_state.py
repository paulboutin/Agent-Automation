#!/usr/bin/env python3
import argparse
import json


CONFLICT_STATES = {"dirty"}
CLEAN_STATES = {"clean", "has_hooks", "unstable"}
BLOCKED_STATES = {"blocked", "behind", "draft"}
PENDING_STATES = {"", "unknown"}


def parse_mergeable(value: str | None) -> bool | None:
    normalized = (value or "").strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def classify_pr_conflict(
    mergeable: bool | None, mergeable_state: str | None, draft: bool = False
) -> dict[str, object]:
    state = (mergeable_state or "").strip().lower()

    if draft or state == "draft":
        classification = "blocked"
        has_conflict = False
        reason = "PR is still a draft."
    elif state in CONFLICT_STATES or mergeable is False:
        classification = "conflict"
        has_conflict = True
        reason = "GitHub reports merge conflicts against the base branch."
    elif state in BLOCKED_STATES:
        classification = "blocked"
        has_conflict = False
        reason = "PR is blocked for a non-conflict reason."
    elif state in CLEAN_STATES or mergeable is True:
        classification = "clean"
        has_conflict = False
        reason = "GitHub reports the PR can merge without conflicts."
    elif state in PENDING_STATES and mergeable is None:
        classification = "pending"
        has_conflict = False
        reason = "GitHub has not finished computing mergeability yet."
    else:
        classification = "pending"
        has_conflict = False
        reason = "Mergeability state is still inconclusive."

    return {
        "classification": classification,
        "has_conflict": has_conflict,
        "mergeable": mergeable,
        "mergeable_state": state,
        "reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mergeable", default="")
    parser.add_argument("--mergeable-state", default="")
    parser.add_argument("--draft", default="false")
    args = parser.parse_args()

    result = classify_pr_conflict(
        parse_mergeable(args.mergeable),
        args.mergeable_state,
        draft=parse_mergeable(args.draft) is True,
    )
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

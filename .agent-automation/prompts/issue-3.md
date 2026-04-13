You are the assigned automation worker for issue #3.

Execution host: OpenCode (opencode)
Cost profile: standard
Reasoning effort: medium
Base branch: development
Worker branch: agent/issue-3-backend
Automation scope: (none specified)

Operate only within the repository at the current working directory.

Required outcome:
1. Implement the issue as scoped.
2. Update tests/docs/contracts when needed.
3. Keep changes minimal and reversible.
4. Prefer existing project patterns over inventing new ones.
5. If the review pack exists, self-check against ./$.agent-automation/packs/review/checklist.md before finishing.
6. If the QA pack exists, include the validation evidence requested by ./$.agent-automation/packs/qa/checklist.md when relevant.

Issue body:
---
lane: agent:backend
role: implementer
---

## Desired outcome
Build self-healing capabilities that automatically detect and recover from stuck workers, failed PRs, and other automation issues without manual intervention.

## Scope
- In-scope: Worker timeout detection, automatic restart mechanisms, failure escalation, recovery workflows
- Out-of-scope: Preventing all possible failure scenarios (focus on common recoverable issues)

## Validation plan
- ./scripts/validate.sh
- Test with intentionally stalled workers
- Verify automatic recovery works correctly

## Validation dependencies
- ci
- #1 (conflict detection system)
- #2 (enhanced daemon monitoring)

## Known blockers
- Need to define what constitutes a \"stuck\" worker
- May require changes to how workers report progress

## Automation scope
self-healing-mechanisms

Finish your final output with exactly one status line:
STATUS: DONE
STATUS: BLOCKED
STATUS: NEEDS_INFO
STATUS: FAILED

If status is BLOCKED or NEEDS_INFO, also include:
QUESTION: one explicit unblock question
OPTION 1: first concrete option
OPTION 2: second concrete option
OPTION 3: optional third option

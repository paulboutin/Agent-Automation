# Review Pack

Use this pack when a worker or operator needs a concise quality gate before marking work complete.

Enabled hosts:
- `codex`
- `claude`
- `opencode`

Review loop:
- Read the issue scope and recent comments.
- Review the diff or branch changes against the issue goal.
- Prioritize bugs, regressions, missing tests, and unsafe rollout assumptions.
- Produce findings first, then a short summary.
- Use `./.agent-automation/packs/review/checklist.md` as the final pass.

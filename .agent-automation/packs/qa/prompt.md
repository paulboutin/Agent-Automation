# QA Pack

Use this pack when implementation work needs validation evidence or operator-proof follow-up.

QA loop:
- Read the issue scope and the claimed implementation result.
- Choose the smallest validation set that proves the scoped outcome.
- Record commands run, environments used, and observed results.
- If proof must happen on a trusted machine, use `./.agent-automation/hooks/local-qa-proof-run.sh --issue <number>`.
- Use `./.agent-automation/packs/qa/checklist.md` before closing the task.

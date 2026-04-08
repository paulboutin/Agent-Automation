# Bootstrap Plan

## Objective

Turn `Agent-Automation` into the upstream factory for repo automation so future projects start from this scaffold instead of copying Phigure-specific automation directly.

## Current State

The repository now contains:

- portable contracts for worker status and PR wake events
- canonical issue and PR templates
- portable message templates
- profile-backed policy resolution helpers
- install, update, render, validate, and smoke scripts
- consumer and upstream example profiles
- placeholder workflow and hook templates

This is enough to start a new project from a clean directory and vendor the factory into it.

## Immediate Next Steps

1. Keep `Agent-Automation` as the only upstream source of truth for factory code.
2. Start the next project from a clean repo or clean project directory.
3. Install this factory into that project with:

```bash
./tools/agent-factory/scripts/install.sh --target .
```

4. Customize `agent-factory.profile.json`.
5. Replace placeholder workflows and hooks with project-specific implementations or thin wrappers.
6. Add optional specialist packs after the core install path is stable.

## What To Grab From Phigure Now

These are the high-value assets worth copying into `Agent-Automation` or keeping nearby before moving to a clean project:

### Automation Design Docs

- `docs/sprints/COORDINATOR_AGENT_AUTOMATION.md`
- `docs/runbooks/DEV_COORDINATOR_RELAY_RUNBOOK.md`

These describe the current coordinator/worker/daemon operating rules and failure-routing behavior. They are the best reference for rebuilding the real generic workflow pack from the current placeholders.

### Worker / Coordinator / Daemon Scripts

- `scripts/agent-session-preflight.sh`
- `scripts/local-worker-start.sh`
- `scripts/local-worker-finish.sh`
- `scripts/local-worker-launch-tmux.sh`
- `scripts/local-worker-run-and-route.sh`
- `scripts/local-qa-proof-launch-tmux.sh`
- `scripts/local-qa-proof-run.sh`
- `scripts/coordinator-relay-handle.sh`
- `scripts/coordinator-relay-poll.sh`
- `scripts/merge-daemon-launch-next.sh`
- `scripts/merge-daemon-status.sh`
- `scripts/merge-daemon-recover-failed.sh`
- `scripts/merge-daemon-recover-conflicts.sh`
- `scripts/merge-daemon-issue-state.py`
- `scripts/issue-validation-plan.py`
- `scripts/resolve-worker-pr-context.js`

These are the most likely inputs for replacing the placeholder hook pack with a real generic implementation.

### Promotion / Governance Scripts

- `scripts/enforce-pr-branch-policy.sh`
- `scripts/enforce-pr-checklist.sh`
- `scripts/validate-automation-ci-guardrails.sh`
- `scripts/check-ai-runtime-edge-smoke-gate.sh`

These are the best reference for the promotion pack and repo-governance rules.

### GitHub Workflows

- `.github/workflows/codex-task-worker.yml`
- `.github/workflows/codex-unblocker.yml`
- `.github/workflows/codex-coordinator-pr-wake.yml`
- `.github/workflows/create-promotion-pr.yml`
- `.github/workflows/pr-body-autofill.yml`
- `.github/workflows/pr-governance.yml`

These should become the first real workflow template pack in `Agent-Automation`.

### Existing Rendered Templates

- `.github/ISSUE_TEMPLATE/agent-task.yml`
- `.github/pull_request_template.md`

These are useful for confirming consumer output against current Phigure behavior.

## What Not To Pull Into Core

Do not move these into generic factory core unless they are rewritten into a neutral pack:

- Phigure AI architecture docs
- product-specific runbooks
- AWS/runtime smoke procedures tied to Phigure APIs
- iOS / Swift / HealthKit domain rules
- Phigure-specific lane naming or branch naming beyond examples

Those belong either in:

- `examples/phigure.repo-profile.json`
- a Phigure-specific pack
- a consumer repo migration guide

## Suggested Extraction Order

1. Bring over the two automation docs as historical/reference material.
2. Rebuild the real hook pack from the Phigure worker/coordinator/daemon scripts.
3. Rebuild the GitHub workflow template pack from the Phigure workflows.
4. Add a promotion/governance pack from the PR and smoke guardrail scripts.
5. Add specialist-pack support after the core workflow pack is stable.

## Definition Of Done For The Factory

The factory is in good shape for broader reuse when:

- a clean consumer repo can install it and validate successfully
- the placeholder hook/workflow templates are replaced by real generic packs
- Phigure can consume it without custom edits inside factory core
- specialist packs can be enabled by profile instead of hand wiring

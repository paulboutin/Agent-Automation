# Operating Model

The factory is split into two layers:

- `core`
  Contracts, scripts, templates, and shared process rules.
- `repo profile`
  Branches, labels, lanes, roles, docs, promotion rules, and hook paths.

## Current Scope

The current scaffold covers:

- worker status contracts
- PR wake contracts
- role-to-cost defaults
- queue label policy
- branch naming policy
- promotion transition policy
- canonical issue and PR templates
- portable message templates
- install, render, validate, and smoke commands

## Concurrent Workstreams

Concurrent workstreams are namespaced by base branch and optional scope.

Example:

```bash
eval "$(./tools/agent-factory/scripts/automation-scope-env.sh --base-branch codex/feature-branch)"
```

## Hooks

Hooks are the repo-specific seam:

- worker start/finish
- tmux launchers
- coordinator relay
- merge daemon
- operator-proof QA

If multiple repos need the same hook behavior, promote it into core.

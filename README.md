# Agent Automation Factory

Portable coordinator/worker/daemon scaffolding for repo automation.

This repository is the upstream source for:

- versioned automation contracts
- portable issue and PR templates
- profile-backed policy resolution
- install, update, render, validate, and smoke commands
- placeholder workflow and hook packs for consuming repos

The intended model is:

- `factory core` stays in this repo
- each consuming repo keeps an `agent-factory.profile.json`
- repo-specific behavior stays in hooks or thin wrappers
- future upgrades happen by updating the vendored package instead of hand-editing automation again

## Layout

- `contracts/`
- `docs/`
- `examples/`
- `scripts/`
- `templates/`

## Profiles

- `examples/upstream-selftest.repo-profile.json`
  Used to validate this repository as the upstream source.
- `examples/scaffold.repo-profile.json`
  Copied into consumer repos by `install.sh` as the default profile.
- `examples/phigure.repo-profile.json`
  Example migration profile for Phigure.

## Upstream Validation

```bash
./scripts/validate.sh
./scripts/smoke.sh
```

## Consumer Install

Install into a target repository:

```bash
./scripts/install.sh --target /path/to/repo
```

Refresh an existing installation:

```bash
./scripts/update.sh --target /path/to/repo
```

After installation, the consumer repo can render its GitHub templates with:

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
```

## Concurrency

The factory supports isolated concurrent workstreams by base branch.

Example:

```bash
eval "$(./tools/agent-factory/scripts/automation-scope-env.sh --base-branch codex/feature-auth)"
```

## Portability Rule

If a change needs a hardcoded repo name, branch name, label name, validation command, or environment contract in core logic, it probably belongs in the repo profile or a repo hook instead.

# Adoption Guide

## Objective

Adopt the factory in another repository without carrying over repo-specific assumptions into the new repo.

## Recommended Consumer Layout

```text
tools/
  agent-factory/
agent-factory.profile.json
.agent-automation/
```

## Adoption Steps

1. Install the package:

```bash
./tools/agent-factory/scripts/install.sh --target .
```

2. Edit `agent-factory.profile.json`:
   - repo identity
   - branches and labels
   - enabled hosts and default host
   - enabled packs
   - cost profile model env vars
   - promotion flow

3. Render assets:

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
```

4. Validate and smoke:

```bash
./tools/agent-factory/scripts/validate.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/smoke.sh --repo-root . --profile ./agent-factory.profile.json
```

## Consumer Ownership

Upstream factory owns:

- contracts
- host defaults
- packs
- render and validation logic

Consumer repo owns:

- the profile
- model env var values
- repo-specific wrappers or overrides
- any trusted local runtime or QA commands

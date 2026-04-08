# Adoption Guide

## Objective

Adopt the factory in another repository without copying Phigure-specific assumptions into the new repo.

## Recommended Consumer Layout

```text
tools/
  agent-factory/
agent-factory.profile.json
```

## Adoption Steps

1. Install the package:

```bash
./tools/agent-factory/scripts/install.sh --target .
```

2. Edit `agent-factory.profile.json` for the target repo:
   - branches
   - labels
   - roles
   - lanes
   - required docs
   - promotion flow
   - hook and workflow paths

3. Render templates:

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
```

4. Validate:

```bash
./tools/agent-factory/scripts/validate.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/smoke.sh --repo-root . --profile ./agent-factory.profile.json
```

5. Replace placeholder hooks and workflows with repo-owned implementations, or keep them as thin wrappers around existing automation.

## Shadow Mode

The safe path is to run the package in shadow mode first:

- keep current entrypoints live
- add profile and validation
- render the templates
- compare decisions before cutover

## Ownership

- upstream repo owns contracts, templates, docs, and generic scripts
- consumer repo owns the profile and repo-specific hooks

# Quickstart

## 1. Install The Factory

From this repository:

```bash
./scripts/install.sh --target /path/to/repo
```

This vendors the factory into `tools/agent-factory/`, writes `agent-factory.profile.json` if needed, and renders the default assets.

## 2. Choose A Host

Edit `agent-factory.profile.json`:

- set `execution.defaultHost`
- narrow `execution.enabledHosts` if you do not want all v1 hosts enabled
- set host model environment variables under `execution.costProfiles`

Examples are provided in:

- `examples/codex.repo-profile.json`
- `examples/claude.repo-profile.json`
- `examples/opencode.repo-profile.json`

## 3. Render Consumer Assets

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
```

Rendered outputs include:

- issue template
- PR template
- GitHub workflows
- local hooks
- review pack
- QA pack

## 4. Validate

```bash
./tools/agent-factory/scripts/validate.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/smoke.sh --repo-root . --profile ./agent-factory.profile.json
```

## 5. Use The Worker Loop

Create a task issue from the rendered issue template, then run:

```bash
./.agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number>
```

For operator-proof work:

```bash
./.agent-automation/hooks/local-qa-proof-launch-tmux.sh <issue-number>
```

## Hosted Worker Note

Hosted GitHub execution is v1-supported only for Codex. Claude and OpenCode follow the same queue model but run locally through the rendered hooks.

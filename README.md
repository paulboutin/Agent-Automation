# Agent Automation Factory

Host-agnostic, GitHub-first automation scaffolding for repository work queues, worker issue flows, local agent runners, and reusable review and QA packs.

This repository is the upstream source for:

- versioned automation contracts
- `repo-profile.v2` configuration
- declarative host configuration for Codex, Claude, and OpenCode
- reusable automation, governance, review, and QA packs
- install, render, validate, and smoke commands
- **Agent role definition and configuration tools**

## What It Does

The factory gives a consumer repository a consistent automation surface:

- GitHub issue intake with a canonical task form
- worker branch naming and PR wake behavior
- hosted worker workflow support where the selected host supports it
- local worker hooks for trusted or host-specific execution
- reusable review and QA methodology packs
- promotion and merge-daemon support hooks

The design goal is to keep generic automation in one upstream package while moving repo-specific policy into the consumer profile.

## Product Model

The factory is split into three layers:

- `core`
  Contracts, profile loading, render logic, and shared scripts.
- `hosts`
  Declarative host settings for supported local and hosted AI runners.
- `packs`
  Reusable behavior bundles such as automation workflows, governance hooks, review checklists, and QA playbooks.

## Supported Hosts

V1 host implementations:

- `codex`
- `claude`
- `opencode`

GitHub-hosted automation is available only when the selected default host supports it. In v1 that means Codex. Claude and OpenCode use the same issue, branch, and queue model through the rendered local hooks.

## Supported Packs

- `automation`
  Task intake, worker dispatch, unblocker, PR wake, and local worker hooks.
- `governance`
  Merge-daemon status and launch-next hooks plus promotion helpers.
- `review`
  Review checklist and prompt pack.
- `qa`
  QA checklist and prompt pack plus operator-proof hook seam.

## Agent Automation Tools

This repository includes specialized tools for configuring and running AI agents with role-based model selection:

### Configuration Scripts

- `scripts/configure_agents.py` - Interactive tool to define agent roles and their associated AI models
- `scripts/define_role.py` - Interactive tool to define new agent roles with custom names and cost levels
- `scripts/run_agent_with_fallback.py` - Runs agents with automatic model configuration fallback when models aren't available

### Execution Scripts

- `tools/agent-factory/scripts/agent_factory.py` - Main agent runner that executes roles with configured models

## Quick Start

Install into a target repository:

```bash
./scripts/install.sh --target /path/to/repo
```

Configure agent roles and models:

```bash
# Interactive configuration of agent roles and their models
python scripts/configure_agents.py

# Define new custom agent roles
python scripts/define_role.py
```

Render assets in that consumer repo:

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
```

Validate the result:

```bash
./tools/agent-factory/scripts/validate.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/smoke.sh --repo-root . --profile ./agent-factory.profile.json
```

Run the upstream package checks in this repo:

```bash
./scripts/validate.sh
./scripts/smoke.sh
```

## Using Agent Automation

### 1. Configure Agent Roles and Models

```bash
# Set up which AI models each agent role should use
python scripts/configure_agents.py
```

This creates/updates `agent-factory.profile.json` with your model selections for each role and host combination.

### 2. Define Custom Agent Roles

```bash
# Create new agent roles beyond the default set
python scripts/define_role.py
```

You'll be prompted for:
- Role name (e.g., "architect", "analyst", "tester")
- Cost level (low/standard/high) which determines model capability
- Model preferences for each host (opencode/codex/claude)

### 3. Run Agents with Configured Models

```bash
# Run a specific agent role with its configured model
python tools/agent-factory/scripts/agent_factory.py \
  --role implementer \
  --host opencode \
  --task "Implement user authentication system"

# List available roles
python tools/agent-factory/scripts/agent_factory.py --list-roles

# Run with automatic fallback if models aren't available
python scripts/run_agent_with_fallback.py \
  --role operator \
  --host opencode \
  --task "Design system architecture"
```

## Local Worker Flow

Typical local execution path:

1. Create a task issue from the rendered issue template.
2. Ensure it has one lane and one role.
3. Launch local workers:

```bash
./.agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number>
```

4. The hook prepares a worktree, prompt file, and branch, then invokes the configured host CLI.
5. Completion routes back to the issue and PR flow through `local-worker-finish.sh`.

## Concurrent Workstreams

Concurrent workstreams are namespaced by base branch and optional scope.

Example:

```bash
eval "$(./tools/agent-factory/scripts/automation-scope-env.sh --base-branch agent/feature-auth)"
```

## Documentation

- [Quickstart](./docs/QUICKSTART.md)
- [Adoption Guide](./docs/ADOPTION_GUIDE.md)
- [Operating Model](./docs/OPERATING_MODEL.md)
- [Host Model](./docs/HOST_MODEL.md)
- [Pack Model](./docs/PACK_MODEL.md)
- [Profile Reference](./docs/PROFILE_REFERENCE.md)
- [Operations Guide](./docs/OPERATIONS.md)
- [Migrations](./docs/MIGRATIONS.md)
- **Agent Automation Tools** (this README)

## Repository Layout

- `contracts/`
- `docs/`
- `examples/`
- `scripts/`
  - `configure_agents.py` - Configure agent roles and models
  - `define_role.py` - Define new custom agent roles
  - `run_agent_with_fallback.py` - Run agents with fallback configuration
  - `compile.py` - Knowledge base compiler
  - `query.py` - Knowledge base query system
  - `lint.py` - Knowledge base health checks
  - And other utility scripts
- `templates/`
- `tools/agent-factory/`
  - `scripts/`
    - `agent_factory.py` - Main agent execution script
    - And other factory scripts
- `knowledge/` - Compiled knowledge base (gitignored)
- `daily/` - Conversation logs (gitignored)

## Portability Rule

If a change needs a hardcoded repo name, branch name, label name, validation command, or runtime command in generic core logic, it probably belongs in the repo profile, host config, or a consumer-owned wrapper.
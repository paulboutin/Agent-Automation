# Operating Model

## Prerequisites

- **Python 3.12+** - Required runtime
- **Git** - Version control
- **GitHub CLI (`gh`)** - GitHub API authentication
- ** pip** - Package manager

## Setup

1. Install dependencies:
   ```bash
   pip install -e .
   ```

2. Configure GitHub authentication:
   ```bash
   gh auth login
   ```

3. Verify installation:
   ```bash
   ./scripts/validate.sh
   ```

## Dependencies

Project dependencies are defined in `pyproject.toml`:
- `claude-agent-sdk>=0.1.29` - AI agent SDK
- `flask>=3.0.0` - Web framework
- `python-dotenv>=1.0.0` - Environment variables
- `textual>=0.62.0` - TUI framework
- `tzdata>=2024.1` - Timezone data

---

The factory is organized around:

- `core`
  Contracts, rendering, validation, and profile resolution.
- `hosts`
  Declarative settings for supported AI runners.
- `packs`
  Reusable automation, governance, review, and QA behavior.

## Current Scope

The v2 scaffold covers:

- worker status and PR wake contracts
- queue label policy
- worker branch naming policy
- promotion transition policy
- issue and PR templates
- GitHub automation workflows
- local worker, QA, relay, and merge-daemon hooks
- review and QA methodology packs

## GitHub-First Boundary

Repository orchestration stays GitHub-first in v1:

- GitHub issues for task intake
- GitHub PRs for worker outputs
- GitHub Actions for hosted automation where supported
- local hooks for trusted or host-specific execution

Host portability is part of v1. Git-provider portability is not.

## Concurrent Workstreams

Concurrent workstreams are namespaced by base branch and optional scope.

Example:

```bash
eval "$(./tools/agent-factory/scripts/automation-scope-env.sh --base-branch agent/feature-branch)"
```

## Promotion Rule

Generic core owns shared process behavior. Consumer repos own repo-specific validation commands, policy wrappers, and environment assumptions through the profile or local wrappers.

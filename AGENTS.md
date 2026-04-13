# Agent Automation Factory

This repo provides an agentic automation framework for coordinating AI workers to implement GitHub issues.

## Quick Start

1. **Create an issue** using `.github/ISSUE_TEMPLATE/agent-task.yml`
2. **Add `ready` label** to trigger worker dispatch
3. **Worker picks up issue**, creates branch, implements, opens PR
4. **PR validates** automatically, human reviews and merges

## Issue Labels

| Label | Description |
|-------|------------|
| `ready` | Issue dispatch to worker |
| `active` | Worker is actively working |
| `done` | Worker completed successfully |
| `blocked` | Worker blocked, needs input |
| `needs-decision` | Requires human decision |
| `agent-failed` | Worker failed, needs retry |

## Worker Labels

Use lane labels to route to specific workers:

- `agent:backend` - Backend/implementation
- `agent:frontend` - Frontend/UI work
- `agent:infra` - Infrastructure/CI
- `agent:docs` - Documentation
- `agent:qa` - QA/review work

## Local Worker Commands

### Start a worker on an issue:

```bash
.agent-automation/hooks/local-worker-start.sh --json <issue-number>
```

### Launch worker in tmux:

```bash
.agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number>
```

### Run worker directly:

```bash
.agent-automation/hooks/local-worker-run-and-route.sh \
  --issue <number> \
  --branch agent/issue-<number>-<lane> \
  --prompt .agent-automation/prompts/issue-<number>.md \
  --host opencode
```

## Daemon Commands

### Check worker status:

```bash
.agent-automation/hooks/merge-daemon-status.sh
```

### Launch next ready issue:

```bash
.agent-automation/hooks/merge-daemon-launch-next.sh
```

## Validation

Run validation before committing:

```bash
./scripts/validate.sh
```

This checks:
- JSON schemas valid
- Profile valid
- Templates match rendered output
- No conflict markers in changes

## File Structure

```
.agent-automation/
  hooks/           # Local worker hooks
    local-worker-start.sh
    local-worker-run-and-route.sh
    local-worker-launch-tmux.sh
    local-worker-finish.sh
    merge-daemon-*.sh
  packs/           # Review/QA prompts
.github/
  ISSUE_TEMPLATE/ # Issue intake templates
  workflows/     # GitHub Actions
contracts/        # JSON schemas
templates/        # Rendered templates
scripts/          # Factory scripts
docs/             # Operating model
```

## Worker Output Format

Workers must end output with exactly one status line:

```
STATUS: DONE
STATUS: BLOCKED
STATUS: NEEDS_INFO
STATUS: FAILED
```

If blocked/needs-info, also include:

```
QUESTION: <unblock question>
OPTION 1: <first option>
OPTION 2: <second option>
```

## Profiles

Edit `agent-factory.profile.json` to configure:
- Enabled hosts
- Default model per host
- Labels and branch naming
- Promotion policy
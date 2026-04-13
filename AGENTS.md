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

## 16) Coordinator/Worker Automation Protocol

- Coordinator creates one GitHub Issue per task and applies:
  - exactly one lane label: `agent:<lane>`
  - one cost label: `cost:low|cost:standard|cost:high` (or explicit cost in issue body)
  - `ready` when a worker should start
- Tracking conventions:
  - milestones represent delivery tracks or release bundles
  - projects represent **features/workstreams**
- Worker runs are automation-driven (issue label dispatch).

### Worker Status End States

Every worker must end output with exactly one terminal status line:
- `STATUS: DONE` - Task completed successfully - PR should be opened
- `STATUS: BLOCKED` - Worker is blocked, needs human help to proceed
- `STATUS: NEEDS_INFO` - Worker needs more information to proceed
- `STATUS: FAILED` - Worker encountered an error and failed

For `BLOCKED` or `NEEDS_INFO`, include:
- `QUESTION: ...`
- `OPTION 1: ...`
- `OPTION 2: ...`
- `OPTION 3: ...` (optional)

### Blocker Routing Contract

When worker ends with BLOCKED or NEEDS_INFO:
1. Automation comments worker output on the issue
2. Add label `needs-decision`
3. Remove label `ready`
4. Keep label `active` if worker should retry after decision

### Resume Contract After Decision

1. Coordinator comments decision on issue
2. Coordinator applies `ready` label again
3. Worker continues on its issue branch and updates/opens a PR to `development`

### Execution Modes

- **Hosted workers**: Enabled when repository variable configured (GitHub Actions workflow dispatch)
- **Local fallback**: Use local worker hooks:
  - `.agent-automation/hooks/local-worker-start.sh <issue-number>`
  - `.agent-automation/hooks/local-worker-finish.sh <issue-number> <status> [message-file]`
- **Parallel local**: Use tmux for multiple workers:
  - `.agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number>...`

### Stuck Worker Detection

- Workers with `active` label but no activity for >1 hour are considered stuck
- Self-healing automation can restart stuck workers by cycling:
  1. Remove `active`, add `ready`
  2. Worker re-picks up issue automatically
- Max 3 restart attempts before marking `agent-failed`
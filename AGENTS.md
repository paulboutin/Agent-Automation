# Agent Automation Factory

This repo provides an agentic automation framework for coordinating AI workers to implement GitHub issues.

## Quick Start

1. **Create an issue** using `.github/ISSUE_TEMPLATE/agent-task.yml`
2. **Add `ready` label** to trigger worker dispatch
3. **Worker picks up issue**, creates branch, implements, opens PR
4. **PR validates** automatically, human reviews and merges

## Grouped Issues: Use Feature Branches

When multiple issues are related/dependent, **use feature branches** to group them:

1. **Create feature branch** first from development:
   ```bash
   git checkout development
   git checkout -b feature/<name>
   git push origin feature/<name>
   ```
2. Set `base_branch: "feature/<name>"` in each related issue
3. Workers PR to the feature branch (not directly to development)
4. Single PR from feature branch → development after all pass

This avoids the problem of merging 6 individual PRs when they should be one.

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

## 17) Feature Branch Workflow

For multi-task features, use the feature branch workflow:

1. **Create feature branch** from development:
   ```bash
   git checkout development
   git checkout -b feature/<name>
   git push origin feature/<name>
   ```

2. **Create issues** targeting the feature branch:
   - Set `base_branch: "feature/<name>"` in issue body
   - All tasks in the feature should PR to this branch

3. **Parallel task execution**:
   - Worker branches: `agent/issue-<num>-<lane>`
   - PR to: `feature/<name>`

4. **Feature QA**:
   - Create dedicated QA issue for the feature branch
   - Run comprehensive validation before merging

5. **Merge to development**:
   - PR from `feature/<name>` -> `development`
   - Run validation, human review

6. **Promote to main**:
   - Normal development -> main promotion

Example:
- `feature/worker-dashboard` created for Agent Dashboard UI
- Issues #16-#20 target `feature/worker-dashboard`
- Issue #21 runs QA on the feature branch
- PR to development after all pass

## 18) QA Workflow

### Feature Branch QA Flow

When a multi-task feature is ready for QA:

1. **Create QA issue** using `.github/ISSUE_TEMPLATE/agent-task.yml`
2. Set `base_branch: "feature/<name>"` in issue body
3. Apply lane label `agent:qa`
4. Apply `ready` label to dispatch

The QA issue should target the feature branch and include:
- Reference to all implemented issues in the feature
- Specific validation requirements
- Links to any testing artifacts

### QA Review Process

QA worker follows `.agent-automation/packs/qa/prompt.md`:

1. **Read implementation** - Review all PRs for the feature
2. **Validate outcome** - Run `./scripts/validate.sh` and feature-specific tests
3. **Capture evidence** - Record commands, environments, results per checklist
4. **Report findings** - Document pass/fail with evidence

### Issue States and Labels

| State | Labels | Action |
|-------|--------|--------|
| Ready for QA | `agent:qa`, `ready` | QA worker picks up |
| QA in Progress | `agent:qa`, `active` | Worker actively testing |
| QA Passed | `agent:qa`, `done` | Feature ready for merge |
| QA Failed | `agent:qa`, `ready` | Return to implementer |

### Self-Healing for Conflicts/Failures

QA worker handles common issues:

**Merge Conflicts:**
1. Fetch latest from feature branch
2. Rebase worker branch onto feature
3. Resolve conflicts
4. Push updated PR
5. Re-run validation

**Validation Failures:**
1. Capture failure output
2. Identify root cause
3. If implementation bug: mark QA failed, tag implementer
4. If test infrastructure: fix and retry
5. Document resolution in issue

**Self-Healing Rules:**
- Max 2 self-healing attempts per issue
- After 2 failures: mark `needs-decision` with question
- Document all repair attempts in issue comments

### Feature Complete → Merge to Development

After QA passes:

1. **Create merge PR** from `feature/<name>` to `development`
2. **Run validation** on merge PR (`./scripts/validate.sh`)
3. **Human review** - Final review of changes
4. **Merge** - Squash and merge to development
5. **Cleanup** - Delete feature branch (optional)

```
QA passes on feature/worker-dashboard
    ↓
Create PR: feature/worker-dashboard → development
    ↓
Run ./scripts/validate.sh
    ↓
Human review and merge
    ↓
Delete feature/worker-dashboard (optional)
```

### QA Evidence Requirements

Per `.agent-automation/packs/qa/checklist.md`:

- Record exact commands run
- Capture environment details (OS, versions)
- Document pass/fail with output
- Identify any proof gaps needing trusted machine validation
- Route gaps as follow-up work, don't hide them

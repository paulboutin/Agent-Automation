# Operations Guide

## Core Commands

From the upstream repo:

```bash
./scripts/validate.sh
./scripts/smoke.sh
```

From a consumer repo:

```bash
./tools/agent-factory/scripts/render.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/validate.sh --repo-root . --profile ./agent-factory.profile.json
./tools/agent-factory/scripts/smoke.sh --repo-root . --profile ./agent-factory.profile.json
```

## Local Worker Commands

Launch one or more local workers:

```bash
./.agent-automation/hooks/local-worker-launch-tmux.sh --run-agent <issue-number> [issue-number...]
```

Dry-run worker launch:

```bash
./.agent-automation/hooks/local-worker-launch-tmux.sh --dry-run <issue-number>
```

Run a prepared worker manually:

```bash
./.agent-automation/hooks/local-worker-run-and-route.sh --issue <n> --branch <branch> --prompt <file> --host <host>
```

Finish a worker manually:

```bash
./.agent-automation/hooks/local-worker-finish.sh <issue-number> DONE|BLOCKED|NEEDS_INFO|FAILED [message-file]
```

## QA Commands

Launch operator-proof sessions:

```bash
./.agent-automation/hooks/local-qa-proof-launch-tmux.sh <issue-number>
```

Run one operator-proof session:

```bash
./.agent-automation/hooks/local-qa-proof-run.sh --issue <issue-number>
```

## Queue / Merge Commands

Inspect launch candidates:

```bash
./.agent-automation/hooks/merge-daemon-launch-next.sh --json
```

Attempt launch of queued work:

```bash
./.agent-automation/hooks/merge-daemon-launch-next.sh --json --launch
```

Inspect queue status:

```bash
./.agent-automation/hooks/merge-daemon-status.sh
```

Inspect open worker PR merge conflicts:

```bash
gh pr list --state open --label "merge-conflict"
```

## Relay Commands

Process queued relay payloads:

```bash
./.agent-automation/hooks/coordinator-relay-poll.sh
```

Handle one relay payload directly:

```bash
./.agent-automation/hooks/coordinator-relay-handle.sh --message-file <path>
```

## Operational Notes

- Hosted automation in v1 is Codex-only.
- Local hooks require the selected host CLI, `gh`, and standard shell tools.
- QA and review packs are methodology packs, not runtime daemons.
- The PR wake workflow labels conflicted PRs with `merge-conflict` and updates the linked worker issue with a resolution comment for worker branches.
- Consumer repos should keep any environment-specific wrappers outside generic core.

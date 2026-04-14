from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WorkerSession:
    """Mock worker session state used by the dashboard."""

    worker_id: str
    issue_number: int
    title: str
    status: str
    lane: str
    branch: str
    host: str
    last_heartbeat: str
    summary: str
    comment_target: str
    current_command: str = ""
    working_directory: str = ""
    log_tail: tuple[str, ...] = ()

    @property
    def status_indicator(self) -> str:
        indicators = {
            "running": "●",
            "stuck": "⬧",
            "blocked": "▲",
            "failed": "■",
            "done": "✓",
            "queued": "○",
        }
        return indicators.get(self.status, "?")


def build_mock_sessions() -> list[WorkerSession]:
    return [
        WorkerSession(
            worker_id="frontend-17",
            issue_number=17,
            title="Build worker dashboard TUI",
            status="running",
            lane="agent:frontend",
            branch="agent/issue-17-frontend",
            host="codex",
            last_heartbeat="15s ago",
            summary="Rendering Textual tabs and wiring mock actions.",
            comment_target="#17",
            current_command="python -m worker_dashboard.ui",
            working_directory="~/.agent-automation/worktrees/issue-17-frontend",
            log_tail=(
                "[12:34:56] Starting worker for issue #17",
                "[12:34:57] Loaded prompt from .agent-automation/prompts/issue-17.md",
                "[12:34:58] Initialized execution environment",
                "[12:35:01] Processing task: Implement dashboard UI",
                "[12:35:02] Reading existing components...",
                "[12:35:05] Analyzing codebase patterns",
                "[12:35:10] Writing new component to ui.py",
            ),
        ),
        WorkerSession(
            worker_id="backend-44",
            issue_number=44,
            title="Detect stuck workers",
            status="blocked",
            lane="agent:backend",
            branch="agent/issue-44-backend",
            host="codex",
            last_heartbeat="5m ago",
            summary="Waiting on stuck worker detection implementation.",
            comment_target="#44",
            current_command="python detect.py --issue 44",
            working_directory="~/.agent-automation/worktrees/issue-44-backend",
            log_tail=(
                "[12:30:00] Starting worker for issue #44",
                "[12:30:01] Checking heartbeat files...",
                "[12:30:02] Found 3 active sessions",
                "[12:30:03] Waiting for worker input...",
            ),
        ),
        WorkerSession(
            worker_id="backend-12",
            issue_number=12,
            title="Implement branch cleanup",
            status="stuck",
            lane="agent:backend",
            branch="agent/issue-12-backend",
            host="claude",
            last_heartbeat="2h 15m ago",
            summary="Worker running >1 hour, may be stuck. Check logs for progress.",
            comment_target="#12",
            current_command="git rebase -i development",
            working_directory="~/.agent-automation/worktrees/issue-12-backend",
            log_tail=(
                "[10:15:00] Starting rebase for issue #12",
                "[10:15:01] Fetching latest from development",
                "[10:15:02] Running rebase...",
            ),
        ),
        WorkerSession(
            worker_id="qa-21",
            issue_number=21,
            title="Feature branch QA pass",
            status="queued",
            lane="agent:qa",
            branch="agent/issue-21-qa",
            host="opencode",
            last_heartbeat="not started",
            summary="Queued behind active worker capacity.",
            comment_target="#21",
            current_command="",
            working_directory="",
            log_tail=(),
        ),
        WorkerSession(
            worker_id="infra-8",
            issue_number=8,
            title="Harden PR validation workflow",
            status="failed",
            lane="agent:infra",
            branch="agent/issue-8-infra",
            host="codex",
            last_heartbeat="8m ago",
            summary="Validation failed after a schema mismatch in generated config.",
            comment_target="#8",
            current_command="./scripts/validate.sh",
            working_directory="~/.agent-automation/worktrees/issue-8-infra",
            log_tail=(
                "[11:45:00] Starting validation for issue #8",
                "[11:45:01] Loading schema from contracts/",
                "[11:45:02] ERROR: Schema validation failed",
                "[11:45:03] Worker terminated with exit code 1",
            ),
        ),
    ]

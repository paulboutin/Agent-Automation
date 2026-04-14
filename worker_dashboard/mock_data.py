from __future__ import annotations

from dataclasses import dataclass, field


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
    current_working_dir: str = ""
    current_command: str = ""
    output_lines: list[str] = field(default_factory=list)
    started_at: str = ""
    runtime: str = ""

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
            current_working_dir="/tmp/worktrees/issue-17",
            current_command="git diff HEAD --stat",
            output_lines=[
                " src/ui/main.py    | 45 +++----",
                " src/ui/list.py  | 12 +--",
                " 2 files changed, 33 insertions, 45 deletions",
            ],
            started_at="2026-04-14T16:45:00Z",
            runtime="15m 23s",
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
            current_working_dir="/tmp/worktrees/issue-44",
            current_command="",
            output_lines=[
                "STATUS: BLOCKED",
                "QUESTION: What is the stuck threshold?",
                "OPTION 1: 1 hour",
                "OPTION 2: 30 minutes",
            ],
            started_at="2026-04-14T14:20:00Z",
            runtime="2h 45m",
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
            current_working_dir="/tmp/worktrees/issue-12",
            current_command="./scripts/cleanup.sh --dry-run",
            output_lines=[
                "[-processing] Found 12 stale branches",
                "[processing] Checking refs...",
                "[processing] Analyzing git history...",
            ],
            started_at="2026-04-14T14:50:00Z",
            runtime="2h 15m",
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
            current_working_dir="",
            current_command="",
            output_lines=[],
            started_at="",
            runtime="",
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
            current_working_dir="/tmp/worktrees/issue-8",
            current_command="python ./scripts/validate.sh",
            output_lines=["./contracts/foo.schema.json: FAILED", "Error: Invalid JSON in schema"],
            started_at="2026-04-14T15:10:00Z",
            runtime="8m 12s",
        ),
    ]

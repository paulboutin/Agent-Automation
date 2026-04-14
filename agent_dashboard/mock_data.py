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

    @property
    def status_indicator(self) -> str:
        indicators = {
            "running": "●",
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
            title="Build agent dashboard TUI",
            status="running",
            lane="agent:frontend",
            branch="agent/issue-17-frontend",
            host="codex",
            last_heartbeat="15s ago",
            summary="Rendering Textual tabs and wiring mock actions.",
            comment_target="#17",
        ),
        WorkerSession(
            worker_id="backend-12",
            issue_number=12,
            title="Implement branch cleanup",
            status="blocked",
            lane="agent:backend",
            branch="agent/issue-12-backend",
            host="claude",
            last_heartbeat="3m ago",
            summary="Waiting on retention policy confirmation for stale branches.",
            comment_target="#12",
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
        ),
    ]

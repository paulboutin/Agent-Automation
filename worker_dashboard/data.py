from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ISO_8601_FORMATS = (
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ISO_8601_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []

    parsed: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            parsed.append(value)
    return parsed


def _extract_prompt_metadata(prompt_file: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if not prompt_file.is_file():
        return metadata

    for line in prompt_file.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip()
        normalized = key.strip().lower().replace(" ", "_")
        if normalized in {
            "execution_host",
            "cost_profile",
            "reasoning_effort",
            "base_branch",
            "worker_branch",
            "automation_scope",
        }:
            metadata[normalized] = value
    return metadata


def _lane_from_branch(branch: str | None) -> str | None:
    if not branch:
        return None
    if branch.startswith("agent/issue-"):
        parts = branch.rsplit("-", 1)
        if len(parts) == 2 and parts[1]:
            return parts[1]
    return None


@dataclass(slots=True)
class WorkerSession:
    issue_number: int | None
    branch: str | None
    status: str
    source: str
    updated_at: datetime | None = None
    lane: str | None = None
    worktree: Path | None = None
    repo_root: Path | None = None
    prompt_file: Path | None = None
    heartbeat_file: Path | None = None
    raw_log_file: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def age_seconds(self) -> int | None:
        if self.updated_at is None:
            return None
        return max(0, int((_utc_now() - self.updated_at).total_seconds()))

    @property
    def is_running(self) -> bool:
        return self.status.lower() == "running"

    @classmethod
    def from_heartbeat(
        cls,
        heartbeat_file: Path,
        *,
        worktree: Path | None = None,
        source: str = "heartbeat",
    ) -> "WorkerSession | None":
        payload = _read_json(heartbeat_file)
        if not isinstance(payload, dict):
            return None

        prompt_file = None
        prompt_match = re.search(r"heartbeat-(\d+)\.json$", heartbeat_file.name)
        if worktree is not None and prompt_match:
            prompt_candidate = worktree / ".agent-automation" / "prompts" / f"issue-{prompt_match.group(1)}.md"
            if prompt_candidate.is_file():
                prompt_file = prompt_candidate

        metadata = _extract_prompt_metadata(prompt_file) if prompt_file else {}
        branch = str(payload.get("branch") or metadata.get("worker_branch") or "").strip() or None
        issue_raw = payload.get("issue")
        try:
            issue_number = int(issue_raw) if issue_raw is not None else None
        except (TypeError, ValueError):
            issue_number = None

        raw_log_file = None
        if worktree is not None and issue_number is not None:
            run_dir = worktree / ".agent-automation" / "runs"
            candidates = sorted(run_dir.glob(f"issue-{issue_number}-*.clean.log"))
            if candidates:
                raw_log_file = candidates[-1]

        return cls(
            issue_number=issue_number,
            branch=branch,
            lane=_lane_from_branch(branch),
            status=str(payload.get("status") or "unknown"),
            source=source,
            updated_at=_parse_timestamp(str(payload.get("timestamp") or "")),
            worktree=worktree,
            repo_root=worktree,
            prompt_file=prompt_file,
            heartbeat_file=heartbeat_file,
            raw_log_file=raw_log_file,
            metadata=metadata,
        )


@dataclass(slots=True)
class QueueStatus:
    queued_issue_numbers: list[int] = field(default_factory=list)
    active_issue_numbers: list[int] = field(default_factory=list)
    blocked_issue_numbers: list[int] = field(default_factory=list)
    relay_inbox_count: int = 0
    handled_events_count: int = 0
    conflict_count: int = 0


@dataclass(slots=True)
class DaemonState:
    state_dir: Path
    heartbeats: list[WorkerSession] = field(default_factory=list)
    queue: QueueStatus = field(default_factory=QueueStatus)
    relay_events: list[dict[str, Any]] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class GitHubSnapshot:
    issues: list[dict[str, Any]] = field(default_factory=list)
    pull_requests: list[dict[str, Any]] = field(default_factory=list)
    workflow_runs: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: datetime | None = None
    available: bool = False
    error: str | None = None


@dataclass(slots=True)
class AggregatedWorkerState:
    sessions: list[WorkerSession]
    daemon: DaemonState
    github: GitHubSnapshot
    refreshed_at: datetime
    cache_age_seconds: int = 0


class GitHubCLI:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def available(self) -> tuple[bool, str | None]:
        if shutil.which("gh") is None:
            return False, "gh CLI not installed"
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            return False, "GH_TOKEN or GITHUB_TOKEN not set"
        return True, None

    def fetch(self) -> GitHubSnapshot:
        ok, reason = self.available()
        if not ok:
            return GitHubSnapshot(fetched_at=_utc_now(), available=False, error=reason)

        try:
            issues = self._run_json(
                [
                    "gh",
                    "issue",
                    "list",
                    "--state",
                    "open",
                    "--limit",
                    "200",
                    "--json",
                    "number,title,labels,assignees,url,updatedAt,createdAt",
                ]
            )
            prs = self._run_json(
                [
                    "gh",
                    "pr",
                    "list",
                    "--state",
                    "open",
                    "--limit",
                    "200",
                    "--json",
                    "number,title,headRefName,baseRefName,url,createdAt,updatedAt,statusCheckRollup",
                ]
            )
            runs = self._run_json(
                [
                    "gh",
                    "run",
                    "list",
                    "--limit",
                    "50",
                    "--json",
                    "databaseId,displayTitle,event,headBranch,status,conclusion,url,createdAt,updatedAt,workflowName",
                ]
            )
        except RuntimeError as exc:
            return GitHubSnapshot(fetched_at=_utc_now(), available=False, error=str(exc))

        return GitHubSnapshot(
            issues=issues if isinstance(issues, list) else [],
            pull_requests=prs if isinstance(prs, list) else [],
            workflow_runs=runs if isinstance(runs, list) else [],
            fetched_at=_utc_now(),
            available=True,
            error=None,
        )

    def _run_json(self, cmd: list[str]) -> Any:
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise RuntimeError(str(exc)) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() or exc.stdout.strip() or "gh command failed"
            raise RuntimeError(stderr) from exc

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("gh returned invalid JSON") from exc


class WorkerDataAggregator:
    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        worktree_roots: list[str | Path] | None = None,
        coordinator_state_dir: str | Path | None = None,
        cache_ttl_seconds: int = 30,
        github_client: GitHubCLI | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.worktree_roots = [
            Path(root).expanduser() for root in (worktree_roots or self._default_worktree_roots())
        ]
        self.coordinator_state_dir = Path(
            coordinator_state_dir or Path.home() / ".agent-automation" / "coordinator"
        ).expanduser()
        self.cache_ttl_seconds = cache_ttl_seconds
        self.github_client = github_client or GitHubCLI(self.repo_root)
        self._cached_state: AggregatedWorkerState | None = None
        self._cached_at_monotonic: float | None = None

    def refresh(self, *, force: bool = False) -> AggregatedWorkerState:
        if not force and self._cached_state is not None and self._cached_at_monotonic is not None:
            age = int(time.monotonic() - self._cached_at_monotonic)
            if age < self.cache_ttl_seconds:
                self._cached_state.cache_age_seconds = age
                return self._cached_state

        sessions = self._discover_sessions()
        daemon = self._collect_daemon_state(sessions)
        github = self.github_client.fetch()
        state = AggregatedWorkerState(
            sessions=sessions,
            daemon=daemon,
            github=github,
            refreshed_at=_utc_now(),
            cache_age_seconds=0,
        )
        self._cached_state = state
        self._cached_at_monotonic = time.monotonic()
        return state

    def _default_worktree_roots(self) -> list[Path]:
        return [
            Path("~/.agent-automation/worktrees").expanduser(),
            Path("/tmp/agent-automation-worktrees"),
        ]

    def _discover_sessions(self) -> list[WorkerSession]:
        sessions: list[WorkerSession] = []
        seen_keys: set[tuple[int | None, str | None, str | None]] = set()
        for worktree in self._discover_worktrees():
            run_dir = worktree / ".agent-automation" / "runs"
            for heartbeat_file in sorted(run_dir.glob("heartbeat-*.json")):
                session = WorkerSession.from_heartbeat(
                    heartbeat_file,
                    worktree=worktree,
                    source="local-worktree",
                )
                if session is None:
                    continue
                key = (session.issue_number, session.branch, str(session.worktree))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                sessions.append(session)
        sessions.sort(
            key=lambda item: (
                item.updated_at or datetime.min.replace(tzinfo=timezone.utc),
                item.issue_number or -1,
            ),
            reverse=True,
        )
        return sessions

    def _discover_worktrees(self) -> list[Path]:
        discovered: list[Path] = []
        for root in self.worktree_roots:
            if not root.is_dir():
                continue
            for candidate in sorted(root.iterdir()):
                if not candidate.is_dir():
                    continue
                if (
                    (candidate / ".git").exists()
                    or (candidate / ".agent-automation" / "prompts").is_dir()
                    or candidate.name.startswith("issue-")
                ):
                    discovered.append(candidate)
        return discovered

    def _collect_daemon_state(self, sessions: list[WorkerSession]) -> DaemonState:
        state_dir = self.coordinator_state_dir
        relay_events = _read_json_lines(state_dir / "logs" / "relay-events.jsonl")
        queue = QueueStatus(
            active_issue_numbers=sorted(
                session.issue_number for session in sessions if session.is_running and session.issue_number
            ),
            queued_issue_numbers=self._read_issue_numbers(state_dir / "queue" / "ready.json"),
            blocked_issue_numbers=self._read_issue_numbers(state_dir / "queue" / "blocked.json"),
            relay_inbox_count=self._count_children(state_dir / "inbox", suffix=".json"),
            handled_events_count=self._count_children(state_dir / "handled", suffix=".json"),
            conflict_count=self._count_children(state_dir / "conflicts", suffix=".md"),
        )
        return DaemonState(
            state_dir=state_dir,
            heartbeats=sessions,
            queue=queue,
            relay_events=relay_events,
            metadata={
                "exists": state_dir.exists(),
                "relay_log_path": str(state_dir / "logs" / "relay-events.jsonl"),
            },
        )

    def _count_children(self, path: Path, *, suffix: str) -> int:
        if not path.is_dir():
            return 0
        return sum(1 for child in path.iterdir() if child.is_file() and child.name.endswith(suffix))

    def _read_issue_numbers(self, path: Path) -> list[int]:
        payload = _read_json(path)
        if isinstance(payload, list):
            return [int(item) for item in payload if isinstance(item, int)]
        if isinstance(payload, dict):
            values = payload.get("issues")
            if isinstance(values, list):
                return [int(item) for item in values if isinstance(item, int)]
        return []

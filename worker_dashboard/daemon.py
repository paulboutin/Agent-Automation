from __future__ import annotations

import atexit
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Any

PID_FILE = Path("/tmp/agent-daemon.pid")
STATE_FILE = Path("/tmp/agent-daemon-state.json")
DEFAULT_POLL_INTERVAL = 30
DEFAULT_STUCK_THRESHOLD = 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


@dataclass
class DaemonSettings:
    auto_restart_stuck: bool = False
    stuck_threshold_minutes: int = DEFAULT_STUCK_THRESHOLD
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL


@dataclass
class DaemonStatus:
    running: bool = False
    pid: int | None = None
    started_at: str | None = None
    last_poll: str | None = None
    settings: DaemonSettings = field(default_factory=DaemonSettings)
    workers: list[dict] = field(default_factory=list)
    queue_counts: dict = field(
        default_factory=lambda: {"active": 0, "blocked": 0, "queued": 0, "done": 0}
    )
    stuck_workers: list[int] = field(default_factory=list)


def load_settings() -> DaemonSettings:
    settings_file = Path("/tmp/agent-daemon-settings.json")
    data = _read_json(settings_file)
    if isinstance(data, dict):
        return DaemonSettings(
            auto_restart_stuck=bool(data.get("auto_restart_stuck", False)),
            stuck_threshold_minutes=int(
                data.get("stuck_threshold_minutes", DEFAULT_STUCK_THRESHOLD)
            ),
            poll_interval_seconds=int(data.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL)),
        )
    return DaemonSettings()


def save_settings(settings: DaemonSettings) -> None:
    settings_file = Path("/tmp/agent-daemon-settings.json")
    _write_json(
        settings_file,
        {
            "auto_restart_stuck": settings.auto_restart_stuck,
            "stuck_threshold_minutes": settings.stuck_threshold_minutes,
            "poll_interval_seconds": settings.poll_interval_seconds,
        },
    )


def get_daemon_status() -> DaemonStatus:
    if not PID_FILE.exists():
        return DaemonStatus(running=False)

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return DaemonStatus(running=False)

    if not _is_process_running(pid):
        PID_FILE.unlink(missing_ok=True)
        return DaemonStatus(running=False)

    state_data = _read_json(STATE_FILE)
    if isinstance(state_data, dict):
        settings = load_settings()
        return DaemonStatus(
            running=True,
            pid=pid,
            started_at=state_data.get("started_at"),
            last_poll=state_data.get("last_poll"),
            settings=settings,
            workers=state_data.get("workers", []),
            queue_counts=state_data.get(
                "queue_counts", {"active": 0, "blocked": 0, "queued": 0, "done": 0}
            ),
            stuck_workers=state_data.get("stuck_workers", []),
        )

    return DaemonStatus(running=True, pid=pid)


def _is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _discover_worktrees() -> list[Path]:
    roots = [
        Path("~/.agent-automation/worktrees").expanduser(),
        Path("/tmp/agent-automation-worktrees"),
    ]
    discovered = []
    for root in roots:
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


def _scan_heartbeats() -> list[dict]:
    workers = []
    for worktree in _discover_worktrees():
        run_dir = worktree / ".agent-automation" / "runs"
        if not run_dir.is_dir():
            continue
        for hb_file in sorted(run_dir.glob("heartbeat-*.json")):
            data = _read_json(hb_file)
            if not isinstance(data, dict):
                continue
            workers.append(
                {
                    "issue": data.get("issue"),
                    "branch": data.get("branch"),
                    "status": data.get("status"),
                    "timestamp": data.get("timestamp"),
                    "worktree": str(worktree),
                }
            )
    return workers


def _calculate_queue_counts(workers: list[dict]) -> dict[str, int]:
    counts = {"active": 0, "blocked": 0, "queued": 0, "done": 0}
    for w in workers:
        status = (w.get("status") or "").lower()
        if status == "running":
            counts["active"] += 1
        elif status == "blocked":
            counts["blocked"] += 1
        elif status == "queued":
            counts["queued"] += 1
        elif status == "done":
            counts["done"] += 1
    return counts


def _detect_stuck_workers(workers: list[dict], threshold_minutes: int) -> list[int]:
    stuck = []
    threshold_seconds = threshold_minutes * 60
    now = time.time()

    for w in workers:
        if (w.get("status") or "").lower() != "running":
            continue
        ts = w.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age = now - dt.timestamp()
            if age >= threshold_seconds:
                issue = w.get("issue")
                if issue:
                    stuck.append(issue)
        except (ValueError, OSError):
            continue
    return stuck


def _restart_worker(issue_number: int) -> bool:
    repo_root = Path(__file__).parent.parent
    try:
        subprocess.run(
            [str(repo_root / ".agent-automation/hooks/local-worker-start.sh"), str(issue_number)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except (subprocess.TimeoutExpired, OSError, subprocess.CalledProcessError):
        return False


def daemon_main() -> None:
    settings = load_settings()

    _write_json(
        STATE_FILE,
        {
            "started_at": _utc_now().isoformat(),
            "last_poll": None,
            "workers": [],
            "queue_counts": {"active": 0, "blocked": 0, "queued": 0, "done": 0},
            "stuck_workers": [],
        },
    )

    stop_event = Event()

    def signal_handler(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    while not stop_event.is_set():
        workers = _scan_heartbeats()
        queue_counts = _calculate_queue_counts(workers)
        stuck = _detect_stuck_workers(workers, settings.stuck_threshold_minutes)

        for issue in stuck:
            if settings.auto_restart_stuck:
                _restart_worker(issue)

        _write_json(
            STATE_FILE,
            {
                "started_at": _utc_now().isoformat(),
                "last_poll": _utc_now().isoformat(),
                "workers": workers,
                "queue_counts": queue_counts,
                "stuck_workers": stuck,
            },
        )

        if settings.auto_restart_stuck:
            settings = load_settings()

        stop_event.wait(settings.poll_interval_seconds)

    if PID_FILE.exists():
        PID_FILE.unlink()


def start_daemon() -> tuple[bool, str]:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if _is_process_running(pid):
                return False, "Daemon already running"
        except (ValueError, OSError):
            pass

    repo_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root)

    try:
        proc = subprocess.Popen(
            [sys.executable, str(__file__)],
            cwd=str(repo_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        PID_FILE.write_text(str(proc.pid))
        return True, f"Daemon started (PID: {proc.pid})"
    except OSError as e:
        return False, str(e)


def stop_daemon() -> tuple[bool, str]:
    if not PID_FILE.exists():
        return False, "Daemon not running"

    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        PID_FILE.unlink(missing_ok=True)
        return False, "Invalid PID file"

    if not _is_process_running(pid):
        PID_FILE.unlink(missing_ok=True)
        return False, "Daemon not running"

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(10):
            time.sleep(0.5)
            if not _is_process_running(pid):
                break
        else:
            os.kill(pid, signal.SIGKILL)

        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
        return True, "Daemon stopped"
    except OSError as e:
        return False, str(e)


if __name__ == "__main__":
    daemon_main()

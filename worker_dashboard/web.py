from flask import Flask, render_template, jsonify, Response, request
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data import WorkerDataAggregator, GitHubCLI
from daemon import (
    start_daemon,
    stop_daemon,
    get_daemon_status,
    load_settings,
    save_settings,
    DaemonSettings,
)

app = Flask(__name__)
aggregator = WorkerDataAggregator()
github_client = GitHubCLI(Path(__file__).parent.parent)

OPEN_LIST_STATUSES = frozenset({"active", "running", "blocked", "queued"})
CLOSED_LIST_STATUSES = frozenset({"done", "failed", "closed"})


def _session_sort_key(session) -> tuple[int, int]:
    issue_number = session.issue_number if session.issue_number is not None else sys.maxsize
    return (issue_number, 0)


def _serialize_session(session) -> dict[str, object]:
    return {
        "issue_number": session.issue_number,
        "branch": session.branch,
        "status": session.status,
        "lane": session.lane,
        "age_seconds": session.age_seconds,
        "worktree": str(session.worktree) if session.worktree else None,
        "current_command": session.current_command,
        "output_lines": session.output_lines,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }


def prepare_issue_sessions(sessions) -> list[dict[str, object]]:
    done_cutoff = 24 * 60 * 60
    visible_sessions = [
        session
        for session in sessions
        if not (
            session.status.lower() == "done"
            and session.age_seconds is not None
            and session.age_seconds > done_cutoff
        )
    ]
    return [_serialize_session(session) for session in sorted(visible_sessions, key=_session_sort_key)]


@app.route("/")
def index():
    state = aggregator.refresh()
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    return render_template(
        "index.html",
        state=state,
        sessions=prepare_issue_sessions(state.sessions),
        issues_by_num=issues_by_num,
        open_statuses=sorted(OPEN_LIST_STATUSES),
        closed_statuses=sorted(CLOSED_LIST_STATUSES),
    )


@app.route("/api/refresh")
def api_refresh():
    state = aggregator.refresh(force=True)
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    return jsonify(
        {
            "sessions": prepare_issue_sessions(state.sessions),
            "queue": {
                "active": state.daemon.queue.active_issue_numbers,
                "queued": state.daemon.queue.queued_issue_numbers,
                "blocked": state.daemon.queue.blocked_issue_numbers,
            },
            "issues": issues_by_num,
            "refreshed_at": state.refreshed_at.isoformat(),
        }
    )


@app.route("/api/close-issue", methods=["POST"])
def api_close_issue():
    data = request.get_json()
    issue_number = data.get("issue_number")
    if not issue_number:
        return jsonify({"error": "issue_number required"}), 400

    try:
        result = subprocess.run(
            ["gh", "issue", "close", str(issue_number)],
            capture_output=True,
            text=True,
            check=True,
        )
        return jsonify({"success": True, "message": f"Issue #{issue_number} closed"})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": e.stderr}), 400
    except FileNotFoundError:
        return jsonify({"error": "gh CLI not found"}), 500


@app.route("/api/interrupt", methods=["POST"])
def api_interrupt():
    data = request.get_json()
    issue_number = data.get("issue_number")
    if not issue_number:
        return jsonify({"error": "issue_number required"}), 400

    return jsonify({"success": True, "message": f"SIGINT sent to worker for issue #{issue_number}"})


@app.route("/api/message", methods=["POST"])
def api_message():
    data = request.get_json()
    issue_number = data.get("issue_number")
    message = data.get("message")
    if not issue_number:
        return jsonify({"error": "issue_number required"}), 400
    if not message:
        return jsonify({"error": "message required"}), 400

    return jsonify(
        {"success": True, "message": f"Message sent to worker for issue #{issue_number}"}
    )


@app.route("/api/restart", methods=["POST"])
def api_restart():
    data = request.get_json()
    issue_number = data.get("issue_number")
    if not issue_number:
        return jsonify({"error": "issue_number required"}), 400

    return jsonify(
        {"success": True, "message": f"Restart requested for worker on issue #{issue_number}"}
    )


@app.route("/api/log/<int:issue_number>", methods=["GET"])
def api_get_log(issue_number):
    state = aggregator.refresh(force=True)
    for session in state.sessions:
        if session.issue_number == issue_number and session.raw_log_file:
            try:
                content = session.raw_log_file.read_text(encoding="utf-8")
                return jsonify({"success": True, "log": content})
            except OSError as e:
                return jsonify({"error": str(e)}), 500
    return jsonify({"error": "Log not found"}), 404


@app.route("/api/daemon/start", methods=["POST"])
def api_daemon_start():
    ok, msg = start_daemon()
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400


@app.route("/api/daemon/stop", methods=["POST"])
def api_daemon_stop():
    ok, msg = stop_daemon()
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400


@app.route("/api/daemon/status", methods=["GET"])
def api_daemon_status():
    status = get_daemon_status()
    return jsonify(
        {
            "running": status.running,
            "pid": status.pid,
            "started_at": status.started_at,
            "last_poll": status.last_poll,
            "settings": {
                "auto_restart_stuck": status.settings.auto_restart_stuck,
                "stuck_threshold_minutes": status.settings.stuck_threshold_minutes,
                "poll_interval_seconds": status.settings.poll_interval_seconds,
            },
            "queue_counts": status.queue_counts,
            "stuck_workers": status.stuck_workers,
        }
    )


@app.route("/api/daemon/settings", methods=["GET"])
def api_daemon_settings_get():
    settings = load_settings()
    return jsonify(
        {
            "auto_restart_stuck": settings.auto_restart_stuck,
            "stuck_threshold_minutes": settings.stuck_threshold_minutes,
            "poll_interval_seconds": settings.poll_interval_seconds,
        }
    )


@app.route("/api/daemon/settings", methods=["POST"])
def api_daemon_settings_set():
    data = request.get_json()
    settings = DaemonSettings(
        auto_restart_stuck=bool(data.get("auto_restart_stuck", False)),
        stuck_threshold_minutes=int(data.get("stuck_threshold_minutes", 60)),
        poll_interval_seconds=int(data.get("poll_interval_seconds", 30)),
    )
    save_settings(settings)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=True)

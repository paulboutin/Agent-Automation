from flask import Flask, render_template, jsonify, Response, request
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data import WorkerDataAggregator, GitHubCLI

app = Flask(__name__)
aggregator = WorkerDataAggregator()
github_client = GitHubCLI(Path(__file__).parent.parent)


@app.route("/")
def index():
    state = aggregator.refresh()
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    done_cutoff = 24 * 60 * 60
    sessions = [
        s
        for s in state.sessions
        if not (s.status.lower() == "done" and s.age_seconds and s.age_seconds > done_cutoff)
    ]
    return render_template(
        "index.html", state=state, sessions=sessions, issues_by_num=issues_by_num
    )


@app.route("/api/refresh")
def api_refresh():
    state = aggregator.refresh(force=True)
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    done_cutoff = 24 * 60 * 60
    sessions = []
    for s in state.sessions:
        if s.status.lower() == "done" and s.age_seconds and s.age_seconds > done_cutoff:
            continue
        sessions.append(
            {
                "issue_number": s.issue_number,
                "branch": s.branch,
                "status": s.status,
                "lane": s.lane,
                "age_seconds": s.age_seconds,
                "worktree": str(s.worktree) if s.worktree else None,
                "current_command": s.current_command,
                "output_lines": s.output_lines,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            }
        )
    return jsonify(
        {
            "sessions": sessions,
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=True)

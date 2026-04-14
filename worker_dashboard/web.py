from flask import Flask, render_template, jsonify, Response, request
import json
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data import WorkerDataAggregator

app = Flask(__name__)
aggregator = WorkerDataAggregator()


@app.route("/")
def index():
    state = aggregator.refresh()
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    return render_template("index.html", state=state, issues_by_num=issues_by_num)


@app.route("/api/refresh")
def api_refresh():
    state = aggregator.refresh(force=True)
    issues_by_num = {issue["number"]: issue for issue in state.github.issues}
    return jsonify(
        {
            "sessions": [
                {
                    "issue_number": s.issue_number,
                    "branch": s.branch,
                    "status": s.status,
                    "lane": s.lane,
                    "age_seconds": s.age_seconds,
                }
                for s in state.sessions
            ],
            "queue": {
                "active": state.daemon.queue.active_issue_numbers,
                "queued": state.daemon.queue.queued_issue_numbers,
                "blocked": state.daemon.queue.blocked_issue_numbers,
            },
            "issues": issues_by_num,
            "refreshed_at": state.refreshed_at.isoformat(),
        }
    )


@app.route("/api/worker/<int:issue_number>")
def api_worker(issue_number):
    state = aggregator.refresh()
    session = next((s for s in state.sessions if s.issue_number == issue_number), None)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    current_command = ""
    working_directory = ""
    if session.worktree:
        current_command = session.metadata.get("current_command", "")
        working_directory = str(session.worktree)

    return jsonify(
        {
            "issue_number": session.issue_number,
            "branch": session.branch,
            "status": session.status,
            "lane": session.lane,
            "worktree": str(session.worktree) if session.worktree else None,
            "current_command": current_command,
            "working_directory": working_directory,
            "log_tail": session.get_log_tail(20),
        }
    )


@app.route("/api/worker/<int:issue_number>/interrupt", methods=["POST"])
def api_interrupt(issue_number):
    state = aggregator.refresh()
    session = next((s for s in state.sessions if s.issue_number == issue_number), None)
    if not session or not session.worktree:
        return jsonify({"error": "Session not found"}), 404

    pid_file = session.worktree / ".agent-automation" / "runs" / f"issue-{issue_number}.pid"
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text().strip())
            subprocess.run(["kill", "-SIGINT", str(pid)], check=False)
            return jsonify({"success": True, "message": f"Sent SIGINT to {pid}"})
        except (ValueError, OSError) as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "PID file not found"}), 404


@app.route("/api/worker/<int:issue_number>/restart", methods=["POST"])
def api_restart(issue_number):
    return jsonify(
        {
            "error": "Restart not implemented - use local worker hooks",
            "hint": "Use .agent-automation/hooks/local-worker-start.sh",
        }
    ), 501


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=True)

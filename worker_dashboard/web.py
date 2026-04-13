from flask import Flask, render_template, jsonify, Response
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data import WorkerDataAggregator

app = Flask(__name__)
aggregator = WorkerDataAggregator()


@app.route("/")
def index():
    state = aggregator.refresh()
    return render_template("index.html", state=state)


@app.route("/api/refresh")
def api_refresh():
    state = aggregator.refresh(force=True)
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
            "refreshed_at": state.refreshed_at.isoformat(),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8765, debug=True)

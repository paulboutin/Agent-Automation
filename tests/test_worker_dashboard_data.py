from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from worker_dashboard.data import GitHubCLI, GitHubSnapshot, WorkerDataAggregator


class StaticGitHubClient:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self) -> GitHubSnapshot:
        self.calls += 1
        return GitHubSnapshot(available=False, error="disabled")


class WorkerDashboardDataTests(unittest.TestCase):
    def test_refresh_discovers_local_sessions_and_daemon_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree_root = root / "worktrees"
            worktree = worktree_root / "issue-16-backend"
            run_dir = worktree / ".agent-automation" / "runs"
            prompt_dir = worktree / ".agent-automation" / "prompts"
            state_dir = root / "coordinator"

            run_dir.mkdir(parents=True)
            prompt_dir.mkdir(parents=True)
            (state_dir / "inbox").mkdir(parents=True)
            (state_dir / "handled").mkdir(parents=True)
            (state_dir / "conflicts").mkdir(parents=True)
            (state_dir / "logs").mkdir(parents=True)
            (state_dir / "queue").mkdir(parents=True)

            (prompt_dir / "issue-16.md").write_text(
                "\n".join(
                    [
                        "Execution host: OpenAI Codex CLI (codex)",
                        "Cost profile: standard",
                        "Reasoning effort: medium",
                        "Base branch: development",
                        "Worker branch: agent/issue-16-backend",
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "heartbeat-16.json").write_text(
                json.dumps(
                    {
                        "branch": "agent/issue-16-backend",
                        "issue": 16,
                        "timestamp": "2026-04-13T18:00:00Z",
                        "status": "running",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "issue-16-20260413-180000.clean.log").write_text(
                "STATUS: DONE\n", encoding="utf-8"
            )
            (state_dir / "inbox" / "payload.json").write_text("{}", encoding="utf-8")
            (state_dir / "handled" / "event.json").write_text("{}", encoding="utf-8")
            (state_dir / "conflicts" / "pr-12.md").write_text("# conflict\n", encoding="utf-8")
            (state_dir / "logs" / "relay-events.jsonl").write_text(
                '{"dedupeKey":"abc"}\n', encoding="utf-8"
            )
            (state_dir / "queue" / "ready.json").write_text("[16, 17]", encoding="utf-8")
            (state_dir / "queue" / "blocked.json").write_text('{"issues":[18]}', encoding="utf-8")

            github = StaticGitHubClient()
            aggregator = WorkerDataAggregator(
                repo_root=root,
                worktree_roots=[worktree_root],
                coordinator_state_dir=state_dir,
                cache_ttl_seconds=30,
                github_client=github,
            )

            snapshot = aggregator.refresh(force=True)

            self.assertEqual(github.calls, 1)
            self.assertEqual(len(snapshot.sessions), 1)
            self.assertEqual(snapshot.sessions[0].issue_number, 16)
            self.assertEqual(snapshot.sessions[0].lane, "backend")
            self.assertEqual(snapshot.daemon.queue.active_issue_numbers, [16])
            self.assertEqual(snapshot.daemon.queue.queued_issue_numbers, [16, 17])
            self.assertEqual(snapshot.daemon.queue.blocked_issue_numbers, [18])
            self.assertEqual(snapshot.daemon.queue.relay_inbox_count, 1)
            self.assertEqual(snapshot.daemon.queue.handled_events_count, 1)
            self.assertEqual(snapshot.daemon.queue.conflict_count, 1)
            self.assertEqual(len(snapshot.daemon.relay_events), 1)

    def test_refresh_uses_cache_until_forced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            github = StaticGitHubClient()
            aggregator = WorkerDataAggregator(
                repo_root=root,
                worktree_roots=[root / "missing"],
                coordinator_state_dir=root / "coordinator",
                cache_ttl_seconds=60,
                github_client=github,
            )

            first = aggregator.refresh(force=True)
            second = aggregator.refresh()
            third = aggregator.refresh(force=True)

            self.assertIs(first, second)
            self.assertIsNot(first, third)
            self.assertEqual(github.calls, 2)

    def test_github_cli_reports_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cli = GitHubCLI(Path(tmp))
            with patch("worker_dashboard.data.shutil.which", return_value="/usr/bin/gh"):
                with patch.dict("os.environ", {}, clear=True):
                    snapshot = cli.fetch()

            self.assertFalse(snapshot.available)
            self.assertIn("GH_TOKEN", snapshot.error or "")

    def test_worker_session_is_stuck_true_when_running_over_1_hour(self) -> None:
        from worker_dashboard.data import WorkerSession

        now = datetime.now(timezone.utc)
        one_hour_ago = now.replace(hour=now.hour - 1)

        session = WorkerSession(
            issue_number=42,
            branch="agent/issue-42-backend",
            status="running",
            source="test",
            updated_at=one_hour_ago,
        )
        self.assertTrue(session.is_stuck)

    def test_worker_session_is_stuck_false_when_running_under_1_hour(self) -> None:
        from worker_dashboard.data import WorkerSession

        now = datetime.now(timezone.utc)
        ten_minutes_ago = now.replace(minute=now.minute - 10)

        session = WorkerSession(
            issue_number=42,
            branch="agent/issue-42-backend",
            status="running",
            source="test",
            updated_at=ten_minutes_ago,
        )
        self.assertFalse(session.is_stuck)

    def test_worker_session_is_stuck_false_when_not_running(self) -> None:
        from worker_dashboard.data import WorkerSession

        now = datetime.now(timezone.utc)
        two_hours_ago = now.replace(hour=now.hour - 2)

        session = WorkerSession(
            issue_number=42,
            branch="agent/issue-42-backend",
            status="done",
            source="test",
            updated_at=two_hours_ago,
        )
        self.assertFalse(session.is_stuck)


if __name__ == "__main__":
    unittest.main()

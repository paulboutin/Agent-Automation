import unittest

from worker_dashboard.mock_data import build_mock_sessions
from worker_dashboard.ui import WorkerDashboardApp


class WorkerDashboardTests(unittest.TestCase):
    def test_mock_sessions_cover_multiple_statuses(self) -> None:
        sessions = build_mock_sessions()

        self.assertGreaterEqual(len(sessions), 4)
        self.assertEqual(sessions[0].issue_number, 17)
        self.assertIn("running", {session.status for session in sessions})
        self.assertIn("stuck", {session.status for session in sessions})
        self.assertIn("blocked", {session.status for session in sessions})

    def test_session_is_open_property(self) -> None:
        sessions = build_mock_sessions()
        open_sessions = [s for s in sessions if s.is_open]
        closed_sessions = [s for s in sessions if not s.is_open]

        self.assertGreater(len(open_sessions), 0)
        self.assertGreater(len(closed_sessions), 0)
        for session in open_sessions:
            self.assertNotIn(session.status, ("done", "closed"))
        for session in closed_sessions:
            self.assertIn(session.status, ("done", "failed", "closed"))

    def test_dashboard_app_is_importable(self) -> None:
        app = WorkerDashboardApp()

        self.assertTrue(hasattr(app, "sessions"))
        self.assertGreaterEqual(len(app.sessions), 1)


if __name__ == "__main__":
    unittest.main()

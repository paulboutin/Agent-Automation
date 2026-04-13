import unittest

from worker_dashboard.mock_data import build_mock_sessions
from worker_dashboard.ui import WorkerDashboardApp


class WorkerDashboardTests(unittest.TestCase):
    def test_mock_sessions_cover_multiple_statuses(self) -> None:
        sessions = build_mock_sessions()

        self.assertGreaterEqual(len(sessions), 4)
        self.assertEqual(sessions[0].issue_number, 17)
        self.assertIn("running", {session.status for session in sessions})
        self.assertIn("blocked", {session.status for session in sessions})

    def test_dashboard_app_is_importable(self) -> None:
        app = WorkerDashboardApp()

        self.assertTrue(hasattr(app, "sessions"))
        self.assertGreaterEqual(len(app.sessions), 1)


if __name__ == "__main__":
    unittest.main()

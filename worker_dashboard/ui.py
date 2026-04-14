from __future__ import annotations

from dataclasses import asdict
from typing import ClassVar

from worker_dashboard.mock_data import WorkerSession, build_mock_sessions

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widgets import (
        Button,
        DataTable,
        Footer,
        Header,
        Input,
        Static,
        TabbedContent,
        TabPane,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised indirectly in this environment
    TEXTUAL_AVAILABLE = False

    class WorkerDashboardApp:  # type: ignore[no-redef]
        """Fallback entrypoint for environments without Textual installed."""

        textual_available: ClassVar[bool] = False

        def __init__(self, *args, **kwargs) -> None:
            self.sessions = build_mock_sessions()

        def run(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError(
                "textual is required to run WorkerDashboardApp. "
                "Install project dependencies to launch the dashboard."
            )

else:
    TEXTUAL_AVAILABLE = True

    class WorkerDashboardApp(App[None]):
        """Terminal dashboard for monitoring worker sessions."""

        CSS = """
        Screen {
            layout: vertical;
        }

        #workspace {
            height: 1fr;
        }

        #workers-panel {
            width: 2fr;
            min-width: 48;
        }

        #detail-panel {
            width: 3fr;
            padding: 1 2;
            border-left: solid $primary;
        }

        #detail-title {
            text-style: bold;
            margin-bottom: 1;
        }

        #detail-body {
            height: 1fr;
        }

        #comment-input {
            margin: 1 0;
        }

        #action-row {
            height: auto;
            margin-top: 1;
        }

        Button {
            margin-right: 1;
        }

        .tab-copy {
            padding: 1 2;
        }

        .group-header {
            text-style: bold;
            padding: 0 1;
        }
        """

        BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

        selected_worker_id = reactive("")
        selected_status_filter = reactive("open")

        def __init__(self) -> None:
            super().__init__()
            self.sessions = build_mock_sessions()

        def filter_sessions(
            self, sessions: list[WorkerSession], status_filter: str
        ) -> list[WorkerSession]:
            if status_filter == "open":
                filtered = [s for s in sessions if s.is_open]
            else:
                filtered = [s for s in sessions if not s.is_open]
            return sorted(filtered, key=lambda s: s.issue_number)

        def group_by_feature(self, sessions: list[WorkerSession]) -> dict[str, list[WorkerSession]]:
            groups: dict[str, list[WorkerSession]] = {}
            for session in sessions:
                key = session.feature_branch if session.feature_branch else "no feature"
                groups.setdefault(key, []).append(session)
            return groups

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with TabbedContent(initial="open"):
                with TabPane("Open", id="open"):
                    with Horizontal(id="workspace"):
                        with Vertical(id="workers-panel"):
                            table = DataTable(
                                id="worker-table", zebra_stripes=True, cursor_type="row"
                            )
                            table.add_columns("Status", "Worker", "Issue", "Lane", "Heartbeat")
                            yield table
                        with Vertical(id="detail-panel"):
                            yield Static("Worker Details", id="detail-title")
                            yield Static("", id="detail-body")
                            yield Input(
                                placeholder="Draft issue comment or operator note",
                                id="comment-input",
                            )
                            with Horizontal(id="action-row"):
                                yield Button("Kill", id="kill", variant="error")
                                yield Button("Restart", id="restart", variant="warning")
                                yield Button("Comment", id="comment", variant="primary")
                                yield Button("Open Logs", id="logs")
                with TabPane("Closed", id="closed"):
                    with Horizontal(id="workspace"):
                        with Vertical(id="workers-panel"):
                            closed_table = DataTable(
                                id="closed-table", zebra_stripes=True, cursor_type="row"
                            )
                            closed_table.add_columns(
                                "Status", "Worker", "Issue", "Lane", "Heartbeat"
                            )
                            yield closed_table
                        with Vertical(id="detail-panel"):
                            yield Static("Worker Details", id="closed-detail-title")
                            yield Static("", id="closed-detail-body")
                with TabPane("Daemon", id="daemon"):
                    yield Static(
                        "Merge daemon is healthy.\n\nQueued issues: 3\nActive workers: 4\nRestarts in last hour: 1",
                        classes="tab-copy",
                    )
                with TabPane("Settings", id="settings"):
                    yield Static(
                        "Host: codex\nBase branch: development\nMock mode: enabled\nNotifications: on",
                        classes="tab-copy",
                    )
            yield Footer()

        def on_mount(self) -> None:
            self._load_workers()

        def action_refresh(self) -> None:
            self.sessions = build_mock_sessions()
            self._load_workers()
            self.notify("Worker list refreshed from mock data.")

        def _load_workers(self) -> None:
            all_sessions = build_mock_sessions()
            open_sessions = self.filter_sessions(all_sessions, "open")
            closed_sessions = self.filter_sessions(all_sessions, "closed")

            open_table = self.query_one("#worker-table", DataTable)
            open_table.clear(columns=False)
            for session in open_sessions:
                open_table.add_row(
                    f"{session.status_indicator} {session.status}",
                    session.worker_id,
                    f"#{session.issue_number}",
                    session.lane,
                    session.last_heartbeat,
                    key=session.worker_id,
                )

            closed_table = self.query_one("#closed-table", DataTable)
            closed_table.clear(columns=False)
            for session in closed_sessions:
                closed_table.add_row(
                    f"{session.status_indicator} {session.status}",
                    session.worker_id,
                    f"#{session.issue_number}",
                    session.lane,
                    session.last_heartbeat,
                    key=session.worker_id,
                )

            if open_sessions:
                open_table.move_cursor(row=0)
                self.selected_worker_id = open_sessions[0].worker_id
                self.selected_status_filter = "open"
                self._render_selected_session()

        def _render_selected_session(self) -> None:
            if self.selected_status_filter == "open":
                detail = self.query_one("#detail-body", Static)
            else:
                detail = self.query_one("#closed-detail-body", Static)

            session = self.selected_session
            if session is None:
                detail.update("No worker selected.")
                return

            session_fields = asdict(session)
            body = "\n".join(
                [
                    f"Worker: {session_fields['worker_id']}",
                    f"Issue: #{session_fields['issue_number']} - {session_fields['title']}",
                    f"Status: {session.status_indicator} {session_fields['status']}",
                    f"Lane: {session_fields['lane']}",
                    f"Branch: {session_fields['branch']}",
                    f"Host: {session_fields['host']}",
                    f"Heartbeat: {session_fields['last_heartbeat']}",
                    "",
                    "Summary:",
                    session_fields["summary"],
                    "",
                    f"Comment target: {session_fields['comment_target']}",
                ]
            )
            detail.update(body)

        def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
            if event.row_key is None:
                return
            self.selected_worker_id = str(event.row_key.value)
            self._render_selected_session()

        def on_tabbed_content_tab_changed(self, event: TabbedContent.TabChanged) -> None:
            if event.tab.id == "open":
                self.selected_status_filter = "open"
            elif event.tab.id == "closed":
                self.selected_status_filter = "closed"

        def on_button_pressed(self, event: Button.Pressed) -> None:
            if not self.selected_session:
                self.notify("Select a worker session first.", severity="warning")
                return

            handlers = {
                "kill": self._kill_worker,
                "restart": self._restart_worker,
                "comment": self._comment_on_worker,
                "logs": self._open_logs,
            }
            handler = handlers.get(event.button.id or "")
            if handler:
                handler()

        @property
        def selected_session(self) -> WorkerSession | None:
            all_sessions = build_mock_sessions()
            for session in all_sessions:
                if session.worker_id == self.selected_worker_id:
                    return session
            return None

        def _kill_worker(self) -> None:
            session = self.selected_session
            assert session is not None
            session.status = "failed"
            session.summary = "Operator requested termination from dashboard."
            self._load_workers()
            self.notify(f"Kill requested for {session.worker_id}.", severity="warning")

        def _restart_worker(self) -> None:
            session = self.selected_session
            assert session is not None
            session.status = "running"
            session.last_heartbeat = "just now"
            session.summary = "Worker restarted from dashboard action handler."
            self._load_workers()
            self.notify(f"Restart requested for {session.worker_id}.")

        def _comment_on_worker(self) -> None:
            session = self.selected_session
            assert session is not None
            comment_input = self.query_one("#comment-input", Input)
            comment = comment_input.value.strip() or "No comment text entered."
            session.summary = f"Latest operator comment: {comment}"
            self._render_selected_session()
            comment_input.value = ""
            self.notify(f"Comment staged for {session.comment_target}.")

        def _open_logs(self) -> None:
            session = self.selected_session
            assert session is not None
            self.notify(f"Would open logs for {session.worker_id} on {session.host}.")

from __future__ import annotations

from dataclasses import asdict
from typing import ClassVar

from agent_dashboard.mock_data import WorkerSession, build_mock_sessions

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

    class AgentDashboardApp:  # type: ignore[no-redef]
        """Fallback entrypoint for environments without Textual installed."""

        textual_available: ClassVar[bool] = False

        def __init__(self, *args, **kwargs) -> None:
            self.sessions = build_mock_sessions()

        def run(self, *args, **kwargs) -> None:
            raise ModuleNotFoundError(
                "textual is required to run AgentDashboardApp. "
                "Install project dependencies to launch the dashboard."
            )

else:
    TEXTUAL_AVAILABLE = True

    class AgentDashboardApp(App[None]):
        """Terminal dashboard for monitoring agent sessions."""

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
        """

        BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

        selected_worker_id = reactive("")

        def __init__(self) -> None:
            super().__init__()
            self.sessions = build_mock_sessions()

        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with TabbedContent(initial="workers"):
                with TabPane("Workers", id="workers"):
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
            table = self.query_one("#worker-table", DataTable)
            table.clear(columns=False)
            for session in self.sessions:
                table.add_row(
                    f"{session.status_indicator} {session.status}",
                    session.worker_id,
                    f"#{session.issue_number}",
                    session.lane,
                    session.last_heartbeat,
                    key=session.worker_id,
                )

            if self.sessions:
                table.move_cursor(row=0)
                self.selected_worker_id = self.sessions[0].worker_id
                self._render_selected_session()

        def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
            if event.row_key is None:
                return
            self.selected_worker_id = str(event.row_key.value)
            self._render_selected_session()

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
            return next(
                (
                    session
                    for session in self.sessions
                    if session.worker_id == self.selected_worker_id
                ),
                None,
            )

        def _render_selected_session(self) -> None:
            detail = self.query_one("#detail-body", Static)
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

#!/usr/bin/env python
"""Worker dashboard runner."""

import asyncio
from worker_dashboard import WorkerDashboardApp

if __name__ == "__main__":
    app = WorkerDashboardApp()
    asyncio.run(app.run_async())

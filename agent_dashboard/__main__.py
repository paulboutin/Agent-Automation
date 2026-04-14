#!/usr/bin/env python
"""Agent dashboard runner."""

import asyncio
from agent_dashboard import AgentDashboardApp

if __name__ == "__main__":
    app = AgentDashboardApp()
    asyncio.run(app.run_async())

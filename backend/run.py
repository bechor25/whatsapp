"""
Windows-safe uvicorn launcher.
Sets ProactorEventLoop policy BEFORE uvicorn creates its event loop.
Required for Playwright (subprocess-based) to work on Windows.

NOTE: reload=False is intentional — with reload=True uvicorn spawns a child
process that loses the ProactorEventLoop policy, breaking Playwright.
Restart this script manually after code changes.
"""
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

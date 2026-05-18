"""
SOTA Browser MCP Server — Download Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_download_file",
        "description": "Trigger a file download by clicking a selector or navigating to a URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "trigger_selector": {
                    "type": "string",
                    "description": "CSS selector of the download trigger button/link",
                },
                "url": {
                    "type": "string",
                    "description": "Direct download URL (alternative to trigger_selector)",
                },
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_wait_for_download",
        "description": "Wait for a pending download to complete and save to disk",
        "inputSchema": {
            "type": "object",
            "properties": {
                "download_id": {"type": "string", "description": "Download ID from browser_download_file"},
                "path": {
                    "type": "string",
                    "description": "Save path (defaults to /tmp/<suggested_filename>)",
                },
            },
            "required": ["download_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_download_file(**kwargs):
        return await manager.download_file(
            kwargs["tab_id"],
            kwargs.get("trigger_selector"),
            kwargs.get("url"),
        )
    handlers["browser_download_file"] = browser_download_file

    async def browser_wait_for_download(**kwargs):
        return await manager.wait_for_download(kwargs["download_id"], kwargs.get("path"))
    handlers["browser_wait_for_download"] = browser_wait_for_download

    return handlers

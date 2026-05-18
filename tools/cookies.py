"""
SOTA Browser MCP Server — Cookie Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_import_cookies",
        "description": "Import cookies into a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "cookies": {"type": "array"},
            },
            "required": ["session_id", "cookies"],
        },
    },
    {
        "name": "browser_export_cookies",
        "description": "Export all cookies from a session context",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
    {
        "name": "browser_clear_cookies",
        "description": "Clear all cookies from a session context",
        "inputSchema": {
            "type": "object",
            "properties": {"session_id": {"type": "string"}},
            "required": ["session_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_import_cookies(**kwargs):
        return await manager.import_cookies(kwargs["session_id"], kwargs["cookies"])
    handlers["browser_import_cookies"] = browser_import_cookies

    async def browser_export_cookies(**kwargs):
        return await manager.export_cookies(kwargs["session_id"])
    handlers["browser_export_cookies"] = browser_export_cookies

    async def browser_clear_cookies(**kwargs):
        return await manager.clear_cookies(kwargs["session_id"])
    handlers["browser_clear_cookies"] = browser_clear_cookies

    return handlers

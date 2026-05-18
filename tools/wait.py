"""
SOTA Browser MCP Server — Wait / Polling Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_wait",
        "description": "Explicit wait (sleep)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "seconds": {"type": "number"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_wait_for_selector",
        "description": "Wait for an element matching selector to appear",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string", "description": "CSS selector to wait for"},
                "state": {
                    "type": "string",
                    "enum": ["attached", "detached", "visible", "hidden"],
                    "description": "Element state to wait for (default: visible)",
                },
                "timeout": {"type": "number", "description": "Timeout in ms (default: 30000)"},
            },
            "required": ["tab_id", "selector"],
        },
    },
    {
        "name": "browser_wait_for_network_idle",
        "description": "Wait until there are no network connections for at least 500ms",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "timeout": {"type": "number", "description": "Timeout in ms (default: 30000)"},
            },
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_wait(**kwargs):
        return await manager.wait(kwargs.get("tab_id"), kwargs.get("seconds", 1.0))
    handlers["browser_wait"] = browser_wait

    async def browser_wait_for_selector(**kwargs):
        return await manager.wait_for_selector(
            kwargs["tab_id"],
            kwargs["selector"],
            kwargs.get("state", "visible"),
            kwargs.get("timeout", 30000),
        )
    handlers["browser_wait_for_selector"] = browser_wait_for_selector

    async def browser_wait_for_network_idle(**kwargs):
        return await manager.wait_for_network_idle(kwargs["tab_id"], kwargs.get("timeout", 30000))
    handlers["browser_wait_for_network_idle"] = browser_wait_for_network_idle

    return handlers

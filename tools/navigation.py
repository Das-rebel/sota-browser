"""
SOTA Browser MCP Server — Navigation Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_navigate",
        "description": "Navigate to URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "url": {"type": "string"},
            },
            "required": ["tab_id", "url"],
        },
    },
    {
        "name": "browser_go_back",
        "description": "Navigate back in browser history",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_go_forward",
        "description": "Navigate forward in browser history",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_reload",
        "description": "Reload the current page",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_wait_for_navigation",
        "description": "Wait for navigation to complete or URL to match pattern",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "url_pattern": {"type": "string", "description": "Glob pattern or regex for URL match"},
                "timeout": {"type": "number", "description": "Timeout in ms (default 30000)"},
            },
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_navigate(**kwargs):
        return await manager.navigate(kwargs["tab_id"], kwargs["url"])
    handlers["browser_navigate"] = browser_navigate

    async def browser_go_back(**kwargs):
        return await manager.go_back(kwargs["tab_id"])
    handlers["browser_go_back"] = browser_go_back

    async def browser_go_forward(**kwargs):
        return await manager.go_forward(kwargs["tab_id"])
    handlers["browser_go_forward"] = browser_go_forward

    async def browser_reload(**kwargs):
        return await manager.reload(kwargs["tab_id"])
    handlers["browser_reload"] = browser_reload

    async def browser_wait_for_navigation(**kwargs):
        return await manager.wait_for_navigation(
            kwargs["tab_id"],
            kwargs.get("url_pattern"),
            kwargs.get("timeout", 30000),
        )
    handlers["browser_wait_for_navigation"] = browser_wait_for_navigation

    return handlers

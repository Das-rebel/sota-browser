"""
SOTA Browser MCP Server — Session & Tab Management Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_create_session",
        "description": "Create an isolated browser session (Playwright BrowserContext). "
                       "Each session has its own cookies, storage, and viewport.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Optional user identifier"},
                "width": {"type": "number", "description": "Viewport width (default 1280)"},
                "height": {"type": "number", "description": "Viewport height (default 720)"},
                "proxy": {"type": "string", "description": "Optional proxy server URL"},
                "user_agent": {"type": "string", "description": "Custom user agent string"},
                "timezone": {"type": "string", "description": "Timezone ID (e.g. America/New_York)"},
                "locale": {"type": "string", "description": "Locale (e.g. en-US)"},
            },
        },
    },
    {
        "name": "browser_close_session",
        "description": "Close a browser session and all its tabs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "browser_create_tab",
        "description": "Open a new tab in an existing session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "url": {"type": "string", "description": "Optional URL to navigate to immediately"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "browser_close_tab",
        "description": "Close a specific tab",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_list_tabs",
        "description": "List all tabs in a session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "browser_switch_tab",
        "description": "Switch to a tab by index within its session",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string", "description": "Current tab ID"},
                "tab_index": {"type": "number", "description": "Index of the tab to switch to"},
            },
            "required": ["tab_id", "tab_index"],
        },
    },
    {
        "name": "browser_info",
        "description": "Get browser server status: session count, tab count, version info",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "browser_set_viewport",
        "description": "Resize the viewport for a tab",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "width": {"type": "number"},
                "height": {"type": "number"},
            },
            "required": ["tab_id", "width", "height"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_create_session(**kwargs):
        opts = {k: v for k, v in kwargs.items() if k not in ("user_id",) and v is not None}
        return await manager.create_session(
            kwargs.get("user_id", "default"),
            **opts,
        )
    handlers["browser_create_session"] = browser_create_session

    async def browser_close_session(**kwargs):
        return await manager.close_session(kwargs["session_id"])
    handlers["browser_close_session"] = browser_close_session

    async def browser_create_tab(**kwargs):
        return await manager.create_tab(kwargs["session_id"], kwargs.get("url"))
    handlers["browser_create_tab"] = browser_create_tab

    async def browser_close_tab(**kwargs):
        return await manager.close_tab(kwargs["tab_id"])
    handlers["browser_close_tab"] = browser_close_tab

    async def browser_list_tabs(**kwargs):
        return await manager.list_tabs(kwargs["session_id"])
    handlers["browser_list_tabs"] = browser_list_tabs

    async def browser_switch_tab(**kwargs):
        return await manager.switch_tab(kwargs["tab_id"], kwargs["tab_index"])
    handlers["browser_switch_tab"] = browser_switch_tab

    async def browser_info(**kwargs):
        return manager.info()
    handlers["browser_info"] = browser_info

    async def browser_set_viewport(**kwargs):
        return await manager.set_viewport(kwargs["tab_id"], kwargs["width"], kwargs["height"])
    handlers["browser_set_viewport"] = browser_set_viewport

    return handlers

"""
SOTA Browser MCP Server — Snapshot / State / Inspection Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_snapshot",
        "description": "Get page accessibility tree",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "screenshot": {"type": "boolean"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_get_state",
        "description": "Get indexed clickable elements for automation",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_get_html",
        "description": "Return raw HTML of page or specific element (truncated to 100KB)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take screenshot",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "full": {"type": "boolean"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_extract_images",
        "description": "Extract images from page",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_extract_links",
        "description": "Extract all links (<a> href + text) from the page",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_get_text",
        "description": "Get inner text of page body or a specific element",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string", "description": "CSS selector (defaults to body)"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_evaluate",
        "description": "Execute JavaScript in main frame or specify frame_index",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "script": {"type": "string"},
                "frame_index": {"type": "integer"},
            },
            "required": ["tab_id", "script"],
        },
    },
    {
        "name": "browser_get_console_logs",
        "description": "Capture browser console messages and errors",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "clear": {"type": "boolean"},
            },
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_snapshot(**kwargs):
        return await manager.get_snapshot(kwargs["tab_id"], kwargs.get("screenshot", False))
    handlers["browser_snapshot"] = browser_snapshot

    async def browser_get_state(**kwargs):
        return await manager.get_state(kwargs["tab_id"])
    handlers["browser_get_state"] = browser_get_state

    async def browser_get_html(**kwargs):
        return await manager.get_html(kwargs["tab_id"], kwargs.get("selector"))
    handlers["browser_get_html"] = browser_get_html

    async def browser_screenshot(**kwargs):
        return await manager.screenshot(kwargs["tab_id"], kwargs.get("full", False))
    handlers["browser_screenshot"] = browser_screenshot

    async def browser_extract_images(**kwargs):
        return await manager.extract_images(kwargs["tab_id"])
    handlers["browser_extract_images"] = browser_extract_images

    async def browser_extract_links(**kwargs):
        return await manager.extract_links(kwargs["tab_id"])
    handlers["browser_extract_links"] = browser_extract_links

    async def browser_get_text(**kwargs):
        return await manager.get_text(kwargs["tab_id"], kwargs.get("selector"))
    handlers["browser_get_text"] = browser_get_text

    async def browser_evaluate(**kwargs):
        return await manager.evaluate(kwargs["tab_id"], kwargs["script"], kwargs.get("frame_index"))
    handlers["browser_evaluate"] = browser_evaluate

    async def browser_get_console_logs(**kwargs):
        return await manager.get_console_logs(kwargs["tab_id"], kwargs.get("clear", False))
    handlers["browser_get_console_logs"] = browser_get_console_logs

    return handlers

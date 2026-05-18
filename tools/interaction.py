"""
SOTA Browser MCP Server — Interaction Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_click",
        "description": "Click element by selector/ref/coordinates",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string"},
                "ref": {"type": "string"},
                "x": {"type": "number"},
                "y": {"type": "number"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_type",
        "description": "Type text into element",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "text": {"type": "string"},
                "selector": {"type": "string"},
                "ref": {"type": "string"},
            },
            "required": ["tab_id", "text"],
        },
    },
    {
        "name": "browser_press_key",
        "description": "Press key (Enter, Tab, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "key": {"type": "string"},
                "modifiers": {"type": "integer"},
            },
            "required": ["tab_id", "key"],
        },
    },
    {
        "name": "browser_scroll",
        "description": "Scroll page (dx/dy)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "dx": {"type": "number"},
                "dy": {"type": "number"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_hover",
        "description": "Hover over element by selector",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string"},
            },
            "required": ["tab_id", "selector"],
        },
    },
    {
        "name": "browser_drag_drop",
        "description": "Drag and drop from source selector to target selector",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "source": {"type": "string"},
                "target": {"type": "string"},
            },
            "required": ["tab_id", "source", "target"],
        },
    },
    {
        "name": "browser_select_option",
        "description": "Select option in a <select> element by value",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["tab_id", "selector", "value"],
        },
    },
    {
        "name": "browser_upload_file",
        "description": "Upload file(s) to an input[type=file] element",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "selector": {"type": "string"},
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File paths to upload",
                },
            },
            "required": ["tab_id", "selector", "paths"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_click(**kwargs):
        return await manager.click(
            kwargs["tab_id"],
            kwargs.get("selector"),
            kwargs.get("ref"),
            kwargs.get("x"),
            kwargs.get("y"),
        )
    handlers["browser_click"] = browser_click

    async def browser_type(**kwargs):
        return await manager.type_text(
            kwargs["tab_id"],
            kwargs["text"],
            kwargs.get("selector"),
            kwargs.get("ref"),
        )
    handlers["browser_type"] = browser_type

    async def browser_press_key(**kwargs):
        return await manager.press_key(kwargs["tab_id"], kwargs["key"], kwargs.get("modifiers", 0))
    handlers["browser_press_key"] = browser_press_key

    async def browser_scroll(**kwargs):
        return await manager.scroll(kwargs["tab_id"], kwargs.get("dx", 0), kwargs.get("dy", -300))
    handlers["browser_scroll"] = browser_scroll

    async def browser_hover(**kwargs):
        return await manager.hover(kwargs["tab_id"], kwargs["selector"])
    handlers["browser_hover"] = browser_hover

    async def browser_drag_drop(**kwargs):
        return await manager.drag_drop(kwargs["tab_id"], kwargs["source"], kwargs["target"])
    handlers["browser_drag_drop"] = browser_drag_drop

    async def browser_select_option(**kwargs):
        return await manager.select_option(kwargs["tab_id"], kwargs["selector"], kwargs["value"])
    handlers["browser_select_option"] = browser_select_option

    async def browser_upload_file(**kwargs):
        return await manager.upload_file(kwargs["tab_id"], kwargs["selector"], kwargs["paths"])
    handlers["browser_upload_file"] = browser_upload_file

    return handlers

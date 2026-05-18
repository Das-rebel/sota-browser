"""
SOTA Browser MCP Server — Frame / Iframe Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_list_frames",
        "description": "List all frames in the page",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_evaluate_in_frame",
        "description": "Evaluate JavaScript in a specific frame by URL contains",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "script": {"type": "string"},
                "frame_url_contains": {"type": "string"},
            },
            "required": ["tab_id", "script", "frame_url_contains"],
        },
    },
    {
        "name": "browser_get_frame_content",
        "description": "Get HTML content from a specific frame",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "frame_index": {"type": "integer"},
                "frame_url_contains": {"type": "string"},
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_inject_all_frames",
        "description": "Inject and run JS in all frames, returns per-frame results",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "script": {"type": "string"},
            },
            "required": ["tab_id", "script"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_list_frames(**kwargs):
        return await manager.list_frames(kwargs["tab_id"])
    handlers["browser_list_frames"] = browser_list_frames

    async def browser_evaluate_in_frame(**kwargs):
        return await manager.evaluate_in_frame(
            kwargs["tab_id"],
            kwargs["script"],
            kwargs.get("frame_selector"),
            kwargs.get("frame_url_contains"),
        )
    handlers["browser_evaluate_in_frame"] = browser_evaluate_in_frame

    async def browser_get_frame_content(**kwargs):
        return await manager.get_frame_content(
            kwargs["tab_id"],
            kwargs.get("frame_index"),
            kwargs.get("frame_url_contains"),
        )
    handlers["browser_get_frame_content"] = browser_get_frame_content

    async def browser_inject_all_frames(**kwargs):
        return await manager.inject_into_all_frames(kwargs["tab_id"], kwargs["script"])
    handlers["browser_inject_all_frames"] = browser_inject_all_frames

    return handlers

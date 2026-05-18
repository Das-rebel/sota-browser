"""
SOTA Browser MCP Server — HTTP Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_http_get",
        "description": "Direct HTTP GET request",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "timeout": {"type": "number"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_http_post",
        "description": "Direct HTTP POST request with body",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "data": {"type": "string", "description": "Request body as string"},
                "json": {"type": "object", "description": "Request body as JSON"},
                "headers": {"type": "object"},
                "timeout": {"type": "number"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_http_put",
        "description": "Direct HTTP PUT request with body",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "data": {"type": "string"},
                "json": {"type": "object"},
                "headers": {"type": "object"},
                "timeout": {"type": "number"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_http_delete",
        "description": "Direct HTTP DELETE request",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "headers": {"type": "object"},
                "timeout": {"type": "number"},
            },
            "required": ["url"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_http_get(**kwargs):
        return await manager.http_get(kwargs["url"], kwargs.get("headers"), kwargs.get("timeout", 10))
    handlers["browser_http_get"] = browser_http_get

    async def browser_http_post(**kwargs):
        return await manager.http_post(
            kwargs["url"], kwargs.get("data"), kwargs.get("json"),
            kwargs.get("headers"), kwargs.get("timeout", 10),
        )
    handlers["browser_http_post"] = browser_http_post

    async def browser_http_put(**kwargs):
        return await manager.http_put(
            kwargs["url"], kwargs.get("data"), kwargs.get("json"),
            kwargs.get("headers"), kwargs.get("timeout", 10),
        )
    handlers["browser_http_put"] = browser_http_put

    async def browser_http_delete(**kwargs):
        return await manager.http_delete(kwargs["url"], kwargs.get("headers"), kwargs.get("timeout", 10))
    handlers["browser_http_delete"] = browser_http_delete

    return handlers

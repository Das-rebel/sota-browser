"""
SOTA Browser MCP Server — Network Interception Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_intercept_request",
        "description": "Start capturing network requests for a tab",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "url_pattern": {
                    "type": "string",
                    "description": "Only capture requests matching this URL substring",
                },
            },
            "required": ["tab_id"],
        },
    },
    {
        "name": "browser_mock_response",
        "description": "Mock HTTP responses for a URL pattern using page.route()",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "url_pattern": {"type": "string", "description": "URL glob pattern to intercept"},
                "body": {"type": "string", "description": "Response body to return"},
                "status": {"type": "integer", "description": "HTTP status code (default: 200)"},
                "content_type": {
                    "type": "string",
                    "description": "Content-Type header (default: application/json)",
                },
            },
            "required": ["tab_id", "url_pattern", "body"],
        },
    },
    {
        "name": "browser_get_network_log",
        "description": "Get captured network request log for a tab",
        "inputSchema": {
            "type": "object",
            "properties": {"tab_id": {"type": "string"}},
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_intercept_request(**kwargs):
        return await manager.intercept_request(kwargs["tab_id"], kwargs.get("url_pattern"))
    handlers["browser_intercept_request"] = browser_intercept_request

    async def browser_mock_response(**kwargs):
        return await manager.mock_response(
            kwargs["tab_id"],
            kwargs["url_pattern"],
            kwargs["body"],
            kwargs.get("status", 200),
            kwargs.get("content_type", "application/json"),
        )
    handlers["browser_mock_response"] = browser_mock_response

    async def browser_get_network_log(**kwargs):
        return await manager.get_network_log(kwargs["tab_id"])
    handlers["browser_get_network_log"] = browser_get_network_log

    return handlers

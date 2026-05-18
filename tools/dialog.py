"""
SOTA Browser MCP Server — Dialog Handling Tools
"""

from __future__ import annotations

from typing import Callable, Dict


# ── MCP Tool Schemas ──────────────────────────────────────────────────

SCHEMAS = [
    {
        "name": "browser_handle_dialog",
        "description": "Accept or dismiss a browser dialog (alert, confirm, prompt)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tab_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["accept", "dismiss"],
                    "description": "Action to take on the dialog (default: accept)",
                },
                "prompt_text": {
                    "type": "string",
                    "description": "Text to enter for prompt dialogs (default: empty)",
                },
            },
            "required": ["tab_id"],
        },
    },
]


# ── Handler Registration ──────────────────────────────────────────────

def register(manager) -> Dict[str, Callable]:
    handlers: Dict[str, Callable] = {}

    async def browser_handle_dialog(**kwargs):
        return await manager.handle_dialog(
            kwargs["tab_id"],
            kwargs.get("action", "accept"),
            kwargs.get("prompt_text", ""),
        )
    handlers["browser_handle_dialog"] = browser_handle_dialog

    return handlers

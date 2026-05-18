"""
SOTA Browser MCP Server — Browser Memory Middleware

BrowserMemoryTree — stores last N actions per domain for recall.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from config import MEMORY_MAX_ACTIONS

logger = logging.getLogger("sota-browser.memory")


class BrowserMemoryTree:
    """Per-domain action history with recall capability."""

    def __init__(self, max_actions: int = MEMORY_MAX_ACTIONS):
        self.max_actions = max_actions
        # domain → deque of action records
        self._tree: Dict[str, deque] = {}

    def _domain_from_args(self, args: Dict[str, Any]) -> str:
        url = args.get("url", "")
        if url and url.startswith("http"):
            try:
                return urlparse(url).netloc
            except Exception:
                pass
        # Fallback: use tab_id hash as pseudo-domain
        tid = args.get("tab_id") or args.get("session_id") or "_unknown"
        return f"_tab:{tid[:16]}"

    def record(self, tool_name: str, args: Dict[str, Any], result: dict) -> None:
        domain = self._domain_from_args(args)
        if domain not in self._tree:
            self._tree[domain] = deque(maxlen=self.max_actions)
        self._tree[domain].append({
            "tool": tool_name,
            "args_summary": {k: str(v)[:80] for k, v in args.items()},
            "success": not bool(isinstance(result, dict) and result.get("error")),
            "timestamp": time.time(),
        })

    def recall(self, domain: str, action: str | None = None, limit: int = 20) -> List[dict]:
        """Recall actions for a domain, optionally filtered by tool name."""
        entries = self._tree.get(domain, deque())
        results = list(entries)
        if action:
            results = [r for r in results if r["tool"] == action]
        return results[-limit:]

    def domains(self) -> List[str]:
        return list(self._tree.keys())

    def stats(self) -> dict:
        return {
            "domains": len(self._tree),
            "total_actions": sum(len(d) for d in self._tree.values()),
        }


class MemoryMiddleware:
    """Wraps tool calls to record actions in BrowserMemoryTree."""

    def __init__(self, tree: BrowserMemoryTree | None = None):
        self.tree = tree or BrowserMemoryTree()

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        result = await next_fn()
        self.tree.record(tool_name, args, result if isinstance(result, dict) else {})
        return result


__all__ = ["BrowserMemoryTree", "MemoryMiddleware"]

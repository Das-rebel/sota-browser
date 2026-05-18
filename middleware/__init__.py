"""
SOTA Browser MCP Server — Middleware Pipeline

Middleware ordering (outer → inner):
  guardrails → cost_tracker → semantic_cache → circuit_breaker → retry → execute
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger("sota-browser.middleware")


class MiddlewarePipeline:
    """Chains middleware around a tool handler."""

    def __init__(self, middlewares: List | None = None):
        self.middlewares: List = middlewares or []

    async def execute(
        self,
        tool_name: str,
        args: Dict[str, Any],
        handler: Callable,
    ) -> dict:
        """Run the full middleware chain, then call handler(**args)."""

        async def chain(index: int) -> dict:
            if index >= len(self.middlewares):
                return await handler(**args)
            mw = self.middlewares[index]
            return await mw.wrap(tool_name, args, lambda: chain(index + 1))

        try:
            return await chain(0)
        except Exception as exc:
            logger.exception("Middleware pipeline error for %s", tool_name)
            return {"error": str(exc)}


__all__ = ["MiddlewarePipeline"]

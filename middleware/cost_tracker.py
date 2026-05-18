"""
SOTA Browser MCP Server — Cost Tracker Middleware

Per-session cost tracking with budget enforcement.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("sota-browser.cost_tracker")

# Relative costs per tool operation (arbitrary units)
OPERATION_COSTS: Dict[str, float] = {
    "browser_navigate": 1.0,
    "browser_snapshot": 0.5,
    "browser_screenshot": 0.5,
    "browser_click": 0.3,
    "browser_type": 0.3,
    "browser_evaluate": 0.2,
    "browser_http_get": 0.5,
    "browser_http_post": 0.6,
    "browser_http_put": 0.6,
    "browser_http_delete": 0.5,
    "browser_fill_form": 1.5,
    "browser_fill_form_from_resume": 2.0,
    "browser_fill_form_page": 1.8,
    "browser_submit_form": 1.0,
    "browser_analyze_form": 1.0,
    "browser_parse_resume": 1.0,
    "browser_download_file": 1.5,
}

DEFAULT_COST = 0.2  # default cost for unlisted tools


class CostTrackerMiddleware:
    """Tracks per-session costs and enforces a budget."""

    def __init__(self, default_budget: float = 10000.0):
        self.default_budget = default_budget
        # session_id → {"total": float, "operations": list}
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "total": 0.0,
                "budget": self.default_budget,
                "operations": [],
            }
        return self._sessions[session_id]

    def get_cost(self, tool_name: str) -> float:
        return OPERATION_COSTS.get(tool_name, DEFAULT_COST)

    def _extract_session_id(self, args: Dict[str, Any]) -> str:
        return args.get("session_id") or args.get("tab_id") or "_global"

    def summary(self, session_id: str | None = None) -> dict:
        if session_id:
            s = self._sessions.get(session_id)
            if not s:
                return {"error": "Session not found"}
            return {
                "session_id": session_id,
                "total_cost": s["total"],
                "budget": s["budget"],
                "remaining": s["budget"] - s["total"],
                "operation_count": len(s["operations"]),
            }
        return {
            "sessions": {
                sid: {"total": s["total"], "budget": s["budget"]}
                for sid, s in self._sessions.items()
            },
            "total_all": sum(s["total"] for s in self._sessions.values()),
        }

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        session_id = self._extract_session_id(args)
        session = self._get_session(session_id)
        cost = self.get_cost(tool_name)

        # Budget check
        if session["total"] + cost > session["budget"]:
            logger.warning(
                "Budget exceeded for session %s: %.1f + %.1f > %.1f",
                session_id,
                session["total"],
                cost,
                session["budget"],
            )
            return {"error": f"Budget exceeded for session {session_id}"}

        # Execute
        result = await next_fn()

        # Record cost
        session["total"] += cost
        session["operations"].append({
            "tool": tool_name,
            "cost": cost,
            "timestamp": time.time(),
        })

        return result


__all__ = ["CostTrackerMiddleware"]

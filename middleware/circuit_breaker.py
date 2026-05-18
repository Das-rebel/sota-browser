"""
SOTA Browser MCP Server — Circuit Breaker Middleware

Per-domain circuit breaker: CLOSED → OPEN → HALF_OPEN.
"""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

from config import CB_FAILURE_THRESHOLD, CB_RECOVERY_TIMEOUT_S

logger = logging.getLogger("sota-browser.circuit_breaker")


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class _DomainBreaker:
    """Tracks failure state for a single domain."""

    def __init__(self, threshold: int, recovery: float):
        self.threshold = threshold
        self.recovery = recovery
        self.state = State.CLOSED
        self.failures = 0
        self.opened_at: float = 0.0

    def record_success(self) -> None:
        self.failures = 0
        self.state = State.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = State.OPEN
            self.opened_at = time.monotonic()
            logger.warning("Circuit OPENED after %d failures", self.failures)

    def allow(self) -> bool:
        if self.state == State.CLOSED:
            return True
        if self.state == State.OPEN:
            if time.monotonic() - self.opened_at >= self.recovery:
                self.state = State.HALF_OPEN
                logger.info("Circuit moving to HALF_OPEN")
                return True
            return False
        # HALF_OPEN — allow one probe
        return True


class CircuitBreakerMiddleware:
    """Blocks calls to domains that are failing repeatedly."""

    def __init__(
        self,
        threshold: int = CB_FAILURE_THRESHOLD,
        recovery_s: float = CB_RECOVERY_TIMEOUT_S,
    ):
        self.threshold = threshold
        self.recovery_s = recovery_s
        self._breakers: Dict[str, _DomainBreaker] = {}

    def _domain(self, args: Dict[str, Any]) -> str:
        """Extract a best-effort domain key from args."""
        for key in ("url", "tab_id", "session_id"):
            val = args.get(key, "")
            if val and isinstance(val, str):
                return val.split("/")[:4][-1] if "/" in str(val) else str(val)[:64]
        return "_unknown"

    def _get_breaker(self, domain: str) -> _DomainBreaker:
        if domain not in self._breakers:
            self._breakers[domain] = _DomainBreaker(self.threshold, self.recovery_s)
        return self._breakers[domain]

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        domain = self._domain(args)
        breaker = self._get_breaker(domain)

        if not breaker.allow():
            return {"error": f"Circuit breaker OPEN for domain: {domain}"}

        try:
            result = await next_fn()
            breaker.record_success()
            return result
        except Exception as exc:
            breaker.record_failure()
            raise


__all__ = ["CircuitBreakerMiddleware"]

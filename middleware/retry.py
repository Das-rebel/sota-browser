"""
SOTA Browser MCP Server — Retry Middleware

Exponential backoff with jitter for transient failures.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Dict

from config import (
    RETRY_BASE_DELAY_MS,
    RETRY_JITTER,
    RETRY_MAX_ATTEMPTS,
    RETRY_MAX_DELAY_MS,
)

logger = logging.getLogger("sota-browser.retry")

# Error substrings that indicate a retryable failure
_RETRYABLE_PATTERNS = ("timeout", "connection", "network", "disconnected", "closed")


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    msg = str(exc).lower()
    return any(p in msg for p in _RETRYABLE_PATTERNS)


class RetryMiddleware:
    """Retries tool calls on transient errors with exponential backoff + jitter."""

    def __init__(
        self,
        max_attempts: int = RETRY_MAX_ATTEMPTS,
        base_delay_ms: int = RETRY_BASE_DELAY_MS,
        max_delay_ms: int = RETRY_MAX_DELAY_MS,
        jitter: float = RETRY_JITTER,
    ):
        self.max_attempts = max_attempts
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter = jitter

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        last_exc: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await next_fn()
            except Exception as exc:
                last_exc = exc
                if not _is_retryable(exc) or attempt == self.max_attempts:
                    raise
                delay_ms = min(
                    self.base_delay_ms * (2 ** (attempt - 1)),
                    self.max_delay_ms,
                )
                jitter_ms = delay_ms * self.jitter * random.random()
                total_s = (delay_ms + jitter_ms) / 1000.0
                logger.warning(
                    "Retry %d/%d for %s in %.1fms: %s",
                    attempt,
                    self.max_attempts,
                    tool_name,
                    total_s * 1000,
                    exc,
                )
                await asyncio.sleep(total_s)
        raise last_exc  # type: ignore[misc]


__all__ = ["RetryMiddleware"]

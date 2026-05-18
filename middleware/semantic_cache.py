"""
SOTA Browser MCP Server — Semantic Cache Middleware

Trigram Jaccard similarity cache — no embedding API required.
TTL-based expiration and invalidation on mutating operations.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Set, Tuple

from config import (
    CACHE_SIMILARITY_THRESHOLD,
    CACHE_TTL_HTTP_S,
    CACHE_TTL_SNAPSHOT_S,
)

logger = logging.getLogger("sota-browser.semantic_cache")

# Tools that invalidate cache entries (mutations)
_MUTATING_TOOLS = {
    "browser_navigate",
    "browser_click",
    "browser_type",
    "browser_fill_form",
    "browser_fill_form_from_resume",
    "browser_fill_form_page",
    "browser_submit_form",
    "browser_press_key",
    "browser_scroll",
    "browser_select_option",
    "browser_upload_file",
    "browser_hover",
    "browser_drag_drop",
    "browser_reload",
}

# Read-only tools eligible for caching
_CACHEABLE_TOOLS = {
    "browser_snapshot",
    "browser_get_state",
    "browser_get_html",
    "browser_extract_images",
    "browser_extract_links",
    "browser_get_text",
    "browser_screenshot",
    "browser_http_get",
    "browser_http_post",
    "browser_http_put",
    "browser_http_delete",
    "browser_list_frames",
    "browser_get_console_logs",
}


def _trigrams(text: str) -> Set[str]:
    """Extract character trigrams from a string."""
    text = text.lower().strip()
    if len(text) < 3:
        return {text} if text else set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


class _CacheEntry:
    __slots__ = ("key", "result", "trigrams", "expires_at", "tool_name")

    def __init__(self, key: str, result: dict, trigrams: Set[str],
                 expires_at: float, tool_name: str):
        self.key = key
        self.result = result
        self.trigrams = trigrams
        self.expires_at = expires_at
        self.tool_name = tool_name


class SemanticCacheMiddleware:
    """Trigram-Jaccard similarity cache for read-only tool results."""

    def __init__(
        self,
        threshold: float = CACHE_SIMILARITY_THRESHOLD,
        ttl_snapshot: float = CACHE_TTL_SNAPSHOT_S,
        ttl_http: float = CACHE_TTL_HTTP_S,
        max_entries: int = 500,
    ):
        self.threshold = threshold
        self.ttl_snapshot = ttl_snapshot
        self.ttl_http = ttl_http
        self.max_entries = max_entries
        # scope → list of _CacheEntry  (scope = tab_id or "_http")
        self._store: Dict[str, List[_CacheEntry]] = defaultdict(list)

    def _scope(self, tool_name: str, args: Dict[str, Any]) -> str:
        if tool_name.startswith("browser_http"):
            return "_http"
        return args.get("tab_id") or args.get("session_id") or "_global"

    def _ttl(self, tool_name: str) -> float:
        if tool_name.startswith("browser_http"):
            return self.ttl_http
        return self.ttl_snapshot

    def _make_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Deterministic key from tool name + stable args."""
        stable = {k: v for k, v in sorted(args.items()) if k not in ("tab_id", "session_id")}
        raw = f"{tool_name}:{sorted(stable.items())}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _query_text(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Get the text to use for similarity comparison."""
        if tool_name.startswith("browser_http"):
            return args.get("url", "")
        if tool_name in ("browser_snapshot", "browser_get_html", "browser_get_text"):
            return args.get("selector", "") + args.get("tab_id", "")
        return tool_name + str(sorted(args.items()))

    def _find(self, scope: str, key: str, query_text: str, tool_name: str) -> _CacheEntry | None:
        now = time.monotonic()
        entries = self._store[scope]
        query_tri = _trigrams(query_text)

        best_entry = None
        best_sim = 0.0

        for entry in entries:
            if entry.tool_name != tool_name:
                continue
            if entry.expires_at < now:
                continue
            if entry.key == key:
                return entry  # exact match
            sim = _jaccard(query_tri, entry.trigrams)
            if sim > best_sim:
                best_sim = sim
                best_entry = entry

        if best_entry and best_sim >= self.threshold:
            logger.debug("Cache hit (sim=%.2f) for %s", best_sim, tool_name)
            return best_entry
        return None

    def _store_result(self, scope: str, key: str, tool_name: str,
                      result: dict, query_text: str, ttl: float) -> None:
        now = time.monotonic()
        entries = self._store[scope]

        # Evict expired
        entries[:] = [e for e in entries if e.expires_at >= now]

        # Cap size
        if len(entries) >= self.max_entries:
            entries.pop(0)

        entries.append(_CacheEntry(
            key=key,
            result=result,
            trigrams=_trigrams(query_text),
            expires_at=now + ttl,
            tool_name=tool_name,
        ))

    def invalidate_scope(self, scope: str) -> None:
        """Invalidate all cache entries for a scope (tab)."""
        self._store.pop(scope, None)

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        # Mutating tools → invalidate cache for the scope
        if tool_name in _MUTATING_TOOLS:
            scope = self._scope(tool_name, args)
            self.invalidate_scope(scope)
            return await next_fn()

        # Non-cacheable tools → pass through
        if tool_name not in _CACHEABLE_TOOLS:
            return await next_fn()

        scope = self._scope(tool_name, args)
        key = self._make_key(tool_name, args)
        query_text = self._query_text(tool_name, args)

        # Check cache
        hit = self._find(scope, key, query_text, tool_name)
        if hit is not None:
            result = dict(hit.result)
            result["_cached"] = True
            return result

        # Execute and store
        result = await next_fn()
        if not isinstance(result, dict) or result.get("error"):
            return result

        self._store_result(scope, key, tool_name, result, query_text, self._ttl(tool_name))
        return result


__all__ = ["SemanticCacheMiddleware"]

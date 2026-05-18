"""
SOTA Browser MCP Server — Guardrails Middleware

Injection detection + PII redaction.  WARN-only by default; blocks in strict_mode.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger("sota-browser.guardrails")

# ---------------------------------------------------------------------------
# 17 injection patterns — look for prompt-injection / script-injection cues
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\s*/?\s*(script|iframe|object|embed|svg)", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"on(error|load|click|mouseover)\s*=", re.I),
    re.compile(r"eval\s*\(", re.I),
    re.compile(r"Function\s*\(", re.I),
    re.compile(r"document\.(cookie|domain|write)", re.I),
    re.compile(r"window\.(location|open|eval)", re.I),
    re.compile(r"fetch\s*\(", re.I),
    re.compile(r"XMLHttpRequest", re.I),
    re.compile(r"import\s*\(", re.I),
    re.compile(r"require\s*\(", re.I),
    re.compile(r"process\.env", re.I),
    re.compile(r"__proto__", re.I),
    re.compile(r"constructor\s*\[", re.I),
]

# ---------------------------------------------------------------------------
# 5 PII patterns
# ---------------------------------------------------------------------------
_PII_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ \-]?){13,19}\b")),
    ("phone", re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
]


class GuardrailsMiddleware:
    """Detects injection and PII in tool arguments.

    By default only logs warnings.  Set ``strict_mode=True`` to block.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode

    # ------------------------------------------------------------------

    @staticmethod
    def _check_injection(text: str) -> List[str]:
        hits: List[str] = []
        for pat in _INJECTION_PATTERNS:
            m = pat.search(text)
            if m:
                hits.append(m.group(0)[:80])
        return hits

    @staticmethod
    def _check_pii(text: str) -> Dict[str, List[str]]:
        found: Dict[str, List[str]] = {}
        for label, pat in _PII_PATTERNS:
            matches = pat.findall(text)
            if matches:
                found[label] = matches[:5]  # cap at 5
        return found

    def _scan_value(self, value: Any) -> Tuple[List[str], Dict[str, List[str]]]:
        """Recursively scan a value for injection + PII."""
        all_inj: List[str] = []
        all_pii: Dict[str, List[str]] = {}

        if isinstance(value, str):
            all_inj.extend(self._check_injection(value))
            pii = self._check_pii(value)
            for k, v in pii.items():
                all_pii.setdefault(k, []).extend(v)
        elif isinstance(value, dict):
            for v in value.values():
                inj, pii = self._scan_value(v)
                all_inj.extend(inj)
                for k, v2 in pii.items():
                    all_pii.setdefault(k, []).extend(v2)
        elif isinstance(value, (list, tuple)):
            for v in value:
                inj, pii = self._scan_value(v)
                all_inj.extend(inj)
                for k, v2 in pii.items():
                    all_pii.setdefault(k, []).extend(v2)
        return all_inj, all_pii

    # ------------------------------------------------------------------

    async def wrap(
        self,
        tool_name: str,
        args: Dict[str, Any],
        next_fn: Callable,
    ) -> dict:
        all_inj: List[str] = []
        all_pii: Dict[str, List[str]] = {}

        for key, value in args.items():
            # Skip non-text fields that won't carry injection
            if key in ("tab_id", "session_id", "frame_index", "tab_index",
                        "timeout", "seconds", "dx", "dy", "full", "clear",
                        "width", "height", "modifiers"):
                continue
            inj, pii = self._scan_value(value)
            all_inj.extend(inj)
            for k, v in pii.items():
                all_pii.setdefault(k, []).extend(v)

        if all_inj:
            msg = f"GUARDRAIL [{tool_name}]: injection patterns detected: {all_inj[:3]}"
            logger.warning(msg)
            if self.strict_mode:
                return {"error": f"Blocked by guardrails: injection patterns detected"}

        if all_pii:
            labels = list(all_pii.keys())
            msg = f"GUARDRAIL [{tool_name}]: PII detected: {labels}"
            logger.warning(msg)
            if self.strict_mode:
                return {"error": f"Blocked by guardrails: PII detected ({', '.join(labels)})"}

        return await next_fn()


__all__ = ["GuardrailsMiddleware"]

"""
SOTA Browser MCP Server — Session Model
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Session:
    """Represents an isolated browser session with its own context."""

    user_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    context: Any = None  # Playwright BrowserContext
    options: Dict[str, Any] = field(default_factory=dict)
    existing_browser: bool = False

    # ---- helpers ----

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created": True,
            "existing_browser": self.existing_browser,
            "note": "Using existing Chrome context" if self.existing_browser else "",
        }

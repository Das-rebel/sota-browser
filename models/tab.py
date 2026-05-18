"""
SOTA Browser MCP Server — Tab Model
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Tab:
    """Represents a single browser tab (Playwright Page)."""

    page: Any  # Playwright Page
    session_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ---- helpers ----

    def to_dict(self) -> dict:
        """Returns a JSON-serializable summary (url/title are async, call manually)."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "url": self.page.url,
        }

    async def to_dict_full(self) -> dict:
        url = self.page.url
        title = ""
        if url != "about:blank":
            try:
                title = await self.page.title()
            except Exception:
                pass
        return {"id": self.id, "session_id": self.session_id, "url": url, "title": title}

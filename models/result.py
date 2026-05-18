"""
SOTA Browser MCP Server — Tool Result Model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """Standardised wrapper for tool return values."""

    success: bool = True
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        if self.error:
            return {"error": self.error, **self.data}
        return {"success": self.success, **self.data}

"""EventLog — lightweight per-session audit trail."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class EventLog:
    """Records tool invocations and outcomes for audit and debugging."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    def record(self, tool_name: str, params: dict | None = None, result: str = "ok") -> None:
        """Append an event entry.

        Args:
            tool_name: The MCP tool that was called.
            params: Input parameters (for audit purposes).
            result: Short outcome string, e.g. "ok", "error", "rollback".
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "params": params or {},
            "result": result,
        }
        self._entries.append(entry)
        logger.debug("event: %s → %s", tool_name, result)

    def entries(self) -> list[dict[str, Any]]:
        """Return all logged events (newest last)."""
        return list(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

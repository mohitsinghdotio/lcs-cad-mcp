"""6-step write tool handler wrapper — snapshot → execute → rollback on failure."""
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


async def execute_write_tool(
    session,
    fn: Callable[..., Awaitable[Any]],
    *args: Any,
    **kwargs: Any,
) -> dict:
    """Execute a write tool with automatic snapshot/rollback support.

    Steps:
        1. Verify session exists.
        2. (Validation happens before this call.)
        3. Take snapshot.
        4. Call fn(*args, **kwargs).
        5. On success: clear snapshot and return result.
        6. On non-recoverable MCPError: rollback and return error response.
           On recoverable MCPError: return error response without rollback.
           On unexpected exception: rollback and return INTERNAL_ERROR.

    Args:
        session: DrawingSession (must not be None — caller checks).
        fn: Async callable implementing the tool business logic.
        *args, **kwargs: Forwarded to fn.

    Returns:
        A response dict (success or error envelope).
    """
    from lcs_cad_mcp.errors import MCPError, ErrorCode

    checkpoint_id = None
    if session.snapshots is not None:
        checkpoint_id = session.snapshots.take()

    try:
        result = await fn(*args, **kwargs)
        if checkpoint_id is not None:
            session.snapshots.clear(checkpoint_id)
        return result
    except MCPError as exc:
        if not exc.recoverable:
            logger.warning("Non-recoverable error: %s — rolling back", exc.code)
            if checkpoint_id is not None:
                try:
                    session.snapshots.restore(checkpoint_id)
                except Exception as rb_exc:
                    logger.error("Rollback failed: %s", rb_exc)
        else:
            # Recoverable — leave drawing state intact
            if checkpoint_id is not None:
                session.snapshots.clear(checkpoint_id)
        return exc.to_response()
    except Exception as exc:
        logger.exception("Unexpected error in write tool: %s", exc)
        if checkpoint_id is not None:
            try:
                session.snapshots.restore_latest()
            except Exception:
                pass
        return MCPError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unexpected server error: {exc}",
            recoverable=False,
            suggested_action="Review server logs for details.",
        ).to_response()

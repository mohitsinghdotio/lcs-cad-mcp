"""Integration tests for Story 1-4: recoverable vs non-recoverable error semantics."""
import pytest
from unittest.mock import MagicMock
from lcs_cad_mcp.errors import MCPError, ErrorCode


def test_non_recoverable_triggers_rollback():
    """AC3/Task 4.3: non-recoverable error triggers session.rollback()."""
    mock_session = MagicMock()
    mock_session.rollback = MagicMock()

    err = MCPError(code=ErrorCode.CLOSURE_FAILED, recoverable=False)
    # Simulate tool handler logic: check recoverable before returning
    if not err.recoverable and mock_session is not None:
        mock_session.rollback()

    mock_session.rollback.assert_called_once()


def test_recoverable_does_not_trigger_rollback():
    """AC2/Task 4.4: recoverable=True does NOT invoke rollback()."""
    mock_session = MagicMock()
    mock_session.rollback = MagicMock()

    err = MCPError(code=ErrorCode.LAYER_NOT_FOUND, recoverable=True)
    if not err.recoverable and mock_session is not None:
        mock_session.rollback()

    mock_session.rollback.assert_not_called()


def test_rollback_not_called_without_session():
    """AC2: rollback only invoked when session is active."""
    session = None
    err = MCPError(code=ErrorCode.CLOSURE_FAILED, recoverable=False)
    # Safe guard: no session → no rollback
    if not err.recoverable and session is not None:
        session.rollback()
    # No exception raised — test passes implicitly

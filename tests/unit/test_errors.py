"""Tests for Story 1-4: Structured error response contract."""
import pytest
from lcs_cad_mcp.errors import MCPError, ErrorCode, success_response


# ── AC1: envelope shape ────────────────────────────────────────────────────

def test_mcp_error_to_response_shape():
    """AC1: to_response() returns exact envelope with all required fields."""
    err = MCPError(
        code=ErrorCode.LAYER_NOT_FOUND,
        message="Layer 'walls' not found",
        recoverable=True,
        suggested_action="Call layer_list to see available layers",
    )
    resp = err.to_response()
    assert resp["success"] is False
    assert resp["data"] is None
    assert "error" in resp
    error = resp["error"]
    assert error["code"] == "LAYER_NOT_FOUND"
    assert error["message"] == "Layer 'walls' not found"
    assert error["recoverable"] is True
    assert error["suggested_action"] == "Call layer_list to see available layers"


def test_mcp_error_defaults():
    """AC1: MCPError defaults — message empty, recoverable True, suggested_action empty."""
    err = MCPError(code=ErrorCode.INTERNAL_ERROR)
    resp = err.to_response()
    assert resp["error"]["message"] == ""
    assert resp["error"]["recoverable"] is True
    assert resp["error"]["suggested_action"] == ""


def test_success_response_with_data():
    """AC1 / Task 2.3: success_response returns symmetric envelope."""
    resp = success_response({"x": 1})
    assert resp == {"success": True, "data": {"x": 1}, "error": None}


def test_success_response_no_data():
    """success_response with no args returns data=None."""
    resp = success_response()
    assert resp["success"] is True
    assert resp["data"] is None
    assert resp["error"] is None


def test_non_recoverable_error():
    """AC3: recoverable=False is preserved in envelope."""
    err = MCPError(code=ErrorCode.CLOSURE_FAILED, recoverable=False)
    resp = err.to_response()
    assert resp["error"]["recoverable"] is False


# ── AC4: ErrorCode constants ────────────────────────────────────────────────

def test_error_code_values_equal_attribute_names():
    """AC4/Task 5.4: every ErrorCode attribute value == attribute name."""
    for attr in vars(ErrorCode):
        if attr.startswith("_"):
            continue
        value = getattr(ErrorCode, attr)
        assert value == attr, f"ErrorCode.{attr} = {value!r}, expected {attr!r}"


def test_error_code_has_required_constants():
    """AC4: all domain-specific codes are defined."""
    required = [
        "SESSION_NOT_STARTED", "BACKEND_UNAVAILABLE", "LAYER_NOT_FOUND",
        "ENTITY_NOT_FOUND", "CLOSURE_FAILED", "DCR_VIOLATION", "CONFIG_INVALID",
        "VALIDATION_ERROR", "ROLLBACK_FAILED", "SNAPSHOT_FAILED",
        "AREA_CALC_FAILED", "REPORT_GENERATION_FAILED", "WORKFLOW_STEP_FAILED",
        "ARCHIVE_WRITE_FAILED", "INTERNAL_ERROR",
    ]
    for code in required:
        assert hasattr(ErrorCode, code), f"ErrorCode missing: {code}"


# ── DrawingSession rollback stub ────────────────────────────────────────────

def test_drawing_session_rollback_is_callable():
    """AC3/Task 4.1: DrawingSession.rollback() exists and is callable."""
    from lcs_cad_mcp.session.context import DrawingSession
    session = DrawingSession(session_id="test-123")
    session.rollback()  # must not raise

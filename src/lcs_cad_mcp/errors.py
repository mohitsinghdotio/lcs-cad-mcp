"""
Structured MCP error contract. All tool handlers use MCPError — never inline error dicts.

HOW TO USE:
  # (a) Recoverable error — session stays intact
  return MCPError(code=ErrorCode.LAYER_NOT_FOUND, message="Layer 'walls' not found",
                  recoverable=True, suggested_action="Call layer_list to see available layers").to_response()

  # (b) Non-recoverable error — triggers rollback
  return MCPError(code=ErrorCode.CLOSURE_FAILED, message="Polygon is not closed",
                  recoverable=False).to_response()

  # (c) Success
  return success_response({"layer_count": 5})
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import BaseModel


def success_response(data: "dict | list | None" = None) -> dict:
    """Return a standard success envelope. Use for ALL successful tool returns."""
    return {"success": True, "data": data, "error": None}


class ErrorCode:
    # Session
    SESSION_NOT_STARTED = "SESSION_NOT_STARTED"
    SESSION_ALREADY_ACTIVE = "SESSION_ALREADY_ACTIVE"
    NO_ACTIVE_SESSION = "NO_ACTIVE_SESSION"
    # CAD Backend
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    DRAWING_OPEN_FAILED = "DRAWING_OPEN_FAILED"
    DRAWING_SAVE_FAILED = "DRAWING_SAVE_FAILED"
    SNAPSHOT_FAILED = "SNAPSHOT_FAILED"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    # Layer
    LAYER_NOT_FOUND = "LAYER_NOT_FOUND"
    LAYER_ALREADY_EXISTS = "LAYER_ALREADY_EXISTS"
    LAYER_INVALID = "LAYER_INVALID"
    # Entity
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ENTITY_INVALID = "ENTITY_INVALID"
    # Verification
    CLOSURE_FAILED = "CLOSURE_FAILED"
    CONTAINMENT_FAILED = "CONTAINMENT_FAILED"
    GEOMETRY_INVALID = "GEOMETRY_INVALID"
    # DCR
    DCR_VIOLATION = "DCR_VIOLATION"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_NOT_LOADED = "CONFIG_NOT_LOADED"
    RULE_ENGINE_ERROR = "RULE_ENGINE_ERROR"
    # Area
    AREA_CALC_FAILED = "AREA_CALC_FAILED"
    # Reports
    REPORT_GENERATION_FAILED = "REPORT_GENERATION_FAILED"
    # Workflow / Archive
    WORKFLOW_STEP_FAILED = "WORKFLOW_STEP_FAILED"
    ARCHIVE_WRITE_FAILED = "ARCHIVE_WRITE_FAILED"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    # File I/O
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    # Snapshot
    SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"
    SESSION_DRAWING_NOT_OPEN = "SESSION_DRAWING_NOT_OPEN"
    # Generic
    INVALID_PARAMS = "INVALID_PARAMS"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class MCPError(Exception):
    """Structured MCP error — can be raised or converted to a response dict."""

    def __init__(
        self,
        code: str,
        message: str = "",
        recoverable: bool = True,
        suggested_action: str = "",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.suggested_action = suggested_action

    def to_response(self) -> dict:
        return {
            "success": False,
            "data": None,
            "error": {
                "code": self.code,
                "message": self.message,
                "recoverable": self.recoverable,
                "suggested_action": self.suggested_action,
            },
        }


def validate_input(model_cls: type[BaseModel], raw: dict) -> tuple[BaseModel | None, dict | None]:
    """Parse and validate raw dict against a Pydantic model.

    Returns (instance, None) on success, (None, error_response_dict) on failure.
    """
    from pydantic import ValidationError

    try:
        return model_cls(**raw), None
    except ValidationError as exc:
        msg = "; ".join(
            f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        return None, MCPError(
            code=ErrorCode.VALIDATION_ERROR,
            message=msg,
            recoverable=True,
            suggested_action="Check parameter types and required fields per tools/list schema.",
        ).to_response()

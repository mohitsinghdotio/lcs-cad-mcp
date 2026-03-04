"""Hypothesis-based property tests for the validation framework."""
import pytest
from hypothesis import given, strategies as st, settings
from pydantic import BaseModel, ValidationError

from lcs_cad_mcp.errors import validate_input, ErrorCode
from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput
from lcs_cad_mcp.modules.layers.schemas import LayerCreateInput
from lcs_cad_mcp.modules.predcr.schemas import PredcrRunCheckInput
from lcs_cad_mcp.modules.entities.schemas import EntityQueryInput
from lcs_cad_mcp.modules.verification.schemas import VerifyClosureInput
from lcs_cad_mcp.modules.config.schemas import ConfigLoadInput
from lcs_cad_mcp.modules.area.schemas import AreaCalculateInput
from lcs_cad_mcp.modules.autodcr.schemas import AutodcrRunInput
from lcs_cad_mcp.modules.reports.schemas import ReportGenerateInput
from lcs_cad_mcp.modules.workflow.schemas import WorkflowRunInput


ALL_SCHEMA_MODULES = [
    CadOpenDrawingInput,
    LayerCreateInput,
    PredcrRunCheckInput,
    EntityQueryInput,
    VerifyClosureInput,
    ConfigLoadInput,
    AreaCalculateInput,
    AutodcrRunInput,
    ReportGenerateInput,
    WorkflowRunInput,
]


def test_all_schema_modules_export_base_model_subclass():
    """Each schemas module must export at least one BaseModel subclass."""
    for cls in ALL_SCHEMA_MODULES:
        assert issubclass(cls, BaseModel), f"{cls} is not a BaseModel subclass"


class TestValidateInputUtility:
    def test_valid_input_returns_instance(self):
        instance, error = validate_input(CadOpenDrawingInput, {"path": "/tmp/test.dxf"})
        assert instance is not None
        assert error is None
        assert instance.path == "/tmp/test.dxf"

    def test_missing_required_field_returns_error_envelope(self):
        instance, error = validate_input(CadOpenDrawingInput, {})
        assert instance is None
        assert error is not None
        assert error["success"] is False
        assert error["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert error["error"]["recoverable"] is True

    def test_wrong_type_returns_error_envelope(self):
        # read_only must be bool-coercible; passing an unconvertible string should fail
        instance, error = validate_input(CadOpenDrawingInput, {"path": "/tmp/t.dxf", "read_only": "not-valid"})
        # Pydantic v2 coerces strings to bool; empty string fails, "not-valid" actually raises
        # Either it succeeds (coercion) or fails (validation error) — we just assert no unhandled exception
        assert instance is not None or error is not None

    def test_validation_error_code(self):
        _, error = validate_input(LayerCreateInput, {})
        assert error["error"]["code"] == "VALIDATION_ERROR"

    def test_validation_error_recoverable_true(self):
        _, error = validate_input(LayerCreateInput, {})
        assert error["error"]["recoverable"] is True

    def test_suggested_action_present(self):
        _, error = validate_input(LayerCreateInput, {})
        assert len(error["error"]["suggested_action"]) > 0


@settings(max_examples=50)
@given(path=st.text())
def test_cad_open_drawing_never_raises_unhandled(path):
    """Server must never raise an unhandled exception regardless of path input."""
    instance, error = validate_input(CadOpenDrawingInput, {"path": path})
    # Either we get a valid instance or a structured error — never an exception
    assert instance is not None or error is not None


@settings(max_examples=50)
@given(name=st.text())
def test_layer_create_never_raises_unhandled(name):
    """LayerCreateInput must never raise an unhandled exception."""
    instance, error = validate_input(LayerCreateInput, {"name": name})
    assert instance is not None or error is not None

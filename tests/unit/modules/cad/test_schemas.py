"""Tests for cad module Pydantic schemas."""
import pytest
from pydantic import ValidationError
from lcs_cad_mcp.modules.cad.schemas import CadOpenDrawingInput, CadPingInput, CadSelectBackendInput


class TestCadOpenDrawingInput:
    def test_valid_input(self):
        inp = CadOpenDrawingInput(path="/tmp/test.dxf")
        assert inp.path == "/tmp/test.dxf"
        assert inp.read_only is False

    def test_valid_with_read_only(self):
        inp = CadOpenDrawingInput(path="/tmp/test.dxf", read_only=True)
        assert inp.read_only is True

    def test_missing_required_path_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            CadOpenDrawingInput()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("path",) for e in errors)

    def test_wrong_type_for_read_only_raises(self):
        with pytest.raises(ValidationError):
            CadOpenDrawingInput(path="/tmp/test.dxf", read_only="not-a-bool-invalid-string-xyz")

    def test_whitespace_stripped_from_path(self):
        inp = CadOpenDrawingInput(path="  /tmp/test.dxf  ")
        assert inp.path == "/tmp/test.dxf"

    def test_frozen_model_immutable(self):
        inp = CadOpenDrawingInput(path="/tmp/test.dxf")
        with pytest.raises(Exception):
            inp.path = "/tmp/other.dxf"

    def test_path_required_in_schema(self):
        schema = CadOpenDrawingInput.model_json_schema()
        assert "path" in schema.get("required", [])

    def test_read_only_optional_with_default_false(self):
        schema = CadOpenDrawingInput.model_json_schema()
        assert "read_only" not in schema.get("required", [])
        props = schema.get("properties", {})
        assert "read_only" in props


class TestCadPingInput:
    def test_instantiate_no_args(self):
        inp = CadPingInput()
        assert inp is not None

    def test_frozen(self):
        inp = CadPingInput()
        # frozen means no attribute assignment
        with pytest.raises(Exception):
            inp.some_field = "value"


class TestCadSelectBackendInput:
    def test_valid_ezdxf(self):
        inp = CadSelectBackendInput(backend="ezdxf")
        assert inp.backend == "ezdxf"

    def test_valid_com(self):
        inp = CadSelectBackendInput(backend="com")
        assert inp.backend == "com"

    def test_missing_backend_raises(self):
        with pytest.raises(ValidationError):
            CadSelectBackendInput()

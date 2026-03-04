"""Tests for layers module Pydantic schemas."""
import pytest
from pydantic import ValidationError
from lcs_cad_mcp.modules.layers.schemas import LayerCreateInput


class TestLayerCreateInput:
    def test_valid_input(self):
        inp = LayerCreateInput(name="walls")
        assert inp.name == "walls"
        assert inp.color == 7
        assert inp.linetype == "CONTINUOUS"

    def test_custom_color_and_linetype(self):
        inp = LayerCreateInput(name="columns", color=3, linetype="DASHED")
        assert inp.color == 3
        assert inp.linetype == "DASHED"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            LayerCreateInput()
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_whitespace_stripped_from_name(self):
        inp = LayerCreateInput(name="  walls  ")
        assert inp.name == "walls"

    def test_frozen(self):
        inp = LayerCreateInput(name="walls")
        with pytest.raises(Exception):
            inp.name = "other"

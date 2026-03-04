"""Unit tests for PreDCR Layer Specification Catalog."""
import pytest
from lcs_cad_mcp.modules.predcr.layer_registry import (
    PREDCR_LAYERS, LayerSpec,
    get_layers_for_building_type, get_layer_by_name, get_all_building_types,
)

VALID_LINETYPES = {"Continuous", "DASHED", "HIDDEN", "CENTER", "DASHDOT", "BORDER"}


def test_predcr_layers_loads_without_error():
    assert len(PREDCR_LAYERS) >= 40, f"Expected >= 40 layers, got {len(PREDCR_LAYERS)}"


def test_no_duplicate_layer_names():
    names = [s.name for s in PREDCR_LAYERS]
    assert len(names) == len(set(names)), f"Duplicate layer names found"


def test_all_color_indices_in_range():
    for spec in PREDCR_LAYERS:
        assert 1 <= spec.color_index <= 256, f"{spec.name} color_index out of range: {spec.color_index}"


def test_all_linetypes_valid():
    for spec in PREDCR_LAYERS:
        assert spec.linetype in VALID_LINETYPES, f"{spec.name} has invalid linetype: {spec.linetype}"


def test_residential_has_at_least_30_layers():
    specs = get_layers_for_building_type("residential")
    assert len(specs) >= 30, f"Expected >= 30 residential layers, got {len(specs)}"


def test_commercial_has_at_least_30_layers():
    specs = get_layers_for_building_type("commercial")
    assert len(specs) >= 30, f"Expected >= 30 commercial layers, got {len(specs)}"


def test_industrial_has_at_least_20_layers():
    specs = get_layers_for_building_type("industrial")
    assert len(specs) >= 20, f"Expected >= 20 industrial layers, got {len(specs)}"


def test_get_layer_by_name_found():
    spec = get_layer_by_name("PREDCR-WALL-EXT")
    assert spec is not None
    assert spec.name == "PREDCR-WALL-EXT"
    assert spec.color_index == 7


def test_get_layer_by_name_case_insensitive():
    spec = get_layer_by_name("predcr-wall-ext")
    assert spec is not None
    assert spec.name == "PREDCR-WALL-EXT"


def test_get_layer_by_name_not_found():
    spec = get_layer_by_name("NONEXISTENT-LAYER")
    assert spec is None


def test_get_all_building_types_contains_main_types():
    types = get_all_building_types()
    assert "residential" in types
    assert "commercial" in types
    assert "industrial" in types
    assert types == sorted(types)  # Must be sorted


def test_get_layers_for_unknown_building_type_raises():
    with pytest.raises(ValueError, match="Unknown building type"):
        get_layers_for_building_type("underwater")


def test_layer_spec_is_frozen():
    spec = PREDCR_LAYERS[0]
    with pytest.raises((TypeError, Exception)):
        spec.name = "MODIFIED"  # Should raise because frozen=True


def test_layer_spec_required_for_non_empty():
    for spec in PREDCR_LAYERS:
        assert len(spec.required_for) > 0, f"{spec.name} has empty required_for"

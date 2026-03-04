"""
PreDCR Layer Specification Catalog — authoritative source of truth for all PreDCR layer definitions.
No MCP or CAD backend imports. Pure data module.
"""
from pydantic import BaseModel, ConfigDict, Field


class LayerSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    color_index: int = Field(ge=1, le=256)
    linetype: str
    required_for: list[str]
    entity_types: list[str]


PREDCR_LAYERS: list[LayerSpec] = [
    # --- Walls and Structure ---
    LayerSpec(name="PREDCR-WALL-EXT", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-WALL-INT", color_index=8, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-COLUMN", color_index=5, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE", "CIRCLE"]),
    LayerSpec(name="PREDCR-BEAM", color_index=5, linetype="Continuous",
              required_for=["commercial", "industrial"], entity_types=["LINE", "LWPOLYLINE"]),
    LayerSpec(name="PREDCR-FOUNDATION", color_index=5, linetype="CENTER",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-SLAB", color_index=8, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-RETAINING-WALL", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),

    # --- Openings ---
    LayerSpec(name="PREDCR-DOOR", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-DOOR-EXT", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-WINDOW", color_index=4, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-WINDOW-EXT", color_index=4, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-SHUTTER", color_index=3, linetype="Continuous",
              required_for=["commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-VENTILATOR", color_index=4, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["INSERT", "LINE"]),

    # --- Vertical Circulation ---
    LayerSpec(name="PREDCR-STAIR", color_index=6, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE", "LINE"]),
    LayerSpec(name="PREDCR-RAMP", color_index=6, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-LIFT", color_index=2, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LWPOLYLINE"]),
    LayerSpec(name="PREDCR-ESCALATOR", color_index=2, linetype="Continuous",
              required_for=["commercial"], entity_types=["INSERT", "LWPOLYLINE"]),

    # --- Sanitation and Services ---
    LayerSpec(name="PREDCR-TOILET", color_index=3, linetype="HIDDEN",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LWPOLYLINE"]),
    LayerSpec(name="PREDCR-SHAFT", color_index=1, linetype="CENTER",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-DUCT", color_index=1, linetype="CENTER",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-WATER-TANK", color_index=4, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-SEPTIC-TANK", color_index=1, linetype="DASHED",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-PLUMBING", color_index=3, linetype="HIDDEN",
              required_for=["residential", "commercial", "industrial"], entity_types=["LINE"]),

    # --- Site and Boundary ---
    LayerSpec(name="PREDCR-SITE-BOUNDARY", color_index=2, linetype="DASHED",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-SETBACK", color_index=1, linetype="DASHED",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-ROAD", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-COMPOUND-WALL", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-GATE", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-PLOT-BOUNDARY", color_index=2, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),

    # --- Open Space and Landscape ---
    LayerSpec(name="PREDCR-OPEN-SPACE", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE", "HATCH"]),
    LayerSpec(name="PREDCR-GARDEN", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE", "HATCH"]),
    LayerSpec(name="PREDCR-LANDSCAPE", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE", "HATCH"]),

    # --- Areas and Computation ---
    LayerSpec(name="PREDCR-BUILTUP-AREA", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-CARPET-AREA", color_index=7, linetype="DASHED",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-COMMON-AREA", color_index=8, linetype="DASHED",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-FLOOR-PLATE", color_index=8, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["LWPOLYLINE"]),

    # --- Annotations ---
    LayerSpec(name="PREDCR-DIMENSION", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["DIMENSION"]),
    LayerSpec(name="PREDCR-TEXT", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["TEXT", "MTEXT"]),
    LayerSpec(name="PREDCR-HATCH", color_index=8, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["HATCH"]),
    LayerSpec(name="PREDCR-TITLE-BLOCK", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["TEXT", "LINE"]),
    LayerSpec(name="PREDCR-NORTH-ARROW", color_index=7, linetype="Continuous",
              required_for=["residential", "commercial", "industrial"], entity_types=["INSERT"]),

    # --- Building-Type Specific ---
    LayerSpec(name="PREDCR-PARKING", color_index=3, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-LOADING", color_index=3, linetype="Continuous",
              required_for=["commercial", "industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-MACHINERY", color_index=5, linetype="Continuous",
              required_for=["industrial"], entity_types=["INSERT", "LWPOLYLINE"]),
    LayerSpec(name="PREDCR-WAREHOUSE", color_index=8, linetype="Continuous",
              required_for=["industrial"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-FIRE-EXIT", color_index=1, linetype="Continuous",
              required_for=["commercial", "industrial"], entity_types=["INSERT", "LINE"]),
    LayerSpec(name="PREDCR-FIRE-HYDRANT", color_index=1, linetype="Continuous",
              required_for=["commercial", "industrial"], entity_types=["INSERT"]),
    LayerSpec(name="PREDCR-UNIT-BOUNDARY", color_index=2, linetype="DASHED",
              required_for=["residential"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-BALCONY", color_index=4, linetype="Continuous",
              required_for=["residential"], entity_types=["LWPOLYLINE"]),
    LayerSpec(name="PREDCR-TERRACE", color_index=4, linetype="Continuous",
              required_for=["residential", "commercial"], entity_types=["LWPOLYLINE"]),
]


def get_layers_for_building_type(building_type: str) -> list[LayerSpec]:
    """Return all LayerSpecs required for the given building type.

    Raises ValueError for completely unknown building types.
    """
    bt = building_type.lower()
    result = [s for s in PREDCR_LAYERS if bt in s.required_for]
    if not result:
        raise ValueError(
            f"Unknown building type: {building_type!r}. "
            f"Known types: {get_all_building_types()}"
        )
    return result


def get_layer_by_name(name: str) -> LayerSpec | None:
    """Case-insensitive lookup of a LayerSpec by name. Returns None if not found."""
    name_upper = name.upper()
    return next((s for s in PREDCR_LAYERS if s.name.upper() == name_upper), None)


def get_all_building_types() -> list[str]:
    """Return deduplicated sorted list of all building type strings in the registry."""
    types: set[str] = set()
    for spec in PREDCR_LAYERS:
        types.update(spec.required_for)
    return sorted(types)

"""Pydantic v2 input/output schemas for the entities module."""
from pydantic import BaseModel, Field, ConfigDict


class EntityQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str | None = Field(None, description="Filter by layer name. None returns all layers.")
    entity_type: str | None = Field(None, description="Filter by entity type (e.g. 'LINE', 'LWPOLYLINE', 'ARC', 'CIRCLE', 'TEXT', 'INSERT').")


class EntityDrawPolylineInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    points: list[list[float]] = Field(..., description="List of [x, y] coordinate pairs defining the polyline vertices.")
    closed: bool = Field(False, description="If true, close the polyline by connecting the last point to the first.")


class EntityDrawLineInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    start: list[float] = Field(..., description="Start point [x, y].")
    end: list[float] = Field(..., description="End point [x, y].")


class EntityDrawArcInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    center: list[float] = Field(..., description="Center point [x, y].")
    radius: float = Field(..., description="Arc radius in drawing units.")
    start_angle: float = Field(..., description="Start angle in degrees (0 = east, counter-clockwise).")
    end_angle: float = Field(..., description="End angle in degrees.")


class EntityDrawCircleInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    center: list[float] = Field(..., description="Center point [x, y].")
    radius: float = Field(..., description="Circle radius in drawing units.")


class EntityAddTextInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    text: str = Field(..., description="Text content to add.")
    position: list[float] = Field(..., description="Insertion point [x, y].")
    height: float = Field(2.5, description="Text height in drawing units.")
    rotation: float = Field(0.0, description="Text rotation angle in degrees.")


class EntityInsertBlockInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Target layer name.")
    block_name: str = Field(..., description="Name of the block definition to insert.")
    position: list[float] = Field(..., description="Insertion point [x, y].")
    scale: float = Field(1.0, description="Uniform scale factor.")
    rotation: float = Field(0.0, description="Rotation angle in degrees.")


class EntityMoveInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    entity_handle: str = Field(..., description="DXF entity handle to move.")
    displacement: list[float] = Field(..., description="Displacement vector [dx, dy].")


class EntityCopyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    entity_handle: str = Field(..., description="DXF entity handle to copy.")
    displacement: list[float] = Field(..., description="Displacement vector [dx, dy] for the copy.")


class EntityDeleteInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    entity_handle: str = Field(..., description="DXF entity handle to delete.")


class EntityChangeLayerInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    entity_handle: str = Field(..., description="DXF entity handle to move to a different layer.")
    target_layer: str = Field(..., description="Name of the target layer.")


class EntityClosePolylineInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    entity_handle: str = Field(..., description="Handle of the LWPOLYLINE entity to close.")

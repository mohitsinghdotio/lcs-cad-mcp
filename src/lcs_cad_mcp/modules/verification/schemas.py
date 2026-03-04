"""Pydantic v2 input/output schemas for the verification module."""
from pydantic import BaseModel, Field, ConfigDict


class VerifyClosureInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Layer name to verify closure on.")
    tolerance: float = Field(0.001, description="Maximum gap distance considered 'closed' (drawing units).")


class VerifyContainmentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    outer_layer: str = Field(..., description="Layer containing the outer boundary polygon.")
    inner_layer: str = Field(..., description="Layer containing the inner polygons that must be contained.")
    tolerance: float = Field(0.001, description="Tolerance for containment check (drawing units).")


class VerifyNamingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code whose naming conventions to validate against.")


class VerifyMinEntityCountInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Layer to check entity count on.")
    min_count: int = Field(1, description="Minimum required number of entities.")
    entity_type: str | None = Field(None, description="Optional entity type filter (e.g. 'LINE', 'LWPOLYLINE').")


class VerifyAllInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code for naming validation.")
    tolerance: float = Field(0.001, description="Tolerance for geometry checks (drawing units).")

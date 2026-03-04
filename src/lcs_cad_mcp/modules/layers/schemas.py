"""Pydantic v2 input/output schemas for the layers module."""
from pydantic import BaseModel, Field, ConfigDict


class LayerCreateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    name: str = Field(..., description="Layer name. Must be unique in the drawing.")
    color: int = Field(7, description="ACI color index (1–255). Default 7 = white.")
    linetype: str = Field("CONTINUOUS", description="Linetype name (e.g. 'CONTINUOUS', 'DASHED').")


class LayerDeleteInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    name: str = Field(..., description="Name of the layer to delete.")
    force: bool = Field(False, description="If true, delete even if the layer has entities.")


class LayerGetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    name: str = Field(..., description="Name of the layer to retrieve.")


class LayerSetPropertiesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    name: str = Field(..., description="Name of the layer to modify.")
    color: int | None = Field(None, description="New ACI color index (1–255).")
    linetype: str | None = Field(None, description="New linetype name.")
    locked: bool | None = Field(None, description="Lock or unlock the layer.")
    frozen: bool | None = Field(None, description="Freeze or thaw the layer.")
    visible: bool | None = Field(None, description="Show or hide the layer.")

"""Pydantic v2 input/output schemas for the area module."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class AreaCalculateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    layer: str = Field(..., description="Layer containing the closed polygon(s) to compute area for.")
    unit: Literal["sqm", "sqft"] = Field("sqm", description="Unit of area: 'sqm' (square metres) or 'sqft' (square feet).")


class AreaComputePlotInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    plot_layer: str = Field(..., description="Layer containing the plot boundary polygon.")
    unit: Literal["sqm", "sqft"] = Field("sqm", description="Unit of area.")


class AreaComputeBuiltupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    floor_layers: list[str] = Field(..., description="Layers containing built-up area polygons per floor.")
    unit: Literal["sqm", "sqft"] = Field("sqm", description="Unit of area.")


class AreaComputeCarpetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    carpet_layer: str = Field(..., description="Layer containing carpet area polygons.")
    unit: Literal["sqm", "sqft"] = Field("sqm", description="Unit of area.")


class AreaComputeFsiInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    plot_layer: str = Field(..., description="Layer containing the plot boundary.")
    floor_layers: list[str] = Field(..., description="Layers contributing to FSI calculation.")
    unit: Literal["sqm", "sqft"] = Field("sqm", description="Unit of area for intermediate calculations.")


class AreaComputeCoverageInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    plot_layer: str = Field(..., description="Layer containing the plot boundary.")
    footprint_layer: str = Field(..., description="Layer containing ground floor footprint polygon.")

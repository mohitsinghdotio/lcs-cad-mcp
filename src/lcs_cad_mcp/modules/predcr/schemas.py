"""Pydantic v2 input/output schemas for the predcr module."""
from pydantic import BaseModel, Field, ConfigDict


class PredcrRunCheckInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    drawing_path: str = Field(..., description="Path to the DXF drawing file to check.")
    authority_code: str = Field(..., description="Local authority code for DCR rule set (e.g. 'MCGM', 'HMDA').")


class PredcrRunSetupInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code for DCR rule set.")
    project_type: str = Field("residential", description="Project type: 'residential', 'commercial', or 'mixed'.")


class PredcrGetLayerSpecInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code.")
    layer_name: str = Field(..., description="Layer name to look up specification for.")


class PredcrValidateDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code for validation rules.")

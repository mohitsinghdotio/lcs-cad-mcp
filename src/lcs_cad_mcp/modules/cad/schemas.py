"""Pydantic v2 input/output schemas for the cad module."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class CadOpenDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    path: str = Field(..., description="Absolute or relative path to the DXF/DWG file to open.")
    read_only: bool = Field(False, description="If true, open the drawing in read-only mode. No save operations are permitted.")


class CadPingInput(BaseModel):
    """Zero-argument schema for the cad_ping health check tool."""
    model_config = ConfigDict(frozen=True)


class CadNewDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    name: str = Field("Untitled", description="Display name for the new drawing.")
    units: Literal["metric", "imperial"] = Field("metric", description="Unit system: 'metric' (mm) or 'imperial' (inches).")


class CadSaveDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    path: str = Field(..., description="Absolute path to save the drawing file.")
    dxf_version: Literal["R12", "R2000", "R2007", "R2010", "R2013", "R2018"] = Field("R2018", description="Output DXF version.")


class CadCloseDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    save: bool = Field(True, description="If true, save before closing.")


class CadSelectBackendInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    backend: str = Field(..., description="Backend to use: 'ezdxf' or 'com'.")

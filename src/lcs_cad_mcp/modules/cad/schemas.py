"""Pydantic v2 input/output schemas for the cad module."""
from pydantic import BaseModel, Field, ConfigDict


class CadOpenDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    path: str = Field(..., description="Absolute or relative path to the DXF/DWG file to open.")
    read_only: bool = Field(False, description="If true, open the drawing in read-only mode. No save operations are permitted.")


class CadPingInput(BaseModel):
    """Zero-argument schema for the cad_ping health check tool."""
    model_config = ConfigDict(frozen=True)


class CadSaveDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    path: str | None = Field(None, description="Optional path to save the drawing. If None, saves to the current path.")


class CadCloseDrawingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    save: bool = Field(True, description="If true, save before closing.")


class CadSelectBackendInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    backend: str = Field(..., description="Backend to use: 'ezdxf' or 'com'.")

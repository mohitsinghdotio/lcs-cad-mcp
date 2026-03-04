"""Pydantic v2 input/output schemas for the autodcr module."""
from pydantic import BaseModel, Field, ConfigDict


class AutodcrRunInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    drawing_path: str = Field(..., description="Path to the DXF drawing file to scrutinise.")
    authority_code: str = Field(..., description="Local authority code for DCR rule set (e.g. 'MCGM', 'HMDA').")
    output_path: str | None = Field(None, description="Optional path to save the scrutiny report. If None, the report is returned inline.")


class AutodcrRunScrutinyInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code for rule evaluation.")
    dry_run: bool = Field(False, description="If true, run checks without writing any output or archive entry.")


class AutodcrDryRunInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code.")
    max_iterations: int = Field(10, description="Maximum correction loop iterations.")

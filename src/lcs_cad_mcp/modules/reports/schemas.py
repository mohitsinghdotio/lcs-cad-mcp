"""Pydantic v2 input/output schemas for the reports module."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class ReportGenerateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    report_type: Literal["pdf", "docx"] = Field(..., description="Output format: 'pdf' or 'docx'.")
    output_path: str = Field(..., description="Absolute path where the report file will be written.")


class ReportGeneratePdfInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    output_path: str = Field(..., description="Absolute path for the generated PDF report.")
    run_id: str | None = Field(None, description="Optional scrutiny run ID to include in the report header.")


class ReportGenerateDocxInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    output_path: str = Field(..., description="Absolute path for the generated DOCX report.")
    run_id: str | None = Field(None, description="Optional scrutiny run ID to include in the report header.")


class ReportGenerateJsonInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    output_path: str = Field(..., description="Absolute path for the generated JSON report file.")
    run_id: str | None = Field(None, description="Optional scrutiny run ID to include in the report.")


class ReportAssembleDataInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    run_id: str = Field(..., description="Scrutiny run ID to assemble report data for.")

"""Pydantic v2 input/output schemas for the workflow module."""
from pydantic import BaseModel, Field, ConfigDict


class WorkflowRunInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    workflow_name: str = Field(..., description="Name of the workflow to execute (e.g. 'predcr_setup', 'autodcr_full').")
    params: dict = Field(default_factory=dict, description="Key-value parameters passed to the workflow.")


class WorkflowRetrieveRunInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    run_id: str = Field(..., description="Unique run ID to retrieve from the archive.")


class WorkflowGetAuditTrailInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    run_id: str | None = Field(None, description="Filter audit trail to a specific run ID. None returns all entries.")
    limit: int = Field(100, description="Maximum number of audit trail entries to return.")


class WorkflowRunPipelineInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    drawing_path: str = Field(..., description="Path to the DXF drawing to process through the full pipeline.")
    authority_code: str = Field(..., description="Local authority code for DCR rule evaluation.")
    output_dir: str = Field(..., description="Directory where all generated reports will be written.")
    dry_run: bool = Field(False, description="If true, run the pipeline without writing any output files.")

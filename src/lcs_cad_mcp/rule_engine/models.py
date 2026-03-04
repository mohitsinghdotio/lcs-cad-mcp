"""Pydantic v2 models for DCR rule configuration and rule evaluation results.

No imports from modules/, backends/, or session/ — stdlib and pydantic only.
"""
from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator, computed_field


class RuleType(str, Enum):
    """DCR rule dimension types."""
    FSI = "FSI"
    GROUND_COVERAGE = "GROUND_COVERAGE"
    SETBACK_FRONT = "SETBACK_FRONT"
    SETBACK_SIDE = "SETBACK_SIDE"
    SETBACK_REAR = "SETBACK_REAR"
    PARKING_RATIO = "PARKING_RATIO"
    HEIGHT_RESTRICTION = "HEIGHT_RESTRICTION"
    OPEN_SPACE = "OPEN_SPACE"


class DCRRule(BaseModel):
    """A single DCR compliance rule."""
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="Unique identifier for this rule.")
    name: str = Field(..., description="Human-readable name of the rule.")
    description: str = Field("", description="Detailed description of what this rule enforces.")
    rule_type: RuleType = Field(..., description="Category of DCR regulation.")
    threshold: float = Field(..., description="Permissible maximum (or minimum for setbacks).")
    unit: str = Field(..., description="Unit of the threshold value (e.g. 'sqm', 'm', 'ratio', '%').")
    zone_applicability: list[str] = Field(..., description="List of zone codes this rule applies to.")
    tolerance: float = Field(0.0, description="Allowable deviation before failure (same unit as threshold).")

    @field_validator("threshold")
    @classmethod
    def threshold_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"threshold must be >= 0, got {v}")
        return v

    @model_validator(mode="after")
    def zone_applicability_non_empty(self) -> DCRRule:
        if not self.zone_applicability:
            raise ValueError("zone_applicability must contain at least one zone code")
        return self


class DCRConfig(BaseModel):
    """Full DCR configuration for a local authority."""
    model_config = ConfigDict(frozen=True)

    version: str = Field(..., description="Config schema version string (semver).")
    authority: str = Field(..., description="Local authority name or code.")
    effective_date: str = Field(..., description="ISO 8601 date when this config became effective.")
    rules: list[DCRRule] = Field(..., description="Ordered list of DCR rules to evaluate.")
    metadata: dict[str, str] = Field(default_factory=dict, description="Optional key-value metadata.")

    @model_validator(mode="after")
    def validate_rules(self) -> DCRConfig:
        if not self.rules:
            raise ValueError("rules must contain at least one rule")
        ids = [r.rule_id for r in self.rules]
        if len(ids) != len(set(ids)):
            seen = set()
            dupes = [rid for rid in ids if rid in seen or seen.add(rid)]  # type: ignore[func-returns-value]
            raise ValueError(f"Duplicate rule_id values: {dupes}")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @computed_field  # type: ignore[misc]
    @property
    def zone_set(self) -> set[str]:
        zones: set[str] = set()
        for rule in self.rules:
            zones.update(rule.zone_applicability)
        return zones


class RuleResult(BaseModel):
    """Result of evaluating a single DCR rule against drawing metrics."""
    model_config = ConfigDict(frozen=True)

    rule_id: str = Field(..., description="ID of the rule that was evaluated.")
    rule_name: str = Field(..., description="Human-readable rule name.")
    passed: bool = Field(..., description="True if the rule was satisfied.")
    computed_value: float = Field(..., description="Actual computed value from the drawing.")
    permissible_value: float = Field(..., description="Maximum (or minimum) permitted by the rule.")
    deviation: float = Field(..., description="Computed - permissible (negative = under limit).")
    suggested_action: str = Field("", description="AI-readable corrective action hint.")
    tolerance: float = Field(0.0, description="Tolerance used when evaluating this rule.")

    @computed_field  # type: ignore[misc]
    @property
    def deviation_percent(self) -> float:
        if self.permissible_value == 0:
            return 0.0
        return abs(self.deviation) / self.permissible_value * 100

    @computed_field  # type: ignore[misc]
    @property
    def status(self) -> Literal["pass", "deviation", "fail"]:
        if self.passed:
            return "pass"
        if abs(self.deviation) <= self.tolerance:
            return "deviation"
        return "fail"


class ScrutinyReport(BaseModel):
    """Aggregated results from a full AutoDCR scrutiny run."""
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(..., description="Unique identifier for this scrutiny run.")
    drawing_path: str = Field(..., description="Path to the evaluated DXF drawing.")
    authority: str = Field(..., description="Authority code used for evaluation.")
    results: list[RuleResult] = Field(default_factory=list)
    overall_pass: bool = Field(..., description="True only if ALL rules passed.")
    total_rules: int = Field(..., description="Number of rules evaluated.")
    passed_rules: int = Field(..., description="Number of rules that passed.")
    failed_rules: int = Field(..., description="Number of rules that failed.")

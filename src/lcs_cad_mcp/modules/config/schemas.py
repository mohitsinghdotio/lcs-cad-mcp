"""Pydantic v2 input/output schemas for the config module."""
from pydantic import BaseModel, Field, ConfigDict


class ConfigLoadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    config_path: str = Field(..., description="Path to the DCR configuration YAML/JSON file to load.")


class ConfigValidateInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    config_path: str = Field(..., description="Path to the DCR configuration file to validate.")


class ConfigGetVersionInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)

    authority_code: str = Field(..., description="Local authority code to get DCR version for.")

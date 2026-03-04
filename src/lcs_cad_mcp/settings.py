from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    dcr_config_path: Path
    archive_path: Path
    cad_backend: Literal["ezdxf", "com"] = "ezdxf"
    log_level: str = "INFO"

    # Transport configuration (Story 1-3)
    mcp_transport: Literal["stdio", "sse"] = "stdio"
    mcp_sse_host: str = "127.0.0.1"
    mcp_sse_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

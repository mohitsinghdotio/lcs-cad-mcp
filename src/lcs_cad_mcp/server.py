"""FastMCP server instance and lifespan configuration."""
import sys
from contextlib import asynccontextmanager
from fastmcp import FastMCP
from lcs_cad_mcp.settings import Settings

__all__ = ["mcp"]


@asynccontextmanager
async def lifespan(app: FastMCP):
    """Server startup / teardown hook."""
    try:
        settings = Settings()
        print(f"lcs-cad-mcp starting — backend={settings.cad_backend}", file=sys.stderr, flush=True)
    except Exception:
        print("lcs-cad-mcp starting — (settings not configured)", file=sys.stderr, flush=True)
    yield
    # Future: clean up resources here


mcp = FastMCP(name="lcs-cad-mcp", version="0.1.0", lifespan=lifespan)

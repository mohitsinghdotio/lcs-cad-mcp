"""MCP server entrypoint — registers all module tools and starts transport."""
from lcs_cad_mcp.server import mcp
from lcs_cad_mcp.modules import (
    cad, predcr, layers, entities, verification,
    config, area, autodcr, reports, workflow,
)

_MODULES = [cad, predcr, layers, entities, verification, config, area, autodcr, reports, workflow]

for _mod in _MODULES:
    _mod.register(mcp)

if __name__ == "__main__":
    import sys
    from lcs_cad_mcp.settings import Settings
    settings = Settings()
    if settings.mcp_transport == "sse":
        print(
            f"Starting lcs-cad-mcp transport=sse "
            f"host={settings.mcp_sse_host} port={settings.mcp_sse_port}",
            file=sys.stderr, flush=True,
        )
        mcp.run(transport="sse", host=settings.mcp_sse_host, port=settings.mcp_sse_port)
    else:
        print("Starting lcs-cad-mcp transport=stdio", file=sys.stderr, flush=True)
        mcp.run(transport="stdio", show_banner=False)

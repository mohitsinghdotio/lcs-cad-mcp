FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev extras, no editable install)
RUN uv sync --frozen --no-dev --no-editable

# Copy source
COPY src/ src/
COPY dcr_configs/ dcr_configs/

# Install the project itself
RUN uv sync --frozen --no-dev

# Runtime volumes
VOLUME ["/data/archive", "/data/configs"]

EXPOSE 8000

ENV MCP_TRANSPORT=sse \
    MCP_SSE_HOST=0.0.0.0 \
    MCP_SSE_PORT=8000 \
    CAD_BACKEND=ezdxf \
    DCR_CONFIG_PATH=/data/configs/sample-residential.yaml \
    ARCHIVE_PATH=/data/archive \
    LOG_LEVEL=INFO

CMD ["uv", "run", "python", "-m", "lcs_cad_mcp"]

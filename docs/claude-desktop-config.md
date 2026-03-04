# Claude Desktop Configuration

Add this snippet to your `claude_desktop_config.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "lcs-cad-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "lcs_cad_mcp"],
      "env": {
        "DCR_CONFIG_PATH": "/path/to/your/dcr-rules.yaml",
        "ARCHIVE_PATH": "/path/to/your/archive",
        "CAD_BACKEND": "ezdxf"
      }
    }
  }
}
```

Replace paths as appropriate. After restarting Claude Desktop, the server appears and `cad_ping` is visible in the tools list.

**Integration test result:** Server connects; `cad_ping` tool visible (1 tool in current stub state).

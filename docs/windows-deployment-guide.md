# Windows Deployment Guide — LCS CAD MCP

Step-by-step guide for deploying `lcs-cad-mcp` on a Windows machine with AutoCAD installed.

> **Note on COM backend:** The AutoCAD COM backend (`CAD_BACKEND=com`) is scaffolded but not yet
> fully implemented. For production use, set `CAD_BACKEND=ezdxf` — it reads/writes `.dwg`/`.dxf`
> files directly without requiring AutoCAD to be running. The COM backend will be functional in a
> future release.

---

## Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| Windows | 10 / 11 (64-bit) | Required for COM backend (future) |
| AutoCAD | 2018 or later | Only needed when COM backend is active |
| Python | 3.11+ | Installed via `uv` (see Step 1) |
| `uv` | latest | Python package manager — replaces pip/venv |

---

## Step 1 — Install `uv`

Open **PowerShell** (no admin required):

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Restart PowerShell, then verify:

```powershell
uv --version
```

---

## Step 2 — Get the Project

Clone the repository (or copy it to a local folder):

```powershell
git clone https://github.com/mohitsinghdotio/lcs-cad-mcp.git
cd lcs-cad-mcp
```

If you don't have Git:
- Download as ZIP from GitHub → extract to `C:\lcs-cad-mcp\`
- Open PowerShell and `cd C:\lcs-cad-mcp`

---

## Step 3 — Install Dependencies

```powershell
uv sync
```

This creates a `.venv` inside the project folder and installs all dependencies.

**If you plan to use the COM backend in the future**, also install `pywin32`:

```powershell
uv run pip install pywin32
```

---

## Step 4 — Prepare Folders

Create folders for DCR config files and archive storage:

```powershell
mkdir C:\lcs-cad-mcp\configs
mkdir C:\lcs-cad-mcp\archive
```

Copy the sample config to use as a starting point:

```powershell
copy dcr_configs\sample-residential.yaml C:\lcs-cad-mcp\configs\dcr-rules.yaml
```

Edit `C:\lcs-cad-mcp\configs\dcr-rules.yaml` to match your authority's actual DCR rules.

---

## Step 5 — Create the `.env` File

In the project root, create a file named `.env`:

```powershell
copy .env.example .env
notepad .env
```

Set the values — use Windows backslashes or forward slashes (both work):

```env
# Required
DCR_CONFIG_PATH=C:/lcs-cad-mcp/configs/dcr-rules.yaml
ARCHIVE_PATH=C:/lcs-cad-mcp/archive

# Use 'ezdxf' (recommended). Switch to 'com' only after COM backend is implemented.
CAD_BACKEND=ezdxf

# Transport: 'stdio' for Claude Desktop/Code (recommended for local use)
# Use 'sse' only if exposing the server to other machines on the network
MCP_TRANSPORT=stdio
```

---

## Step 6 — Verify the Server Starts

```powershell
uv run python -m lcs_cad_mcp
```

Expected stderr output (startup messages go to stderr, not stdout):
```
Starting lcs-cad-mcp transport=stdio
lcs-cad-mcp starting — backend=ezdxf
```

The process will wait silently for MCP client input — that is normal for stdio mode.
Press `Ctrl+C` to stop.

---

## Step 7 — Connect to Claude Desktop

Locate the Claude Desktop config file:

```
%APPDATA%\Claude\claude_desktop_config.json
```

Open it in Notepad (or VS Code). Add the `lcs-cad-mcp` entry under `mcpServers`:

```json
{
  "mcpServers": {
    "lcs-cad-mcp": {
      "command": "C:\\Users\\<YourUsername>\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--project", "C:\\lcs-cad-mcp",
        "python", "-m", "lcs_cad_mcp"
      ],
      "env": {
        "DCR_CONFIG_PATH": "C:\\lcs-cad-mcp\\configs\\dcr-rules.yaml",
        "ARCHIVE_PATH":    "C:\\lcs-cad-mcp\\archive",
        "CAD_BACKEND":     "ezdxf",
        "MCP_TRANSPORT":   "stdio"
      }
    }
  }
}
```

> **Important:** Replace `<YourUsername>` with your actual Windows username.
> Claude Desktop uses a restricted PATH — `"uv"` alone will not be found. You must use the full path to `uv.exe`.

To find your exact `uv.exe` path, run in PowerShell:
```powershell
(Get-Command uv).Source
```

> Use double backslashes (`\\`) inside JSON strings.

**Restart Claude Desktop.** The server should connect automatically on launch.

To confirm: open Claude Desktop → click the tools icon → you should see `cad_ping` and the other LCS tools listed.

---

## Step 8 — Connect to Claude Code (CLI)

In your shell profile or directly in the terminal, add the MCP server:

```powershell
claude mcp add lcs-cad-mcp `
  --command uv `
  --args "--project C:\lcs-cad-mcp run python -m lcs_cad_mcp" `
  --env DCR_CONFIG_PATH=C:\lcs-cad-mcp\configs\dcr-rules.yaml `
  --env ARCHIVE_PATH=C:\lcs-cad-mcp\archive `
  --env CAD_BACKEND=ezdxf
```

Or edit `%APPDATA%\Claude\claude_code_config.json` directly with the same JSON structure as Step 7.

---

## Optional — SSE Transport (multi-client / remote)

Use this if you want the server accessible from multiple machines on a LAN.

In `.env`:
```env
MCP_TRANSPORT=sse
MCP_SSE_HOST=0.0.0.0
MCP_SSE_PORT=8000
```

Start the server:
```powershell
uv run python -m lcs_cad_mcp
# → Starting lcs-cad-mcp transport=sse host=0.0.0.0 port=8000
```

Clients connect to: `http://<your-machine-ip>:8000/sse`

To run as a background Windows service, use [NSSM](https://nssm.cc/):
```powershell
nssm install lcs-cad-mcp "C:\Users\<you>\.local\bin\uv.exe" `
  "run --project C:\lcs-cad-mcp python -m lcs_cad_mcp"
nssm set lcs-cad-mcp AppEnvironmentExtra DCR_CONFIG_PATH=C:\lcs-cad-mcp\configs\dcr-rules.yaml
nssm set lcs-cad-mcp AppEnvironmentExtra ARCHIVE_PATH=C:\lcs-cad-mcp\archive
nssm set lcs-cad-mcp AppEnvironmentExtra MCP_TRANSPORT=sse
nssm start lcs-cad-mcp
```

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| `uv: command not found` | uv not on PATH | Restart PowerShell after install |
| `DCR_CONFIG_PATH` not found error | Path typo in `.env` or JSON | Verify the path exists; use forward slashes |
| Claude Desktop shows no tools | Config JSON syntax error | Validate JSON at jsonlint.com |
| `ModuleNotFoundError: win32com` | pywin32 not installed | `uv run pip install pywin32` |
| COM backend raises `BACKEND_UNAVAILABLE` | Not yet implemented | Set `CAD_BACKEND=ezdxf` — COM is a future feature |
| Server exits immediately in stdio | No client connected | Normal — stdio mode waits for MCP client input |

---

## File Layout After Setup

```
C:\lcs-cad-mcp\
├── .env                          ← your settings
├── configs\
│   └── dcr-rules.yaml            ← your DCR rule config
├── archive\                      ← auto-created submission archive
├── src\lcs_cad_mcp\              ← server source
└── .venv\                        ← Python environment (auto-created by uv)
```

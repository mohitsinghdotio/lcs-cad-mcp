"""CAD backend package — self-registers available backends with BackendFactory."""
from __future__ import annotations

import sys

from lcs_cad_mcp.backends.base import CADBackend, BackendFactory, DrawingMetadata, LayerInfo, EntityInfo

# Register ezdxf backend (cross-platform)
try:
    from lcs_cad_mcp.backends.ezdxf_backend import EzdxfBackend
    BackendFactory.register("ezdxf", EzdxfBackend)
except ImportError:
    pass

# Register COM backend (Windows only)
if sys.platform == "win32":
    try:
        from lcs_cad_mcp.backends.com_backend import COMBackend
        BackendFactory.register("com", COMBackend)
    except ImportError:
        pass

__all__ = ["CADBackend", "BackendFactory", "DrawingMetadata", "LayerInfo", "EntityInfo"]

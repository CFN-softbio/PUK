"""MCP server for interatomic potential management."""

import os
import json
from mcp.server.fastmcp import FastMCP

from potential_manager import (
    download_potential as _download_potential,
    download_from_openkim as _download_from_openkim,
    create_sw_potential as _create_sw_potential,
    validate_potential as _validate_potential,
    list_potential_files as _list_potential_files,
    list_available_sources as _list_available_sources,
)

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")

mcp = FastMCP("lammps-potential")


@mcp.tool()
def download_potential(
    element: str,
    potential_type: str = "eam",
    custom_url: str | None = None,
) -> str:
    """Download an interatomic potential for an element.

    Searches GitHub LAMMPS repo and OpenKIM with auto-fallback.
    Handles both direct files and archives (.txz, .tar.gz, .zip).

    Args:
        element: Chemical element symbol (e.g. Cu, Au, Si)
        potential_type: Potential type: eam, sw, tersoff, meam (default "eam")
        custom_url: Optional direct URL to download from

    Returns:
        JSON with success, filepath, filename, source, file_size, error
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        r = _download_potential(element, potential_type, custom_url, workspace)
        return json.dumps({
            "success": r.success,
            "filepath": r.filepath,
            "filename": r.filename,
            "source": r.source,
            "file_size": r.file_size,
            "error": r.error,
            "alternatives": r.alternatives,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def download_from_openkim(
    kim_model_id: str,
    element: str | None = None,
) -> str:
    """Download an interatomic potential from OpenKIM by model ID.

    Args:
        kim_model_id: OpenKIM model ID (e.g. EAM_Dynamo_GolaPastewka_2018_CuAu__MO_426403318662_000)
        element: Optional element symbol to help identify the best file in the archive

    Returns:
        JSON with success, filepath, filename, source, file_size, error
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        r = _download_from_openkim(kim_model_id, element, workspace)
        return json.dumps({
            "success": r.success,
            "filepath": r.filepath,
            "filename": r.filename,
            "source": r.source,
            "file_size": r.file_size,
            "error": r.error,
            "alternatives": r.alternatives,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def create_sw_potential(element: str) -> str:
    """Generate a Stillinger-Weber potential file from built-in parameters.

    Available elements: Si, Ge, C.

    Args:
        element: Element symbol (Si, Ge, or C)

    Returns:
        JSON with success, filepath, filename, file_size, error
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        r = _create_sw_potential(element, workspace)
        return json.dumps({
            "success": r.success,
            "filepath": r.filepath,
            "filename": r.filename,
            "source": r.source,
            "file_size": r.file_size,
            "error": r.error,
        })
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def validate_potential(filepath: str, element: str | None = None) -> str:
    """Validate an interatomic potential file.

    Performs format-specific checks: EAM header parsing, SW parameter verification,
    MEAM keyword detection, Tersoff field count, and dummy content detection.

    Args:
        filepath: Path to potential file (absolute or relative to workspace)
        element: Optional element symbol for context-aware validation

    Returns:
        JSON with valid, format, message, details
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        r = _validate_potential(filepath, element, workspace)
        return json.dumps({
            "valid": r.valid,
            "format": r.format,
            "message": r.message,
            "details": r.details,
        })
    except Exception as e:
        return json.dumps({"valid": False, "error": str(e)})


@mcp.tool()
def list_potential_files() -> str:
    """List all potential files in the workspace.

    Returns:
        JSON with files array containing name and size_bytes for each file
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        files = _list_potential_files(workspace)
        return json.dumps({"files": files})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_available_sources(element: str | None = None) -> str:
    """Show known download URLs and sources for an element.

    Args:
        element: Element symbol (e.g. Cu). If omitted, shows all elements.

    Returns:
        JSON with known sources, GitHub files, and SW generation availability
    """
    try:
        result = _list_available_sources(element)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()

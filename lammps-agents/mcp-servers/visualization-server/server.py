"""MCP server for LAMMPS visualization — OVITO rendering and matplotlib plots."""

import os
import json
from mcp.server.fastmcp import FastMCP

from ovito_renderer import (
    render_dump_frame as _render_dump_frame,
    render_multiple_frames as _render_multiple_frames,
    create_dump_animation as _create_dump_animation,
    analyze_dump_file as _analyze_dump_file,
)
from plot_elastic import plot_elastic_constants as _plot_elastic_constants
from plot_melting import plot_melting_analysis as _plot_melting_analysis

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")

mcp = FastMCP("lammps-visualization")


# ── OVITO tools ──────────────────────────────────────────────────────────────

@mcp.tool()
def render_dump_frame(dump_file: str, output_image: str = "frame.png",
                      frame_number: str = "last",
                      image_width: int = 1600, image_height: int = 1200) -> str:
    """Render a single frame from a LAMMPS dump file to PNG using OVITO.

    Args:
        dump_file: Dump file name in workspace (e.g. dump.output)
        output_image: Output PNG filename (default: frame.png)
        frame_number: Frame index or "last" (default: last)
        image_width: Image width in pixels (default: 1600)
        image_height: Image height in pixels (default: 1200)

    Returns:
        JSON with success, filepath, frame_rendered, total_frames, atom_count
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _render_dump_frame(workspace, dump_file, output_image,
                                     frame_number, image_width, image_height)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def render_multiple_frames(dump_file: str, frame_count: int = 5,
                            output_prefix: str = "frame",
                            image_width: int = 1600, image_height: int = 1200) -> str:
    """Render multiple evenly-spaced frames from a LAMMPS dump file to PNGs.

    Args:
        dump_file: Dump file name in workspace
        frame_count: Number of frames to render (default: 5)
        output_prefix: Prefix for output filenames (default: frame)
        image_width: Image width in pixels (default: 1600)
        image_height: Image height in pixels (default: 1200)

    Returns:
        JSON with success, rendered_frames, failed_frames, counts
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _render_multiple_frames(workspace, dump_file, frame_count,
                                          output_prefix, image_width, image_height)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def create_dump_animation(dump_file: str, output_gif: str = "animation.gif",
                           frame_count: int = 10, duration: float = 0.5) -> str:
    """Create a GIF animation from LAMMPS dump file frames.

    Args:
        dump_file: Dump file name in workspace
        output_gif: Output GIF filename (default: animation.gif)
        frame_count: Number of frames to include (default: 10)
        duration: Duration per frame in seconds (default: 0.5)

    Returns:
        JSON with success, filepath, frame_count_used, file_size
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _create_dump_animation(workspace, dump_file, output_gif,
                                         frame_count, duration)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def analyze_dump_file(dump_file: str) -> str:
    """Extract metadata from a LAMMPS dump file (frames, atoms, box, properties).

    Falls back to text parsing if OVITO is not available.

    Args:
        dump_file: Dump file name in workspace (e.g. dump.output)

    Returns:
        JSON with total_frames, atom_count, box_dimensions, particle_properties
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _analyze_dump_file(workspace, dump_file)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Matplotlib tools ─────────────────────────────────────────────────────────

@mcp.tool()
def plot_elastic_constants(matrix_file: str = "elastic_matrix.txt",
                           output_image: str = "elastic_constants_visualization.png") -> str:
    """Create a 6x6 elastic constants heatmap from an elastic matrix file.

    The matrix file should contain a 6x6 space-separated matrix of Cij values in GPa.

    Args:
        matrix_file: Input matrix filename (default: elastic_matrix.txt)
        output_image: Output PNG filename (default: elastic_constants_visualization.png)

    Returns:
        JSON with success, filepath, file_size, matrix_shape
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _plot_elastic_constants(workspace, matrix_file, output_image)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def plot_melting_analysis(log_file: str = "log.lammps",
                          output_image: str = "melting_analysis.png",
                          plot_style: str = "simple",
                          system_name: str = None,
                          num_atoms: int = None,
                          material: str = None) -> str:
    """Create melting point analysis plots from a LAMMPS log file.

    Parses thermo output (Step/Temp/PE columns), computes binned heat capacity,
    and identifies melting temperature from heat capacity peak.

    Args:
        log_file: LAMMPS log or output file (default: log.lammps)
        output_image: Output PNG filename (default: melting_analysis.png)
        plot_style: "simple" (2-panel) or "comprehensive" (4-panel with summary)
        system_name: Optional system description (for comprehensive style)
        num_atoms: Optional atom count (for comprehensive style)
        material: Optional material name (for comprehensive style)

    Returns:
        JSON with success, filepath, data_points, melting_estimates, temperature_range
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = _plot_melting_analysis(workspace, log_file, output_image,
                                         plot_style, system_name, num_atoms, material)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ── Utility ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_visualization_files() -> str:
    """List all image files (PNG, GIF, JPG) in the workspace.

    Returns:
        JSON with files array containing name and size_bytes for each file
    """
    workspace = os.path.abspath(WORKSPACE)
    extensions = {".png", ".gif", ".jpg", ".jpeg"}

    try:
        files = []
        if os.path.isdir(workspace):
            for entry in sorted(os.listdir(workspace)):
                if os.path.splitext(entry)[1].lower() in extensions:
                    full = os.path.join(workspace, entry)
                    files.append({"name": entry, "size_bytes": os.path.getsize(full)})
        return json.dumps({"files": files, "count": len(files)})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


if __name__ == "__main__":
    mcp.run()

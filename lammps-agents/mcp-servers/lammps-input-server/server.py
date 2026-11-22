"""MCP server for LAMMPS input script generation."""

import os
import json
from mcp.server.fastmcp import FastMCP

from input_generator import (
    generate_lattice_constants,
    generate_elastic_constants,
    generate_melting_point,
    list_input_files,
)

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")

mcp = FastMCP("lammps-input")


@mcp.tool()
def generate_lattice_constants_input(
    structure_file: str,
    potential_file: str,
    elements: str,
    potential_type: str | None = None,
    output_filename: str | None = None,
) -> str:
    """Generate LAMMPS input script for lattice constants and cohesive energy.

    Args:
        structure_file: Structure file name (e.g. cu_structure.lmp)
        potential_file: Potential file name (e.g. Cu_u3.eam)
        elements: Space-separated element symbols (e.g. "Cu" or "Cu Zn")
        potential_type: Potential type: eam, eam_alloy, sw, tersoff, meam (auto-detected if omitted)
        output_filename: Output filename (default: in.lattice_constants)

    Returns:
        JSON with filepath, filename, simulation_type, potential_type, files_created
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        result = generate_lattice_constants(
            structure_file=structure_file,
            potential_file=potential_file,
            elements=elements,
            workspace=workspace,
            potential_type=potential_type,
            output_filename=output_filename,
        )
        return json.dumps(result)
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def generate_elastic_constants_input(
    structure_file: str,
    potential_file: str,
    elements: str,
    potential_type: str | None = None,
) -> str:
    """Generate LAMMPS input files for elastic constants calculation (6x6 stiffness tensor).

    Creates 4 files: in.elastic, init.mod, potential.mod, displace.mod

    Args:
        structure_file: Structure file name (e.g. cu_structure.lmp)
        potential_file: Potential file name (e.g. Cu_u3.eam)
        elements: Space-separated element symbols (e.g. "Cu")
        potential_type: Potential type: eam, eam_alloy, sw, tersoff, meam (auto-detected if omitted)

    Returns:
        JSON with filepath, filename, simulation_type, potential_type, files_created
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        result = generate_elastic_constants(
            structure_file=structure_file,
            potential_file=potential_file,
            elements=elements,
            workspace=workspace,
            potential_type=potential_type,
        )
        return json.dumps(result)
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def generate_melting_point_input(
    structure_file: str,
    potential_file: str,
    elements: str,
    estimated_melting_point: float,
    potential_type: str | None = None,
    supercell_z: int = 3,
) -> str:
    """Generate LAMMPS input files for melting point calculation via solid-liquid coexistence.

    Creates 3 sequential scripts: in.melt_relax, in.melt_interface, in.melt_coexist

    Args:
        structure_file: Structure file name (e.g. cu_structure.lmp)
        potential_file: Potential file name (e.g. Cu_u3.eam)
        elements: Space-separated element symbols (e.g. "Cu")
        estimated_melting_point: Estimated melting point in Kelvin
        potential_type: Potential type: eam, eam_alloy, sw, tersoff, meam (auto-detected if omitted)
        supercell_z: Z-direction replication for interface (default 3)

    Returns:
        JSON with filepath, simulation_type, potential_type, files_created, run_order
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        result = generate_melting_point(
            structure_file=structure_file,
            potential_file=potential_file,
            elements=elements,
            estimated_melting_point=estimated_melting_point,
            workspace=workspace,
            potential_type=potential_type,
            supercell_z=supercell_z,
        )
        return json.dumps(result)
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_input_files_tool() -> str:
    """List all LAMMPS input (.in) and module (.mod) files in the workspace.

    Returns:
        JSON with files array containing name and size_bytes for each file
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        files = list_input_files(workspace)
        return json.dumps({"files": files})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()

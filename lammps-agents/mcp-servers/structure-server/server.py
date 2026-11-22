"""MCP server for crystal structure creation using atomsk."""

import os
import json
from mcp.server.fastmcp import FastMCP

from structure_manager import (
    create_crystal_structure,
    create_alloy_structure,
    list_structures,
)

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")
ATOMSK = os.environ.get("ATOMSK_PATH", "atomsk")

mcp = FastMCP("lammps-structure")


@mcp.tool()
def create_crystal(
    element: str,
    crystal_type: str,
    lattice_param: float,
    size: str = "10 10 10",
    output_format: str = "lammps",
) -> str:
    """Create a crystal structure file using atomsk.

    Args:
        element: Chemical element symbol (e.g. Au, Cu, Fe, Si)
        crystal_type: Crystal structure type: fcc, bcc, hcp, diamond, or sc
        lattice_param: Lattice parameter in Angstroms
        size: Supercell duplication as 3 space-separated integers (e.g. "10 10 10")
        output_format: Output file format, default "lammps" (.lmp)

    Returns:
        JSON with filepath, atom_count, file_size, crystal_type, lattice_param
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        result = create_crystal_structure(
            element=element,
            crystal_type=crystal_type,
            lattice_param=lattice_param,
            size=size,
            output_format=output_format,
            workspace=workspace,
            atomsk_path=ATOMSK,
        )
        return json.dumps({
            "filepath": result.filepath,
            "atom_count": result.atom_count,
            "file_size": result.file_size,
            "crystal_type": result.crystal_type,
            "lattice_param": result.lattice_param,
        })
    except (ValueError, RuntimeError) as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def create_alloy(
    base_element: str,
    alloy_element: str,
    crystal_type: str,
    lattice_param: float,
    alloy_fraction: float,
    size: str = "10 10 10",
    output_filename: str | None = None,
) -> str:
    """Create a random alloy structure by substituting atoms in a base crystal.

    Args:
        base_element: Base element symbol (e.g. Cu)
        alloy_element: Alloying element symbol (e.g. Zn)
        crystal_type: Crystal structure type: fcc, bcc, hcp, diamond, or sc
        lattice_param: Lattice parameter in Angstroms
        alloy_fraction: Fraction of atoms to substitute (0 to 1, exclusive)
        size: Supercell duplication as 3 space-separated integers (e.g. "10 10 10")
        output_filename: Optional output filename (default: auto-generated)

    Returns:
        JSON with filepath, atom_count, base_element, alloy_element, fraction
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        result = create_alloy_structure(
            base_element=base_element,
            alloy_element=alloy_element,
            crystal_type=crystal_type,
            lattice_param=lattice_param,
            size=size,
            alloy_fraction=alloy_fraction,
            workspace=workspace,
            atomsk_path=ATOMSK,
            output_filename=output_filename,
        )
        return json.dumps({
            "filepath": result.filepath,
            "atom_count": result.atom_count,
            "base_element": result.base_element,
            "alloy_element": result.alloy_element,
            "fraction": result.fraction,
        })
    except (ValueError, RuntimeError) as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_structure_files() -> str:
    """List all structure files (.lmp, .cfg, .xyz) in the workspace.

    Returns:
        JSON with files array containing name, size_bytes, atom_count for each file
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        files = list_structures(workspace)
        return json.dumps({"files": files})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()

"""MCP server for LAMMPS results parsing and analysis."""

import os
import json
from mcp.server.fastmcp import FastMCP

from log_parser import (
    parse_general,
    parse_lattice_constants,
    parse_elastic_constants,
    list_results,
)

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")

mcp = FastMCP("lammps-results")


@mcp.tool()
def parse_lammps_log(log_file: str) -> str:
    """Parse general information from a LAMMPS log file.

    Extracts: LAMMPS version, atom count, warnings, errors, wall time,
    and thermo block metadata (column names, row count, step range).

    Args:
        log_file: Log file name in workspace (e.g. in.lattice_constants.log)

    Returns:
        JSON with version, atom_count, warnings, errors, wall_time, thermo_blocks
    """
    workspace = os.path.abspath(WORKSPACE)
    filepath = os.path.join(workspace, log_file)
    try:
        result = parse_general(filepath)
        return json.dumps(result)
    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def extract_lattice_constants(log_file: str, supercell_size: int = 10) -> str:
    """Extract lattice constants and cohesive energy from a LAMMPS log file.

    Parses the delimited "Lattice Constants and Cohesive Energy" section.
    Returns cohesive energy, cell dimensions, angles, and derived per-unit-cell
    lattice parameters (cell dimension / supercell_size).

    Args:
        log_file: Log file name in workspace (e.g. in.lattice_constants.log)
        supercell_size: Supercell replication factor (default 10)

    Returns:
        JSON with cohesive_energy_eV_per_atom, cell_dimensions, cell_angles, lattice_parameters
    """
    workspace = os.path.abspath(WORKSPACE)
    filepath = os.path.join(workspace, log_file)
    try:
        result = parse_lattice_constants(filepath, supercell_size)
        return json.dumps(result)
    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def extract_elastic_constants(log_file: str) -> str:
    """Extract elastic constants tensor and derived properties from a LAMMPS log file.

    Parses the delimited "Components of the Elastic Constant Tensor" and
    "Average properties for a cubic crystal" sections.

    Args:
        log_file: Log file name in workspace (e.g. in.elastic.log)

    Returns:
        JSON with elastic_constants_GPa (21 Cij values), derived_properties
        (bulk_modulus, shear_moduli, poisson_ratio)
    """
    workspace = os.path.abspath(WORKSPACE)
    filepath = os.path.join(workspace, log_file)
    try:
        result = parse_elastic_constants(filepath)
        return json.dumps(result)
    except FileNotFoundError as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def list_results_files() -> str:
    """Categorize all files in the workspace by type.

    Classifies files into: logs, structures, potentials, inputs, data_files, dumps, other.

    Returns:
        JSON with categorized file listings (name, size_bytes per file)
    """
    workspace = os.path.abspath(WORKSPACE)
    try:
        result = list_results(workspace)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


if __name__ == "__main__":
    mcp.run()

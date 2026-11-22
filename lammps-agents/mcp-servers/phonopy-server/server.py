"""MCP server for phonon dispersion calculations via phonopy."""

import os
import json
from mcp.server.fastmcp import FastMCP

from phonopy_manager import (
    setup_phonon_calculation,
    run_phonon_force_calculations,
    generate_phonon_dispersion,
    list_phonon_files,
)

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")
LAMMPS_PATH = os.environ.get("LAMMPS_PATH", "lmp")
PHONOPY_PATH = os.environ.get("PHONOPY_PATH", "phonopy")

mcp = FastMCP("phonopy-server")


@mcp.tool()
def setup_phonon_calculation_tool(
    structure_file: str,
    potential_file: str,
    elements: str,
    dim: str = "3 3 3",
    potential_type: str | None = None,
) -> str:
    """Set up phonon displacement calculations.

    Removes phonon files from any previous run, converts the LAMMPS structure to
    POSCAR, generates displacements with phonopy, and creates per-displacement
    directories with LAMMPS input files.

    Args:
        structure_file: Structure file name (e.g. cu_structure.lmp)
        potential_file: Potential file name (e.g. Cu_u3.eam). For single-element funcfl
            EAM files on an alloy, give one file per element in the order of `elements`
            (e.g. "Ni_u3.eam Cu_u3.eam"); cross terms come from LAMMPS mixing.
        elements: Space-separated element symbols, in LAMMPS atom-type order (e.g. "Cu" or "Ni Cu")
        dim: Supercell dimensions for phonopy (default "3 3 3")
        potential_type: Potential type override: eam, eam_alloy, sw, tersoff, meam (auto-detected if omitted)

    Returns:
        JSON with success, displacement_count, potential_type, directories_created
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = setup_phonon_calculation(
        workspace=workspace,
        structure_file=structure_file,
        potential_file=potential_file,
        elements=elements,
        dim=dim,
        potential_type=potential_type,
        phonopy_path=PHONOPY_PATH,
    )
    return json.dumps(result)


@mcp.tool()
def run_phonon_force_calculations_tool(
    timeout_per_displacement: int = 300,
) -> str:
    """Run LAMMPS force calculations on all displacement directories.

    Executes LAMMPS on each disp-XXX/in.forces, then runs phonopy to
    collect forces into FORCE_SETS.

    Args:
        timeout_per_displacement: Timeout per LAMMPS run in seconds (default 300)

    Returns:
        JSON with success, total, completed, failed, force_sets_created
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = run_phonon_force_calculations(
        workspace=workspace,
        lammps_path=LAMMPS_PATH,
        phonopy_path=PHONOPY_PATH,
        timeout_per_displacement=timeout_per_displacement,
    )
    return json.dumps(result)


@mcp.tool()
def generate_phonon_dispersion_tool(
    npoints: int = 101,
) -> str:
    """Generate phonon band structure from POSCAR and FORCE_SETS.

    Detects the lattice from POSCAR (conventional FCC/BCC cells are reduced to the
    primitive cell and use the standard Γ-X-W-K-Γ-L-U / Γ-H-N-Γ-P-H paths), writes
    band.conf, and runs phonopy to produce band.yaml/band.dat/band.pdf.

    Args:
        npoints: Number of k-points along each segment (default 101)

    Returns:
        JSON with success, crystal_system, lattice_type, lattice_params, kpoint_path, files_created
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = generate_phonon_dispersion(
        workspace=workspace,
        phonopy_path=PHONOPY_PATH,
        npoints=npoints,
    )
    return json.dumps(result)


@mcp.tool()
def list_phonon_files_tool() -> str:
    """List all phonon-related files in the workspace.

    Scans for POSCAR files, displacement directories, FORCE_SETS, and band files.

    Returns:
        JSON with setup_files, displacement_dirs, force_data, band_files
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = list_phonon_files(workspace)
    return json.dumps(result)


if __name__ == "__main__":
    mcp.run()

"""MCP server for LAMMPS execution."""

import os
import json
from mcp.server.fastmcp import FastMCP

from executor import run_lammps, run_lammps_batch, list_log_files

WORKSPACE = os.environ.get("WORKSPACE_DIR", "./workspace")
LAMMPS_PATH = os.environ.get("LAMMPS_PATH", "lmp")

mcp = FastMCP("lammps-executor")


@mcp.tool()
def run_lammps_simulation(
    input_file: str,
    timeout: int = 6000,
    log_file: str | None = None,
) -> str:
    """Run a LAMMPS input file and return execution results.

    Args:
        input_file: Input file name in workspace (e.g. in.lattice_constants)
        timeout: Timeout in seconds (default 6000)
        log_file: Optional log file name (default: {input_file}.log)

    Returns:
        JSON with success, exit_code, log_file, output_tail, errors
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = run_lammps(
        input_file=input_file,
        workspace=workspace,
        lammps_path=LAMMPS_PATH,
        timeout=timeout,
        log_file=log_file,
    )
    return json.dumps(result)


@mcp.tool()
def run_lammps_batch_simulation(
    input_files: list[str],
    timeout_per_file: int = 6000,
) -> str:
    """Run multiple LAMMPS input files sequentially.

    Useful for multi-stage simulations like melting point (relax, interface, coexist).

    Args:
        input_files: List of input file names to run in order
        timeout_per_file: Timeout per file in seconds (default 6000)

    Returns:
        JSON with per-file results and summary (total, succeeded, failed)
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    result = run_lammps_batch(
        input_files=input_files,
        workspace=workspace,
        lammps_path=LAMMPS_PATH,
        timeout_per_file=timeout_per_file,
    )
    return json.dumps(result)


@mcp.tool()
def list_lammps_log_files() -> str:
    """List all LAMMPS log (.log) and output (.out) files in the workspace.

    Returns:
        JSON with files array containing name and size_bytes for each file
    """
    workspace = os.path.abspath(WORKSPACE)
    os.makedirs(workspace, exist_ok=True)
    try:
        files = list_log_files(workspace)
        return json.dumps({"files": files})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run()

"""LAMMPS subprocess execution logic."""

import os
import subprocess


def run_lammps(
    input_file: str,
    workspace: str,
    lammps_path: str = "lmp",
    timeout: int = 6000,
    log_file: str | None = None,
) -> dict:
    """Run a LAMMPS input file via subprocess.

    Args:
        input_file: Input file name (relative to workspace).
        workspace: Absolute path to workspace directory.
        lammps_path: Path to LAMMPS executable.
        timeout: Timeout in seconds.
        log_file: Optional log file name. Defaults to {input_file}.log.

    Returns:
        Dict with success, exit_code, log_file, output_tail, errors.
    """
    input_path = os.path.join(workspace, input_file)
    if not os.path.isfile(input_path):
        return {
            "success": False,
            "exit_code": -1,
            "log_file": None,
            "output_tail": "",
            "errors": f"Input file not found: {input_file}",
        }

    if log_file is None:
        log_file = f"{input_file}.log"
    log_path = os.path.join(workspace, log_file)

    try:
        result = subprocess.run(
            [lammps_path, "-in", input_file],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # Write full stdout to log file
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)

        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "log_file": log_file,
            "output_tail": result.stdout[-2000:] if result.stdout else "",
            "errors": result.stderr[-1000:] if result.stderr else "",
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "log_file": log_file,
            "output_tail": "",
            "errors": f"LAMMPS execution timed out after {timeout}s",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "exit_code": -1,
            "log_file": None,
            "output_tail": "",
            "errors": f"LAMMPS executable not found: {lammps_path}",
        }
    except Exception as e:
        return {
            "success": False,
            "exit_code": -1,
            "log_file": log_file,
            "output_tail": "",
            "errors": str(e),
        }


def run_lammps_batch(
    input_files: list[str],
    workspace: str,
    lammps_path: str = "lmp",
    timeout_per_file: int = 6000,
) -> dict:
    """Run multiple LAMMPS input files sequentially.

    Args:
        input_files: List of input file names.
        workspace: Absolute path to workspace directory.
        lammps_path: Path to LAMMPS executable.
        timeout_per_file: Timeout per file in seconds.

    Returns:
        Dict with results array and summary (total, succeeded, failed).
    """
    results = []
    succeeded = 0
    failed = 0

    for input_file in input_files:
        result = run_lammps(
            input_file=input_file,
            workspace=workspace,
            lammps_path=lammps_path,
            timeout=timeout_per_file,
        )
        results.append({"input_file": input_file, **result})
        if result["success"]:
            succeeded += 1
        else:
            failed += 1

    return {
        "results": results,
        "summary": {
            "total": len(input_files),
            "succeeded": succeeded,
            "failed": failed,
        },
    }


def list_log_files(workspace: str) -> list[dict]:
    """List .log and .out files in workspace.

    Args:
        workspace: Absolute path to workspace directory.

    Returns:
        List of dicts with name and size_bytes.
    """
    files = []
    for name in sorted(os.listdir(workspace)):
        if name.endswith((".log", ".out")):
            path = os.path.join(workspace, name)
            if os.path.isfile(path):
                files.append({
                    "name": name,
                    "size_bytes": os.path.getsize(path),
                })
    return files

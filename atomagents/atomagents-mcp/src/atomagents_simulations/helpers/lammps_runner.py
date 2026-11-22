"""LAMMPS execution via subprocess — supports both lmp binary and Python bindings."""

import os
import shutil
import subprocess


def _find_lammps_binary():
    """Find the LAMMPS executable."""
    for name in ("lmp", "lmp_mpi", "lmp_serial"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _has_python_lammps():
    """Check if the Python lammps module is importable."""
    try:
        import lammps
        return True
    except ImportError:
        return False


def run_lammps(script_or_input: str, num_cpus: int = 4, timeout: int = 3600,
               log_path: str = None, extra_args: str = None):
    """Run a LAMMPS simulation.

    Automatically detects whether to use the lmp binary directly or the
    Python LAMMPS bindings via mpirun.

    Args:
        script_or_input: Either a LAMMPS input file (.in) or a Python script (.py)
            that uses the lammps Python module.
        num_cpus: Number of MPI processes.
        timeout: Maximum runtime in seconds.
        log_path: Path for the LAMMPS log file (used with binary mode).
        extra_args: Extra arguments (e.g. '-partition 10x2' for NEB).

    Returns:
        subprocess.CompletedProcess result.
    """
    lmp_binary = _find_lammps_binary()

    if script_or_input.endswith('.in'):
        # Direct binary mode — preferred
        if lmp_binary is None:
            raise RuntimeError("No LAMMPS binary (lmp, lmp_mpi, lmp_serial) found in PATH")

        cmd_parts = [f'mpirun -np {num_cpus}', lmp_binary, f'-in {script_or_input}']
        if log_path:
            cmd_parts.append(f'-log {log_path}')
        if extra_args:
            cmd_parts.append(extra_args)

        command = ' '.join(cmd_parts)
    else:
        # Python binding mode (legacy)
        command = f'mpirun -np {num_cpus} python {script_or_input}'

    result = subprocess.run(
        command, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout
    )
    return result


def run_lammps_input(input_file: str, log_path: str, num_cpus: int = 4,
                     timeout: int = 3600, extra_args: str = None):
    """Run a LAMMPS input file directly using the lmp binary.

    This is the preferred method — it avoids the Python lammps module dependency.

    Args:
        input_file: Path to LAMMPS input script (.in file).
        log_path: Path for the LAMMPS log file.
        num_cpus: Number of MPI processes.
        timeout: Maximum runtime in seconds.
        extra_args: Extra command-line arguments (e.g. '-partition 10x2').

    Returns:
        subprocess.CompletedProcess result.
    """
    lmp_binary = _find_lammps_binary()
    if lmp_binary is None:
        raise RuntimeError("No LAMMPS binary found in PATH")

    cmd_parts = [f'mpirun -np {num_cpus}', lmp_binary, f'-in {input_file}', f'-log {log_path}']
    if extra_args:
        cmd_parts.append(extra_args)

    command = ' '.join(cmd_parts)
    result = subprocess.run(
        command, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, timeout=timeout
    )
    return result


def check_lammps_result(result) -> None:
    """Check a LAMMPS subprocess result and raise on failure."""
    if result.returncode != 0:
        stderr_lines = result.stderr.strip().split('\n')[-5:]
        stdout_lines = result.stdout.strip().split('\n')[-2:]
        error_msg = '\n'.join(stderr_lines + stdout_lines)
        raise RuntimeError(f"LAMMPS simulation failed:\n{error_msg}")

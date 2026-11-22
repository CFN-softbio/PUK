import os
import subprocess
from dataclasses import dataclass


VALID_CRYSTAL_TYPES = {"fcc", "bcc", "hcp", "diamond", "sc"}


@dataclass
class StructureResult:
    filepath: str
    atom_count: str
    file_size: int
    crystal_type: str
    lattice_param: float


@dataclass
class AlloyResult:
    filepath: str
    atom_count: str
    base_element: str
    alloy_element: str
    fraction: float


def _count_atoms_in_lammps_file(filepath: str) -> str:
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "atoms" in line:
                    return line.split()[0]
    except Exception:
        pass
    return "unknown"


def _parse_size(size: str) -> list[str]:
    parts = size.strip().split()
    if len(parts) != 3:
        raise ValueError(f"Size must be 3 space-separated integers, got: {size!r}")
    for p in parts:
        if not p.isdigit() or int(p) <= 0:
            raise ValueError(f"Size components must be positive integers, got: {p!r}")
    return parts


def _validate_crystal_type(crystal_type: str) -> str:
    ct = crystal_type.lower().strip()
    if ct not in VALID_CRYSTAL_TYPES:
        raise ValueError(
            f"Invalid crystal type {crystal_type!r}. "
            f"Must be one of: {', '.join(sorted(VALID_CRYSTAL_TYPES))}"
        )
    return ct


def create_crystal_structure(
    element: str,
    crystal_type: str,
    lattice_param: float,
    size: str,
    output_format: str,
    workspace: str,
    atomsk_path: str,
) -> StructureResult:
    ct = _validate_crystal_type(crystal_type)
    if lattice_param <= 0:
        raise ValueError(f"Lattice parameter must be positive, got {lattice_param}")
    size_parts = _parse_size(size)

    ext = "lmp" if output_format.lower() == "lammps" else output_format.lower()
    output_file = f"{element.lower()}_structure.{ext}"

    cmd = [
        atomsk_path,
        "--create", ct, str(lattice_param), element,
        "-duplicate", *size_parts,
        output_file,
        "-overwrite",
    ]

    result = subprocess.run(
        cmd, cwd=workspace, capture_output=True, text=True, timeout=1200,
        stdin=subprocess.DEVNULL,
    )

    output_path = os.path.join(workspace, output_file)
    if result.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f"atomsk failed: {result.stderr or 'Unknown error'}")

    return StructureResult(
        filepath=output_path,
        atom_count=_count_atoms_in_lammps_file(output_path),
        file_size=os.path.getsize(output_path),
        crystal_type=ct,
        lattice_param=lattice_param,
    )


def create_alloy_structure(
    base_element: str,
    alloy_element: str,
    crystal_type: str,
    lattice_param: float,
    size: str,
    alloy_fraction: float,
    workspace: str,
    atomsk_path: str,
    output_filename: str | None = None,
) -> AlloyResult:
    ct = _validate_crystal_type(crystal_type)
    if lattice_param <= 0:
        raise ValueError(f"Lattice parameter must be positive, got {lattice_param}")
    if not (0 < alloy_fraction < 1):
        raise ValueError(f"Alloy fraction must be between 0 and 1 exclusive, got {alloy_fraction}")
    size_parts = _parse_size(size)

    if output_filename is None:
        output_filename = f"{base_element.lower()}_{int(alloy_fraction * 100)}{alloy_element.lower()}_alloy.lmp"

    import uuid
    base_file = f"_tmp_base_{uuid.uuid4().hex[:8]}.cfg"

    # Step 1: create base crystal
    create_cmd = [
        atomsk_path,
        "--create", ct, str(lattice_param), base_element,
        "-duplicate", *size_parts,
        base_file,
        "-overwrite",
    ]
    subprocess.run(create_cmd, cwd=workspace, check=True, capture_output=True, text=True, timeout=1200, stdin=subprocess.DEVNULL)

    # Remove existing output to avoid atomsk ambiguity prompt
    output_path = os.path.join(workspace, output_filename)
    if os.path.exists(output_path):
        os.remove(output_path)

    # Step 2: substitute atoms
    pct = f"{int(alloy_fraction * 100)}%"
    alloy_cmd = [
        atomsk_path, base_file,
        "-select", "random", pct, base_element,
        "-substitute", base_element, alloy_element,
        output_filename,
    ]
    result = subprocess.run(
        alloy_cmd, cwd=workspace, capture_output=True, text=True, timeout=1200,
        stdin=subprocess.DEVNULL,
    )

    if result.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError(f"atomsk alloy creation failed: {result.stderr or 'Unknown error'}")

    # Clean up temp file
    base_path = os.path.join(workspace, base_file)
    if os.path.exists(base_path):
        os.remove(base_path)

    return AlloyResult(
        filepath=output_path,
        atom_count=_count_atoms_in_lammps_file(output_path),
        base_element=base_element,
        alloy_element=alloy_element,
        fraction=alloy_fraction,
    )


def list_structures(workspace: str) -> list[dict]:
    extensions = {".lmp", ".cfg", ".xyz"}
    files = []
    for name in os.listdir(workspace):
        _, ext = os.path.splitext(name)
        if ext.lower() in extensions:
            path = os.path.join(workspace, name)
            atom_count = _count_atoms_in_lammps_file(path) if ext.lower() == ".lmp" else "n/a"
            files.append({
                "name": name,
                "size_bytes": os.path.getsize(path),
                "atom_count": atom_count,
            })
    return files

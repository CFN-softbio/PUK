"""Core business logic for phonon dispersion calculations via phonopy."""

import os
import glob
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import numpy as np
import yaml
from ase.io import read, write


def _detect_potential_type(potential_file: str) -> dict:
    """Detect potential type and return appropriate LAMMPS commands."""
    filename = Path(potential_file).name.lower()

    try:
        with open(potential_file, "r") as f:
            content = f.read(500).lower()
    except Exception:
        content = ""

    config: dict = {}

    if any(ext in filename for ext in [".eam", ".alloy", ".fs"]):
        if ".fs" in filename or "setfl" in content:
            config["pair_style"] = "eam/fs"
        elif ".alloy" in filename or "funcfl" in content:
            config["pair_style"] = "eam/alloy"
        else:
            config["pair_style"] = "eam"
    elif any(ext in filename for ext in [".meam", ".library"]):
        config["pair_style"] = "meam"
        config["meam_library"] = True
    elif "tersoff" in filename or ".tersoff" in filename:
        config["pair_style"] = "tersoff"
    elif "sw" in filename or "stillinger" in filename:
        config["pair_style"] = "sw"
    elif "reax" in filename or ".ff" in filename:
        config["pair_style"] = "reax/c"
    elif any(term in filename for term in ["airebo", "rebo"]):
        config["pair_style"] = "airebo"
    else:
        config["pair_style"] = "unknown"

    return config


def _generate_pair_coeff_line(
    config: dict, elements: list[str], potential_filenames: list[str]
) -> str:
    """Generate appropriate pair_coeff line(s) based on potential type."""
    pair_style = config["pair_style"]
    potential_filename = potential_filenames[0]

    if pair_style in ["eam/alloy", "eam/fs"]:
        return f"pair_coeff * * {potential_filename} {' '.join(elements)}"

    if pair_style == "eam":
        # funcfl files are single-element: one file per atom type, cross terms by mixing
        if len(potential_filenames) > 1:
            return "\n".join(
                f"pair_coeff {i} {i} {fname}"
                for i, fname in enumerate(potential_filenames, start=1)
            )
        return f"pair_coeff * * {potential_filename}"

    if pair_style == "meam":
        if config.get("meam_library"):
            return (
                f"pair_coeff * * library.meam {' '.join(elements)} "
                f"{potential_filename} {' '.join(elements)}"
            )
        return f"pair_coeff * * {potential_filename} {' '.join(elements)}"

    if pair_style in ["tersoff", "sw"]:
        return f"pair_coeff * * {potential_filename} {' '.join(elements)}"

    if pair_style == "reax/c":
        return f"pair_coeff * * {potential_filename}"

    # Generic fallback (airebo, unknown, etc.)
    return f"pair_coeff * * {potential_filename} {' '.join(elements)}"


def _generate_lammps_input(
    config: dict, elements: list[str], potential_filenames: list[str]
) -> str:
    """Generate LAMMPS input file for single-point force calculation."""
    pair_style = config["pair_style"]
    pair_coeff = _generate_pair_coeff_line(config, elements, potential_filenames)

    input_content = f"""# LAMMPS input for phonon force calculation
units metal
atom_style atomic
boundary p p p
read_data structure.lmp

# Potential settings
pair_style {pair_style}
{pair_coeff}

# Neighbor settings
neighbor 2.0 bin
neigh_modify delay 0 every 1 check yes

# Force calculation
compute forces all property/atom fx fy fz
dump forces all custom 1 forces.dump id type x y z fx fy fz

# Run single point calculation
run 0

# Output final forces
write_dump all custom forces.dat id type x y z fx fy fz modify sort id
"""

    if pair_style == "reax/c":
        input_content = input_content.replace(
            "# Potential settings",
            "# Potential settings\nfix qeq all qeq/reax 1 0.0 10.0 1.0e-6 reax/c",
        )

    return input_content


def _determine_crystal_system(lattice_params) -> str:
    """Determine crystal system from lattice parameters."""
    a, b, c, alpha, beta, gamma = lattice_params
    tol = 1e-3

    angles_90 = [abs(angle - 90.0) < tol for angle in [alpha, beta, gamma]]
    all_90 = all(angles_90)

    a_eq_b = abs(a - b) < tol
    b_eq_c = abs(b - c) < tol
    all_equal = a_eq_b and b_eq_c

    if all_equal and all_90:
        return "cubic"
    elif a_eq_b and all_90:
        return "tetragonal"
    elif all_90:
        return "orthorhombic"
    elif a_eq_b and abs(gamma - 120.0) < tol and angles_90[0] and angles_90[1]:
        return "hexagonal"
    elif all_equal and abs(alpha - beta) < tol and abs(beta - gamma) < tol:
        if abs(alpha - 90.0) < tol:
            return "cubic"
        return "rhombohedral"
    elif angles_90[0] and abs(gamma - 90.0) > tol:
        return "monoclinic"
    else:
        return "triclinic"


# Centred cubic lattices: primitive axes (relative to the conventional cell) and
# Setyawan-Curtarolo paths in primitive reciprocal coordinates.
_CENTRED_CUBIC = {
    "F": {
        "primitive_axis": "0 1/2 1/2  1/2 0 1/2  1/2 1/2 0",
        "path": "0 0 0  1/2 0 1/2  1/2 1/4 3/4  3/8 3/8 3/4  0 0 0  1/2 1/2 1/2  5/8 1/4 5/8",
        "labels": ["$\\Gamma$", "X", "W", "K", "$\\Gamma$", "L", "U"],
    },
    "I": {
        "primitive_axis": "-1/2 1/2 1/2  1/2 -1/2 1/2  1/2 1/2 -1/2",
        "path": "0 0 0  1/2 -1/2 1/2  0 0 1/2  0 0 0  1/4 1/4 1/4  1/2 -1/2 1/2",
        "labels": ["$\\Gamma$", "H", "N", "$\\Gamma$", "P", "H"],
    },
}


def _get_centring(atoms) -> str:
    """Return the lattice-centring letter (P, F, I, ...) from the space group."""
    import spglib

    cell = (atoms.cell[:], atoms.get_scaled_positions(), atoms.get_atomic_numbers())
    dataset = spglib.get_symmetry_dataset(cell, symprec=1e-3)
    if dataset is None:
        return "P"
    international = getattr(dataset, "international", None) or dataset["international"]
    return international[0]


def _get_kpoint_path(crystal_system: str) -> tuple:
    """Get appropriate k-point path for crystal system."""
    paths = {
        "cubic": (
            "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.0 0.0  0.5 0.5 0.5",
            ["G", "X", "M", "G", "R"],
        ),
        "tetragonal": (
            "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.0 0.0  "
            "0.0 0.0 0.5  0.5 0.0 0.5  0.5 0.5 0.5  0.0 0.0 0.5",
            ["G", "X", "M", "G", "Z", "R", "A", "Z"],
        ),
        "hexagonal": (
            "0.0 0.0 0.0  0.5 0.0 0.0  0.333 0.333 0.0  0.0 0.0 0.0  "
            "0.0 0.0 0.5  0.5 0.0 0.5  0.333 0.333 0.5  0.0 0.0 0.5",
            ["G", "M", "K", "G", "A", "L", "H", "A"],
        ),
        "orthorhombic": (
            "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.5 0.0  0.0 0.0 0.0  "
            "0.0 0.0 0.5  0.5 0.0 0.5  0.5 0.5 0.5  0.0 0.5 0.5  0.0 0.0 0.5",
            ["G", "X", "S", "Y", "G", "Z", "U", "R", "T", "Z"],
        ),
        "rhombohedral": (
            "0.0 0.0 0.0  0.5 0.5 0.0  0.5 0.0 0.5  0.0 0.0 0.5  "
            "0.0 0.0 0.0  0.5 0.0 0.0",
            ["G", "L", "B", "Z", "G", "X"],
        ),
    }
    # Default for monoclinic/triclinic/unknown
    default = (
        "0.0 0.0 0.0  0.5 0.0 0.0  0.5 0.5 0.0  0.0 0.5 0.0  "
        "0.0 0.0 0.0  0.0 0.0 0.5",
        ["G", "X", "S", "Y", "G", "Z"],
    )
    return paths.get(crystal_system, default)


def _parse_supercell_matrix(workspace: str) -> list[int]:
    """Parse supercell matrix from phonopy_disp.yaml."""
    yaml_path = os.path.join(workspace, "phonopy_disp.yaml")
    if not os.path.exists(yaml_path):
        return [3, 3, 3]

    try:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        raw = data.get("supercell_matrix", [3, 3, 3])

        if isinstance(raw, list):
            if len(raw) == 3 and all(isinstance(x, (int, float)) for x in raw):
                return [int(x) for x in raw]
            if len(raw) == 3 and all(isinstance(x, list) for x in raw):
                return [int(raw[i][i]) for i in range(3)]
    except Exception:
        pass

    return [3, 3, 3]


# ---------------------------------------------------------------------------
# Public API: the 4 tool implementations
# ---------------------------------------------------------------------------


def setup_phonon_calculation(
    workspace: str,
    structure_file: str,
    potential_file: str,
    elements: str,
    dim: str = "3 3 3",
    potential_type: str | None = None,
    phonopy_path: str = "phonopy",
) -> dict:
    """Set up phonon displacement calculations.

    0. Remove phonon files left over from a previous run
    1. Convert LAMMPS structure to POSCAR
    2. Generate displacements with phonopy
    3. Create per-displacement LAMMPS directories

    potential_file may list several space-separated files (one per element, in
    the order of `elements`) for single-element funcfl EAM potentials.
    """
    struct_path = os.path.join(workspace, structure_file)
    pot_paths = [os.path.join(workspace, p) for p in potential_file.split()]
    element_list = elements.strip().split()

    if not os.path.isfile(struct_path):
        return {"success": False, "error": f"Structure file not found: {structure_file}"}
    for pot_path in pot_paths:
        if not os.path.isfile(pot_path):
            return {"success": False, "error": f"Potential file not found: {os.path.basename(pot_path)}"}

    # Step 0: Stale POSCAR-*/disp-* from an earlier system would be picked up below
    for pattern in ["disp-*", "POSCAR-*", "SPOSCAR", "phonopy_disp.yaml", "phonopy.yaml", "FORCE_SETS", "band.*"]:
        for path in glob.glob(os.path.join(workspace, pattern)):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    # Step 1: Convert to POSCAR (LAMMPS type i -> elements[i-1])
    try:
        atoms = read(struct_path, format="lammps-data")
        if "type" in atoms.arrays:
            types = atoms.arrays["type"]
            if types.max() > len(element_list):
                return {
                    "success": False,
                    "error": f"Structure has {types.max()} atom types but only {len(element_list)} elements given",
                }
            atoms.set_chemical_symbols([element_list[t - 1] for t in types])
        poscar_path = os.path.join(workspace, "POSCAR")
        write(poscar_path, atoms, format="vasp")
    except Exception as e:
        return {"success": False, "error": f"Failed to convert structure to POSCAR: {e}"}

    # Step 2: Generate displacements
    result = subprocess.run(
        f'{phonopy_path} --dim="{dim}" -d',
        shell=True,
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {
            "success": False,
            "error": f"phonopy displacement generation failed: {result.stderr}",
        }

    # Step 3: Detect potential type
    if potential_type:
        config = {"pair_style": potential_type}
    else:
        config = _detect_potential_type(pot_paths[0])

    potential_filenames = [Path(p).name for p in pot_paths]

    # Step 4: Create displacement directories
    poscars = sorted(glob.glob(os.path.join(workspace, "POSCAR-*")))
    if not poscars:
        return {"success": False, "error": "No POSCAR-* files generated by phonopy"}

    dirs_created = []
    for i, poscar in enumerate(poscars):
        disp_dir = os.path.join(workspace, f"disp-{i + 1:03d}")
        os.makedirs(disp_dir, exist_ok=True)

        disp_atoms = read(poscar, format="vasp")
        # specorder keeps LAMMPS type numbering in the order of `elements`
        # (ASE otherwise sorts alphabetically, which breaks per-type pair_coeff)
        write(
            os.path.join(disp_dir, "structure.lmp"),
            disp_atoms,
            format="lammps-data",
            specorder=element_list,
        )

        for pot_path in pot_paths:
            shutil.copy2(pot_path, os.path.join(disp_dir, Path(pot_path).name))

        input_content = _generate_lammps_input(config, element_list, potential_filenames)
        with open(os.path.join(disp_dir, "in.forces"), "w") as f:
            f.write(input_content)

        dirs_created.append(f"disp-{i + 1:03d}")

    return {
        "success": True,
        "displacement_count": len(dirs_created),
        "potential_type": config["pair_style"],
        "directories_created": dirs_created,
    }


def run_phonon_force_calculations(
    workspace: str,
    lammps_path: str = "lmp",
    phonopy_path: str = "phonopy",
    timeout_per_displacement: int = 300,
) -> dict:
    """Run LAMMPS force calculations on each displacement, then collect into FORCE_SETS."""
    disp_dirs = sorted(glob.glob(os.path.join(workspace, "disp-*")))
    if not disp_dirs:
        return {"success": False, "error": "No disp-* directories found in workspace"}

    completed = 0
    failed = 0
    errors = []

    for disp_dir in disp_dirs:
        input_path = os.path.join(disp_dir, "in.forces")
        if not os.path.isfile(input_path):
            failed += 1
            errors.append(f"{os.path.basename(disp_dir)}: in.forces not found")
            continue

        try:
            result = subprocess.run(
                [lammps_path, "-in", "in.forces"],
                cwd=disp_dir,
                capture_output=True,
                text=True,
                timeout=timeout_per_displacement,
            )
            forces_path = os.path.join(disp_dir, "forces.dat")
            if result.returncode != 0 or not os.path.isfile(forces_path):
                failed += 1
                errors.append(
                    f"{os.path.basename(disp_dir)}: LAMMPS failed - {result.stderr[:200]}"
                )
            else:
                completed += 1
        except subprocess.TimeoutExpired:
            failed += 1
            errors.append(f"{os.path.basename(disp_dir)}: timed out after {timeout_per_displacement}s")
        except Exception as e:
            failed += 1
            errors.append(f"{os.path.basename(disp_dir)}: {e}")

    if completed == 0:
        return {
            "success": False,
            "total": len(disp_dirs),
            "completed": 0,
            "failed": failed,
            "force_sets_created": False,
            "errors": errors,
        }

    # Collect forces into FORCE_SETS
    force_files = sorted(glob.glob(os.path.join(workspace, "disp-*/forces.dat")))
    result = subprocess.run(
        [phonopy_path, "--lammps", "-f"] + force_files,
        cwd=workspace,
        capture_output=True,
        text=True,
    )

    force_sets_created = os.path.isfile(os.path.join(workspace, "FORCE_SETS"))
    if result.returncode != 0:
        errors.append(f"phonopy FORCE_SETS generation: {result.stderr[:300]}")

    return {
        "success": force_sets_created,
        "total": len(disp_dirs),
        "completed": completed,
        "failed": failed,
        "force_sets_created": force_sets_created,
        "errors": errors if errors else None,
    }


def generate_phonon_dispersion(
    workspace: str,
    phonopy_path: str = "phonopy",
    npoints: int = 101,
) -> dict:
    """Generate phonon band structure from POSCAR + FORCE_SETS."""
    poscar_path = os.path.join(workspace, "POSCAR")
    force_sets_path = os.path.join(workspace, "FORCE_SETS")

    if not os.path.isfile(poscar_path):
        return {"success": False, "error": "POSCAR not found in workspace"}
    if not os.path.isfile(force_sets_path):
        return {"success": False, "error": "FORCE_SETS not found in workspace"}

    try:
        unitcell = read(poscar_path, format="vasp")
    except Exception as e:
        return {"success": False, "error": f"Failed to read POSCAR: {e}"}

    elements = list(dict.fromkeys(unitcell.get_chemical_symbols()))
    lattice_params = unitcell.cell.cellpar()
    crystal_system = _determine_crystal_system(lattice_params)
    supercell_matrix = _parse_supercell_matrix(workspace)

    primitive_axis_line = ""
    lattice_type = crystal_system
    centring = _get_centring(unitcell) if crystal_system == "cubic" else "P"
    if centring in _CENTRED_CUBIC:
        # Conventional FCC/BCC cell: reduce to the primitive cell for the band path
        spec = _CENTRED_CUBIC[centring]
        kpoint_path, path_labels = spec["path"], spec["labels"]
        primitive_axis_line = f"PRIMITIVE_AXIS = {spec['primitive_axis']}\n"
        lattice_type = {"F": "fcc", "I": "bcc"}[centring]
    else:
        kpoint_path, path_labels = _get_kpoint_path(crystal_system)

    band_conf = (
        f"# Phonopy band structure configuration\n"
        f"# Auto-generated for {lattice_type} lattice\n"
        f"\n"
        f"ATOM_NAME = {' '.join(elements)}\n"
        f"DIM = {supercell_matrix[0]} {supercell_matrix[1]} {supercell_matrix[2]}\n"
        f"{primitive_axis_line}"
        f"BAND_POINTS = {npoints}\n"
        f"\n"
        f"# High-symmetry k-point path for {lattice_type} lattice\n"
        f"BAND = {kpoint_path}\n"
        f"BAND_LABELS = {' '.join(path_labels)}\n"
        f"\n"
        f"FORCE_SETS = READ\n"
    )

    with open(os.path.join(workspace, "band.conf"), "w") as f:
        f.write(band_conf)

    result = subprocess.run(
        [phonopy_path, "-p", "-s", "band.conf"],
        cwd=workspace,
        capture_output=True,
        text=True,
        env={**os.environ, "MPLBACKEND": "Agg"},
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": f"phonopy band calculation failed: {result.stderr}",
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    files_created = []
    for name in ["band.conf", "band.yaml", "band.dat", "band.pdf"]:
        if os.path.isfile(os.path.join(workspace, name)):
            files_created.append(name)

    return {
        "success": True,
        "crystal_system": crystal_system,
        "lattice_type": lattice_type,
        "lattice_params": {
            "a": round(lattice_params[0], 4),
            "b": round(lattice_params[1], 4),
            "c": round(lattice_params[2], 4),
            "alpha": round(lattice_params[3], 2),
            "beta": round(lattice_params[4], 2),
            "gamma": round(lattice_params[5], 2),
        },
        "kpoint_path": " -> ".join(label.replace("$\\Gamma$", "G") for label in path_labels),
        "files_created": files_created,
    }


def list_phonon_files(workspace: str) -> dict:
    """Scan workspace for phonon-related files."""
    setup_files = []
    displacement_dirs = []
    force_data = []
    band_files = []

    for name in sorted(os.listdir(workspace)):
        full = os.path.join(workspace, name)

        if name in ("POSCAR", "phonopy_disp.yaml"):
            setup_files.append({"name": name, "size_bytes": os.path.getsize(full)})

        elif name.startswith("POSCAR-") and os.path.isfile(full):
            setup_files.append({"name": name, "size_bytes": os.path.getsize(full)})

        elif name.startswith("disp-") and os.path.isdir(full):
            has_forces = os.path.isfile(os.path.join(full, "forces.dat"))
            displacement_dirs.append({"name": name, "forces_computed": has_forces})

        elif name == "FORCE_SETS" and os.path.isfile(full):
            force_data.append({"name": name, "size_bytes": os.path.getsize(full)})

        elif name.startswith("band.") and os.path.isfile(full):
            band_files.append({"name": name, "size_bytes": os.path.getsize(full)})

    return {
        "setup_files": setup_files,
        "displacement_dirs": displacement_dirs,
        "force_data": force_data,
        "band_files": band_files,
    }

"""Parsing logic for LAMMPS log files."""

import re
from pathlib import Path


# Compiled regex patterns
RE_VERSION = re.compile(r"^LAMMPS \((.+)\)", re.MULTILINE)
RE_ATOMS = re.compile(r"^\s*(\d+) atoms\s*$", re.MULTILINE)
RE_WARNING = re.compile(r"^WARNING: (.+)$", re.MULTILINE)
RE_ERROR = re.compile(r"^ERROR: (.+)$", re.MULTILINE)
RE_WALL_TIME = re.compile(r"^Total wall time: (.+)$", re.MULTILINE)
RE_LOOP_TIME = re.compile(
    r"^Loop time of ([\d.e+-]+) on (\d+) procs for (\d+) steps with (\d+) atoms",
    re.MULTILINE,
)
RE_THERMO_HEADER = re.compile(r"^\s*(Step\s+.+)$", re.MULTILINE)

# Lattice constants patterns
RE_COHESIVE = re.compile(r"Cohesive energy = ([\d.e+-]+) eV/atom")
RE_CELL_A = re.compile(r"Cell a = ([\d.e+-]+) Angstrom")
RE_CELL_B = re.compile(r"Cell b = ([\d.e+-]+) Angstrom")
RE_CELL_C = re.compile(r"Cell c = ([\d.e+-]+) Angstrom")
RE_CELL_ALPHA = re.compile(r"Cell alpha = ([\d.e+-]+) degrees")
RE_CELL_BETA = re.compile(r"Cell beta\s*= ([\d.e+-]+) degrees")
RE_CELL_GAMMA = re.compile(r"Cell gamma = ([\d.e+-]+) degrees")
RE_NUM_ATOMS = re.compile(r"Number of atoms = (\d+)")

# Elastic constants patterns
RE_CIJ = re.compile(r"Elastic Constant C(\d\d)all = ([\d.e+-]+) GPa")
RE_BULK = re.compile(r"Bulk Modulus = ([\d.e+-]+) GPa")
RE_SHEAR1 = re.compile(r"Shear Modulus 1 = ([\d.e+-]+) GPa")
RE_SHEAR2 = re.compile(r"Shear Modulus 2 = ([\d.e+-]+) GPa")
RE_POISSON = re.compile(r"Poisson Ratio = ([\d.e+-]+)")


def _read_log(filepath: str) -> str:
    """Read a log file and return its contents."""
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"Log file not found: {filepath}")
    return p.read_text(encoding="utf-8", errors="replace")


def parse_general(log_file: str) -> dict:
    """Parse general info from a LAMMPS log file."""
    text = _read_log(log_file)

    version_m = RE_VERSION.search(text)
    atoms_matches = RE_ATOMS.findall(text)
    warnings = RE_WARNING.findall(text)
    errors = RE_ERROR.findall(text)
    wall_m = RE_WALL_TIME.search(text)

    # Thermo blocks
    thermo_blocks = []
    for header_m in RE_THERMO_HEADER.finditer(text):
        columns = header_m.group(1).split()
        # Count data rows: lines after header until "Loop time of" or blank
        start = header_m.end()
        block_text = text[start:]
        row_count = 0
        first_step = None
        last_step = None
        for line in block_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("Loop time"):
                break
            parts = stripped.split()
            if parts and parts[0].lstrip("-").isdigit():
                row_count += 1
                step = int(parts[0])
                if first_step is None:
                    first_step = step
                last_step = step
            else:
                break
        thermo_blocks.append({
            "columns": columns,
            "row_count": row_count,
            "step_range": [first_step, last_step] if first_step is not None else None,
        })

    return {
        "success": True,
        "version": version_m.group(1) if version_m else None,
        "atom_count": int(atoms_matches[0]) if atoms_matches else None,
        "warnings": warnings,
        "errors": errors,
        "wall_time": wall_m.group(1) if wall_m else None,
        "thermo_blocks": thermo_blocks,
    }


def parse_lattice_constants(log_file: str, supercell_size: int = 10) -> dict:
    """Parse lattice constants and cohesive energy from a LAMMPS log."""
    text = _read_log(log_file)

    # Find the delimited section
    marker = "Lattice Constants and Cohesive Energy"
    if marker not in text:
        return {
            "success": False,
            "error": f"Section '{marker}' not found in log file",
        }

    section_start = text.index(marker)
    section = text[section_start:]

    cohesive_m = RE_COHESIVE.search(section)
    cell_a_m = RE_CELL_A.search(section)
    cell_b_m = RE_CELL_B.search(section)
    cell_c_m = RE_CELL_C.search(section)
    alpha_m = RE_CELL_ALPHA.search(section)
    beta_m = RE_CELL_BETA.search(section)
    gamma_m = RE_CELL_GAMMA.search(section)
    natoms_m = RE_NUM_ATOMS.search(section)

    if not cohesive_m:
        return {"success": False, "error": "Could not parse cohesive energy"}

    cell_a = float(cell_a_m.group(1)) if cell_a_m else None
    cell_b = float(cell_b_m.group(1)) if cell_b_m else None
    cell_c = float(cell_c_m.group(1)) if cell_c_m else None

    result = {
        "success": True,
        "cohesive_energy_eV_per_atom": float(cohesive_m.group(1)),
        "num_atoms": int(natoms_m.group(1)) if natoms_m else None,
        "cell_dimensions": {
            "a_angstrom": cell_a,
            "b_angstrom": cell_b,
            "c_angstrom": cell_c,
        },
        "cell_angles": {
            "alpha_degrees": float(alpha_m.group(1)) if alpha_m else None,
            "beta_degrees": float(beta_m.group(1)) if beta_m else None,
            "gamma_degrees": float(gamma_m.group(1)) if gamma_m else None,
        },
        "supercell_size": supercell_size,
        "lattice_parameters": {},
    }

    # Derive per-unit-cell lattice parameters
    if cell_a is not None:
        result["lattice_parameters"]["a_angstrom"] = cell_a / supercell_size
    if cell_b is not None:
        result["lattice_parameters"]["b_angstrom"] = cell_b / supercell_size
    if cell_c is not None:
        result["lattice_parameters"]["c_angstrom"] = cell_c / supercell_size

    return result


def parse_elastic_constants(log_file: str) -> dict:
    """Parse elastic constants tensor and derived properties from a LAMMPS log."""
    text = _read_log(log_file)

    marker = "Components of the Elastic Constant Tensor"
    if marker not in text:
        return {
            "success": False,
            "error": f"Section '{marker}' not found in log file",
        }

    section_start = text.index(marker)
    section = text[section_start:]

    # Parse all Cij values
    cij = {}
    for m in RE_CIJ.finditer(section):
        key = f"C{m.group(1)}"
        cij[key] = float(m.group(2))

    if not cij:
        return {"success": False, "error": "Could not parse any Cij values"}

    # Parse derived properties
    bulk_m = RE_BULK.search(section)
    shear1_m = RE_SHEAR1.search(section)
    shear2_m = RE_SHEAR2.search(section)
    poisson_m = RE_POISSON.search(section)

    return {
        "success": True,
        "elastic_constants_GPa": cij,
        "derived_properties": {
            "bulk_modulus_GPa": float(bulk_m.group(1)) if bulk_m else None,
            "shear_modulus_1_GPa": float(shear1_m.group(1)) if shear1_m else None,
            "shear_modulus_2_GPa": float(shear2_m.group(1)) if shear2_m else None,
            "poisson_ratio": float(poisson_m.group(1)) if poisson_m else None,
        },
    }


def list_results(workspace: str) -> dict:
    """Categorize workspace files by type."""
    ws = Path(workspace)
    if not ws.exists():
        return {"success": False, "error": f"Workspace not found: {workspace}"}

    categories = {
        "logs": [],
        "structures": [],
        "potentials": [],
        "inputs": [],
        "data_files": [],
        "dumps": [],
        "other": [],
    }

    ext_map = {
        ".log": "logs",
        ".out": "logs",
        ".lmp": "structures",
        ".cfg": "structures",
        ".xyz": "structures",
        ".eam": "potentials",
        ".alloy": "potentials",
        ".fs": "potentials",
        ".sw": "potentials",
        ".tersoff": "potentials",
        ".meam": "potentials",
        ".dat": "data_files",
        ".dump": "dumps",
    }

    for f in sorted(ws.iterdir()):
        if not f.is_file():
            continue
        name = f.name
        size = f.stat().st_size
        ext = f.suffix.lower()

        # Categorize: check extension first, then name patterns
        if ext in ext_map:
            category = ext_map[ext]
        elif name.startswith("in.") or ext == ".mod":
            category = "inputs"
        else:
            category = "other"

        categories[category].append({"name": name, "size_bytes": size})

    return {"success": True, "files": categories}

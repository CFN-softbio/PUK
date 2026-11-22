"""Input file generation logic for LAMMPS simulations."""

import os
import shutil

from templates import (
    POTENTIAL_MAP,
    EXTENSION_MAP,
    LATTICE_CONSTANTS_TEMPLATE,
    INIT_MOD_TEMPLATE,
    POTENTIAL_MOD_TEMPLATE,
    MELT_RELAX_TEMPLATE,
    MELT_INTERFACE_TEMPLATE,
    MELT_COEXIST_TEMPLATE,
    format_potential_block,
)


def detect_potential_type(potential_file: str) -> str | None:
    """Auto-detect potential type from file extension."""
    name = potential_file.lower()
    # Check multi-part extensions first
    for ext, ptype in sorted(EXTENSION_MAP.items(), key=lambda x: -len(x[0])):
        if name.endswith(ext):
            return ptype
    return None


def resolve_potential_type(potential_file: str, potential_type: str | None) -> str:
    """Resolve potential type: use explicit value or auto-detect from filename."""
    if potential_type:
        if potential_type not in POTENTIAL_MAP:
            raise ValueError(
                f"Unknown potential_type '{potential_type}'. "
                f"Valid types: {', '.join(POTENTIAL_MAP.keys())}"
            )
        return potential_type
    detected = detect_potential_type(potential_file)
    if detected:
        return detected
    raise ValueError(
        f"Cannot auto-detect potential type from '{potential_file}'. "
        f"Please specify potential_type explicitly."
    )


def build_potential_block(potential_file: str, potential_type: str, elements: str) -> str:
    """Build pair_style + pair_coeff lines for a given potential."""
    pair_style, coeff_pattern = POTENTIAL_MAP[potential_type]
    pair_coeff = coeff_pattern.format(file=potential_file, elements=elements)
    return format_potential_block(pair_style, pair_coeff)


def generate_lattice_constants(
    structure_file: str,
    potential_file: str,
    elements: str,
    workspace: str,
    potential_type: str | None = None,
    output_filename: str | None = None,
) -> dict:
    """Generate LAMMPS input for lattice constants and cohesive energy."""
    ptype = resolve_potential_type(potential_file, potential_type)
    potential_block = build_potential_block(potential_file, ptype, elements)

    content = LATTICE_CONSTANTS_TEMPLATE.format(
        structure_file=structure_file,
        potential_block=potential_block,
    )

    filename = output_filename or "in.lattice_constants"
    filepath = os.path.join(workspace, filename)
    with open(filepath, "w", newline="\n") as f:
        f.write(content)

    return {
        "filepath": filepath,
        "filename": filename,
        "simulation_type": "lattice_constants",
        "potential_type": ptype,
        "files_created": [filename],
    }


def generate_elastic_constants(
    structure_file: str,
    potential_file: str,
    elements: str,
    workspace: str,
    potential_type: str | None = None,
    default_files_dir: str | None = None,
) -> dict:
    """Generate LAMMPS input files for elastic constants calculation.

    Creates 4 files: in.elastic, init.mod, potential.mod, displace.mod
    """
    ptype = resolve_potential_type(potential_file, potential_type)
    potential_block = build_potential_block(potential_file, ptype, elements)

    # Find default files directory
    if default_files_dir is None:
        # Look relative to project root
        server_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(server_dir))
        default_files_dir = os.path.join(project_root, "src", "tools", "default_files")

    files_created = []

    # 1. Copy in.elastic (unchanged)
    src_elastic = os.path.join(default_files_dir, "in.elastic")
    dst_elastic = os.path.join(workspace, "in.elastic")
    shutil.copy2(src_elastic, dst_elastic)
    files_created.append("in.elastic")

    # 2. Generate init.mod (customized with structure file)
    init_content = INIT_MOD_TEMPLATE.format(structure_file=structure_file)
    init_path = os.path.join(workspace, "init.mod")
    with open(init_path, "w", newline="\n") as f:
        f.write(init_content)
    files_created.append("init.mod")

    # 3. Generate potential.mod (customized with pair_style/pair_coeff)
    potential_content = POTENTIAL_MOD_TEMPLATE.format(potential_block=potential_block)
    potential_path = os.path.join(workspace, "potential.mod")
    with open(potential_path, "w", newline="\n") as f:
        f.write(potential_content)
    files_created.append("potential.mod")

    # 4. Copy displace.mod (unchanged)
    src_displace = os.path.join(default_files_dir, "displace.mod")
    dst_displace = os.path.join(workspace, "displace.mod")
    shutil.copy2(src_displace, dst_displace)
    files_created.append("displace.mod")

    return {
        "filepath": dst_elastic,
        "filename": "in.elastic",
        "simulation_type": "elastic_constants",
        "potential_type": ptype,
        "files_created": files_created,
    }


def generate_melting_point(
    structure_file: str,
    potential_file: str,
    elements: str,
    estimated_melting_point: float,
    workspace: str,
    potential_type: str | None = None,
    supercell_z: int = 3,
) -> dict:
    """Generate LAMMPS input files for melting point calculation.

    Creates 3 sequential scripts:
    - in.melt_relax — relax structure
    - in.melt_interface — create solid-liquid interface
    - in.melt_coexist — coexistence run to find melting point
    """
    ptype = resolve_potential_type(potential_file, potential_type)
    potential_block = build_potential_block(potential_file, ptype, elements)

    melt_temp = estimated_melting_point * 1.5  # Well above melting point
    equil_temp = estimated_melting_point

    # Replicate line for z-direction extension
    replicate_line = ""
    if supercell_z > 1:
        replicate_line = f"replicate       1 1 {supercell_z}"

    files_created = []

    # 1. Relaxation script
    relax_content = MELT_RELAX_TEMPLATE.format(
        structure_file=structure_file,
        potential_block=potential_block,
    )
    relax_path = os.path.join(workspace, "in.melt_relax")
    with open(relax_path, "w", newline="\n") as f:
        f.write(relax_content)
    files_created.append("in.melt_relax")

    # 2. Interface creation script
    interface_content = MELT_INTERFACE_TEMPLATE.format(
        potential_block=potential_block,
        replicate_line=replicate_line,
        melt_temp=melt_temp,
        equil_temp=equil_temp,
    )
    interface_path = os.path.join(workspace, "in.melt_interface")
    with open(interface_path, "w", newline="\n") as f:
        f.write(interface_content)
    files_created.append("in.melt_interface")

    # 3. Coexistence script
    coexist_content = MELT_COEXIST_TEMPLATE.format(
        potential_block=potential_block,
        equil_temp=equil_temp,
    )
    coexist_path = os.path.join(workspace, "in.melt_coexist")
    with open(coexist_path, "w", newline="\n") as f:
        f.write(coexist_content)
    files_created.append("in.melt_coexist")

    return {
        "filepath": relax_path,
        "filename": "in.melt_relax",
        "simulation_type": "melting_point",
        "potential_type": ptype,
        "estimated_melting_point": estimated_melting_point,
        "files_created": files_created,
        "run_order": [
            "in.melt_relax",
            "in.melt_interface",
            "in.melt_coexist",
        ],
    }


def list_input_files(workspace: str) -> list[dict]:
    """List all LAMMPS input/mod files in workspace."""
    results = []
    for name in sorted(os.listdir(workspace)):
        if name.startswith("in.") or name.endswith(".mod"):
            path = os.path.join(workspace, name)
            if os.path.isfile(path):
                results.append({
                    "name": name,
                    "size_bytes": os.path.getsize(path),
                })
    return results

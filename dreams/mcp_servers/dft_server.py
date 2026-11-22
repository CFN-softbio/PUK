#!/usr/bin/env python
"""
DREAMS DFT MCP Server

Exposes DFT tools for structure generation, Quantum ESPRESSO input file creation,
convergence testing, post-processing, and analysis via the Model Context Protocol.
"""

import os
import io
import json
import contextlib
import sqlite3
import time
from copy import deepcopy
from typing import Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import rcParams

from mcp.server.fastmcp import FastMCP

from mcp_servers.shared import (
    get_config, get_working_dir, get_pseudo_dir,
    select_k_ecut, read_BEEF_output, initialize_database,
)
from ase.io import read, write
from ase.build import bulk, add_adsorbate
from ase.eos import EquationOfState
import ase.build
try:
    from autocat.surface import generate_surface_structures
    from autocat.adsorption import get_adsorbate_height_estimate
    HAS_AUTOCAT = True
except ImportError:
    HAS_AUTOCAT = False

# ---------------------------------------------------------------------------
# Helpers (non-tool logic extracted from src/tools.py)
# ---------------------------------------------------------------------------


def _get_kpoints(cell, kspacing: float) -> list:
    """Compute odd k-point grid from cell and kspacing."""
    kpoints = [
        2 * ((np.ceil(2 * np.pi / np.linalg.norm(ii) / kspacing).astype(int)) // 2 + 1)
        for ii in cell
    ]
    for i in range(len(kpoints)):
        if kpoints[i] % 2 == 0:
            kpoints[i] = kpoints[i] - 1 if kpoints[i] > 1 else kpoints[i] + 1
    return kpoints


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "dreams-dft",
    instructions=(
        "DREAMS DFT server — tools for crystal structure generation, "
        "Quantum ESPRESSO input file creation, convergence testing, "
        "equation-of-state calculations, and post-processing of DFT results."
    ),
)


# ── Structure generation tools ────────────────────────────────────────────


@mcp.tool()
def init_structure_data(
    element: str,
    lattice: str,
    a: float,
    b: Optional[float] = None,
    c: Optional[float] = None,
) -> str:
    """
    Create a single-element bulk crystal structure and save it.

    Args:
        element: Element symbol (e.g. 'Li', 'Pt')
        lattice: One of sc, fcc, bcc, tetragonal, bct, hcp, rhombohedral,
                 orthorhombic, mcl, diamond, zincblende, rocksalt,
                 cesiumchloride, fluorite, wurtzite
        a: Lattice constant a
        b: Lattice constant b (optional)
        c: Lattice constant c (optional)

    Returns:
        Path where the structure was saved.
    """
    wd = get_working_dir()
    os.makedirs(wd, exist_ok=True)
    atoms = bulk(element, lattice, a=a, b=b, c=c, cubic=True)
    save_path = os.path.join(wd, f"{element}-{lattice}.xyz")
    write(save_path, atoms)
    return f"Created atoms saved in {save_path}"


@mcp.tool()
def generate_surface_and_get_sites(
    species: str,
    crystal_structure: str,
    lattice_a: float,
    facet: str,
    supercell_dim: list[int],
    n_fixed_layers: int = 3,
) -> str:
    """
    Generate a surface slab and return available adsorption sites.

    Args:
        species: Element symbol (e.g. 'Pt')
        crystal_structure: Crystal structure (fcc, bcc, etc.)
        lattice_a: Lattice parameter a for the species
        facet: Miller index string (e.g. '111', '100')
        supercell_dim: Supercell repetitions [nx, ny, nz]. nz is forced to 6.
        n_fixed_layers: Number of fixed bottom layers (default 3)
    """
    if not HAS_AUTOCAT:
        return "Error: autocat package is not installed. Install it to use surface generation tools."
    wd = get_working_dir()
    a_dict = {species: lattice_a}
    supercell_dim[-1] = 6

    surface_dict = generate_surface_structures(
        species_list=[species],
        crystal_structures={species: crystal_structure},
        a_dict=a_dict,
        facets={species: [facet]},
        supercell_dim=supercell_dim,
        n_fixed_layers=n_fixed_layers,
        dirs_exist_ok=True,
        write_to_disk=True,
        write_location=wd,
    )

    dir_name = wd.split("/")[-1]
    key = f"{crystal_structure}{facet}"
    my_surface = surface_dict[species][key]["structure"]
    my_sites = my_surface.info["adsorbate_info"]["sites"]

    func = eval(f"ase.build.{key}")
    tmp_atom = func(species, size=(1, 1, 1), a=lattice_a)
    for site in my_sites:
        my_sites[site] = np.sum(
            tmp_atom.cell * [my_sites[site][0], my_sites[site][1], 0], axis=0
        )[:2]

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(my_sites)
    sites_str = buf.getvalue()

    abs_path = surface_dict[species][key]["traj_file_path"]
    rel_path = abs_path.split(f"{dir_name}/")[-1]
    return f"Surface saved at {rel_path}, available adsorption sites: {sites_str}"


@mcp.tool()
def generate_adsorbate(
    symbols: str,
    positions: list[list[float]],
    filename: str,
) -> str:
    """
    Generate an adsorbate molecule and save it as a .traj file.

    Args:
        symbols: Element symbols with no delimiters (e.g. 'CO')
        positions: Atom positions [[x1,y1,z1], [x2,y2,z2], ...]
        filename: Output filename ending in .traj (no path)
    """
    assert filename.endswith(".traj"), "filename must end with .traj"
    assert "/" not in filename, "filename must not contain '/'"

    wd = get_working_dir()
    from ase import Atoms

    ads_dir = os.path.join(wd, "adsorbates")
    os.makedirs(ads_dir, exist_ok=True)
    atoms = Atoms(symbols=symbols, positions=positions)
    atoms.center(vacuum=10.0)
    write(os.path.join(ads_dir, filename), atoms)
    return f"Adsorbate saved at adsorbates/{filename}"


@mcp.tool()
def add_adsorbate_to_surface(
    surface_path: str,
    adsorbate_path: str,
    sites: list[list[float]],
    rotations: list[list],
    output_filename: str,
) -> str:
    """
    Add adsorbate(s) to a surface structure at specified sites.

    Args:
        surface_path: Path to the surface .traj file
        adsorbate_path: Path to the adsorbate .traj file
        sites: Adsorption site positions [[x1,y1], [x2,y2], ...]
        rotations: Rotations for each adsorbate [[angle, axis], ...] e.g. [[90.0, 'x']]
        output_filename: Output .traj filename (no path)
    """
    assert output_filename.endswith(".traj"), "output_filename must end with .traj"
    assert "/" not in output_filename

    if not HAS_AUTOCAT:
        return "Error: autocat package is not installed. Install it to use adsorption tools."
    wd = get_working_dir()
    dir_name = wd.split("/")[-1]

    # Resolve surface path
    if not surface_path.startswith(dir_name) and not surface_path.startswith(f"./{dir_name}") and not surface_path.startswith("/"):
        surface_path = os.path.join(wd, surface_path)
    my_surface = read(surface_path)

    # Resolve adsorbate path
    if not adsorbate_path.startswith(dir_name) and not adsorbate_path.startswith(f"./{dir_name}") and not adsorbate_path.startswith("/"):
        adsorbate_path = os.path.join(wd, adsorbate_path)
    my_adsorbate = read(adsorbate_path)

    for one_site, one_rot in zip(sites, rotations):
        ads_copy = my_adsorbate.copy()
        ads_copy.rotate(float(one_rot[0]), one_rot[1], center="COP")
        lowest_idx = ads_copy.positions[:, 2].argmin()
        height = get_adsorbate_height_estimate(
            my_surface, ads_copy, (one_site[0], one_site[1]), anchor_atom_index=lowest_idx
        )
        add_adsorbate(
            my_surface, ads_copy, height=height,
            position=(one_site[0], one_site[1]), mol_index=lowest_idx,
        )

    parent_path = os.path.dirname(surface_path)
    abs_path = os.path.join(parent_path, output_filename)
    write(abs_path, my_surface)
    rel_path = abs_path.split(f"{dir_name}/")[-1]
    return f"Surface with adsorbate saved at {rel_path}"


# ── Pseudopotential tools ─────────────────────────────────────────────────


@mcp.tool()
def find_pseudopotential(element: str) -> str:
    """
    Find available pseudopotential files for an element.

    Args:
        element: Element symbol (e.g. 'Li', 'Pt')
    """
    pseudo_dir = get_pseudo_dir()
    matches = []
    for root, dirs, files in os.walk(pseudo_dir):
        for f in files:
            if element == f.split("_")[0].capitalize():
                matches.append(f)
    if matches:
        listing = "\n".join(matches)
        return f"Pseudopotential files for {element}:\n{listing}\nunder {pseudo_dir}"
    return f"Could not find pseudopotential for {element}"


# ── QE script generation tools ────────────────────────────────────────────


@mcp.tool()
def write_qe_script(
    elements: list[str],
    pseudopotential_files: list[str],
    filename: str,
    input_atoms_path: str,
    ensemble_calculation: bool,
    calculation: str,
    restart_mode: str,
    prefix: str,
    ibrav: int,
    nat: int,
    ntyp: int,
    ecutwfc: float,
    ecutrho: float,
    occupations: str,
    smearing: str,
    degauss: float,
    conv_thr: float,
    electron_maxstep: int,
    kspacing: float,
    input_dft: str,
    additional_input: Optional[dict] = None,
) -> str:
    """
    Generate a Quantum ESPRESSO input file (.pwi) using ASE.

    Args:
        elements: Distinct element symbols in the unit cell
        pseudopotential_files: Pseudopotential filenames matching elements order
        filename: Output filename ending in .pwi
        input_atoms_path: Path to input structure (.traj, .xyz, or .pwi with relaxed structure)
        ensemble_calculation: True for BEEF ensemble calculation
        calculation: 'scf', 'relax', or 'ensemble'
        restart_mode: 'from_scratch' or 'restart'
        prefix: Prefix for output files
        ibrav: Bravais lattice index (use 0 for conventional cell)
        nat: Number of atoms
        ntyp: Number of atom types
        ecutwfc: Wavefunction energy cutoff in Ry (30-100)
        ecutrho: Charge density cutoff in Ry (typically ecutwfc*4)
        occupations: 'smearing', 'tetrahedra', 'fixed', etc.
        smearing: 'gaussian', 'methfessel-paxton', 'marzari-vanderbilt', 'fermi-dirac'
        degauss: Gaussian spreading in Ry
        conv_thr: SCF convergence threshold (use 1e-6)
        electron_maxstep: Max SCF iterations
        kspacing: K-point spacing in 1/Angstrom
        input_dft: DFT functional ('LDA', 'PBE', or 'BEEF-vdW')
        additional_input: Extra QE input parameters as a flat dict
    """
    if additional_input is None:
        additional_input = {}

    if ensemble_calculation:
        assert calculation == "ensemble", "Set calculation='ensemble' for ensemble runs"
    if calculation == "ensemble":
        assert input_atoms_path.endswith(".pwi"), "Ensemble calc needs relaxed .pwi structure"
        assert input_dft == "BEEF-vdW", "Ensemble calc requires BEEF-vdW functional"

    wd = get_working_dir()
    pseudo_dir = get_pseudo_dir()
    dir_name = wd.split("/")[-1]

    # Validate pseudopotentials
    pseudopotentials = {}
    for el, pp in zip(elements, pseudopotential_files):
        if not os.path.exists(os.path.join(pseudo_dir, pp)):
            return f"Invalid pseudopotential file: {pp}. Check the filename."
        pseudopotentials[el] = pp

    # Resolve input atoms path
    resolved = input_atoms_path
    if not resolved.startswith(dir_name) and not resolved.startswith(f"./{dir_name}") and not resolved.startswith("/"):
        resolved = os.path.join(wd, resolved)
    if resolved.endswith(".pwi"):
        resolved += ".pwo"
    try:
        atoms = read(resolved)
    except Exception:
        if os.path.exists(resolved):
            return f"Job {input_atoms_path} failed or did not converge. Use only converged jobs."
        return f"Invalid input atoms path: {input_atoms_path}."

    kpoints = _get_kpoints(atoms.cell, kspacing)
    out_path = os.path.join(wd, filename)

    write(
        out_path,
        atoms,
        input_data={
            "calculation": calculation,
            "restart_mode": restart_mode,
            "prefix": prefix,
            "pseudo_dir": pseudo_dir,
            "outdir": "./out",
            "disk_io": "none",
            "ibrav": ibrav,
            "nat": nat,
            "ntyp": ntyp,
            "ecutwfc": ecutwfc,
            "ecutrho": ecutrho,
            "occupations": occupations,
            "smearing": smearing,
            "degauss": degauss,
            "conv_thr": conv_thr,
            "electron_maxstep": electron_maxstep,
            "input_dft": input_dft,
            **additional_input,
        },
        format="espresso-in",
        pseudopotentials=pseudopotentials,
        kpts=tuple(kpoints),
    )

    return f"Quantum ESPRESSO input script written to {filename}"


@mcp.tool()
def generate_convergence_test(
    input_file_name: str,
    kspacing_values: list[float],
    ecutwfc_values: list[int],
) -> str:
    """
    Generate convergence test input scripts from a template QE input file.

    Creates scripts varying kspacing (at max ecutwfc) and ecutwfc (at min kspacing).
    Writes a jobs_K_and_ecut.json sidecar in the working directory that maps each
    generated .pwi filename to its (kspacing, ecutwfc) pair, for later use by
    get_kspacing_ecutwfc.

    Args:
        input_file_name: Template .pwi filename
        kspacing_values: K-spacings to test (e.g. [0.1, 0.15, 0.2, 0.25, 0.3])
        ecutwfc_values: Energy cutoffs to test (e.g. [40, 60, 80, 100, 120])
    """
    wd = get_working_dir()
    input_file = os.path.join(wd, input_file_name)

    try:
        atom = read(input_file)
    except Exception:
        return f"Invalid input file: {input_file_name}."

    cell = atom.cell
    ecutwfc_max = max(ecutwfc_values)
    kspacing_min = min(kspacing_values)
    job_list_dict = {}
    job_list = []

    # Vary kspacing at max ecutwfc
    for k in kspacing_values:
        kpoints = _get_kpoints(cell, k)
        with open(input_file, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "ecutwfc" in line:
                lines[i] = f"    ecutwfc = {ecutwfc_max},\n"
            if "ecutrho" in line:
                lines[i] = f"    ecutrho = {ecutwfc_max * 4},\n"
            if "K_POINTS" in line:
                lines[i + 1] = " ".join(map(str, kpoints)) + " 0 0 0\n"
        base = os.path.splitext(input_file_name)[0].split("_k_")[0]
        new_name = f"{base}_k_{k}_ecutwfc_{ecutwfc_max}.pwi"
        job_list_dict[new_name] = {"k": k, "ecutwfc": ecutwfc_max}
        job_list.append(new_name)
        with open(os.path.join(wd, new_name), "w") as f:
            f.writelines(lines)

    # Vary ecutwfc at min kspacing
    for e in ecutwfc_values:
        kpoints = _get_kpoints(cell, kspacing_min)
        with open(input_file, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "ecutwfc" in line:
                lines[i] = f"    ecutwfc = {e},\n"
            if "ecutrho" in line:
                lines[i] = f"    ecutrho = {e * 4},\n"
            if "K_POINTS" in line:
                lines[i + 1] = " ".join(map(str, kpoints)) + " 0 0 0\n"
        new_name = f"{os.path.splitext(input_file_name)[0]}_k_{kspacing_min}_ecutwfc_{e}.pwi"
        job_list_dict[new_name] = {"k": kspacing_min, "ecutwfc": e}
        job_list.append(new_name)
        with open(os.path.join(wd, new_name), "w") as f:
            f.writelines(lines)

    job_list = sorted(set(job_list))
    with open(os.path.join(wd, "jobs_K_and_ecut.json"), "w") as f:
        json.dump(job_list_dict, f, indent=2)

    return (
        f"Generated {len(job_list)} convergence-test scripts: {job_list}. "
        "Submit them via the HPC server or run_jobs_locally."
    )


@mcp.tool()
def generate_eos_test(
    input_file_name: str,
    kspacing: float,
    ecutwfc: int,
    step_size: float = 0.025,
) -> str:
    """
    Generate equation-of-state test scripts (5 volume points) from a template.

    Args:
        input_file_name: Template .pwi filename
        kspacing: K-point spacing to use
        ecutwfc: Energy cutoff to use
        step_size: Cell scaling step (default 0.025 → 0.95 to 1.05)
    """
    assert 0.01 < step_size < 0.1, "step_size must be between 0.01 and 0.1"

    wd = get_working_dir()
    input_file = os.path.join(wd, input_file_name)
    prefix = input_file_name.split(".")[0]

    try:
        atom = read(input_file)
    except Exception:
        return f"Invalid input file: {input_file_name}."

    cell = atom.cell
    kpoints = _get_kpoints(cell, kspacing)
    job_list = []

    for scale in np.linspace(1 - step_size * 2, 1 + step_size * 2, 5):
        with open(input_file, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "ecutwfc" in line:
                lines[i] = f"    ecutwfc = {ecutwfc},\n"
            if "ecutrho" in line:
                lines[i] = f"    ecutrho = {ecutwfc * 4},\n"
            if "CELL_PARAMETERS" in line:
                lines[i + 1] = f"{cell[0][0]*scale} {cell[0][1]*scale} {cell[0][2]*scale}\n"
                lines[i + 2] = f"{cell[1][0]*scale} {cell[1][1]*scale} {cell[1][2]*scale}\n"
                lines[i + 3] = f"{cell[2][0]*scale} {cell[2][1]*scale} {cell[2][2]*scale}\n"
            if "K_POINTS" in line:
                lines[i + 1] = f"{kpoints[0]} {kpoints[1]} {kpoints[2]} 0 0 0\n"

        new_name = f"{prefix}_{scale}.pwi"
        job_list.append(new_name)
        with open(os.path.join(wd, new_name), "w") as f:
            f.writelines(lines)

    job_list = sorted(set(job_list))
    return f"EOS test scripts generated. Files: {job_list}. Submit them via the HPC server or run_jobs_locally."


# ── Post-processing / analysis tools ─────────────────────────────────────


@mcp.tool()
def get_kspacing_ecutwfc(
    job_files: list[str],
    threshold: float = 1.0,
) -> str:
    """
    Determine optimal kspacing and ecutwfc from convergence test results.

    Reads the jobs_K_and_ecut.json sidecar written by generate_convergence_test
    to recover each job's (kspacing, ecutwfc), and reads energies from the .pwo
    output files.

    Args:
        job_files: List of .pwi filenames from the convergence test
        threshold: Convergence threshold in meV/atom (default 1.0)
    """
    wd = get_working_dir()
    sidecar = os.path.join(wd, "jobs_K_and_ecut.json")
    if not os.path.exists(sidecar):
        return "jobs_K_and_ecut.json not found. Run generate_convergence_test first."
    with open(sidecar, "r") as f:
        job_dict = json.load(f)

    kspacing_vals, ecutwfc_vals, energies, good_jobs = [], [], [], []
    n_atoms = None

    for job in job_files:
        if job not in job_dict:
            return f"Job {job} not in jobs_K_and_ecut.json. Was it generated by generate_convergence_test?"
        try:
            atom = read(os.path.join(wd, job + ".pwo"))
        except Exception:
            continue
        energies.append(atom.get_potential_energy())
        n_atoms = atom.get_number_of_atoms()
        kspacing_vals.append(job_dict[job]["k"])
        ecutwfc_vals.append(job_dict[job]["ecutwfc"])
        good_jobs.append(job)

    if len(set(kspacing_vals)) <= 1 and len(set(ecutwfc_vals)) <= 1:
        return "Too few converged jobs. Regenerate the convergence test with finer settings."
    if len(set(kspacing_vals)) == 1:
        return "Only one kspacing converged. Regenerate with finer kspacing."
    if len(set(ecutwfc_vals)) == 1:
        return "Only one ecutwfc converged. Regenerate with finer ecutwfc."

    df = pd.DataFrame({"job": good_jobs, "kspacing": kspacing_vals, "ecutwfc": ecutwfc_vals, "energy": energies})
    df.to_csv(os.path.join(wd, "convergence_test.csv"), index=False)

    k_chosen, ecut_chosen, finer_ecut, df_k, df_e, finer_k = select_k_ecut(df, threshold, n_atoms)

    df_k.to_csv(os.path.join(wd, "df_k.csv"), index=False)
    df_e.to_csv(os.path.join(wd, "df_e.csv"), index=False)

    if finer_ecut and ecut_chosen < 120 and finer_k and k_chosen > 0.1:
        return "Only the finest settings converged. Regenerate with finer ecutwfc AND kspacing."
    if finer_ecut and ecut_chosen < 120:
        return "Only the finest ecutwfc converged. Regenerate with finer ecutwfc."
    if finer_k and k_chosen > 0.1:
        return "Only the finest kspacing converged. Regenerate with finer kspacing."
    return f"Use kspacing {k_chosen} and ecutwfc {ecut_chosen} for production calculations."


@mcp.tool()
def read_energy_from_output(job_files: list[str]) -> str:
    """
    Read total energies from finished QE output files.

    Args:
        job_files: List of .pwi filenames whose .pwo outputs should be read
    """
    wd = get_working_dir()

    result = ""
    for job in job_files:
        path = os.path.join(wd, job + ".pwo")
        if not os.path.exists(path):
            return f"Output file {job}.pwo does not exist."
        try:
            atoms = read(path)
            result += f"Energy from {job}: {atoms.get_potential_energy()} eV\n"
        except Exception:
            with open(path, "r") as f:
                text = f.read()
            if "convergence NOT achieved" in text:
                result += f"Job {job} did not converge.\n"
            else:
                return f"Failed to read {job}.pwo. Resubmit the job."
    return result


@mcp.tool()
def calculate_lattice_constant(job_files: list[str]) -> str:
    """
    Calculate lattice constant by fitting an equation of state to volume/energy data.

    Args:
        job_files: List of .pwi filenames for the EOS jobs
    """
    wd = get_working_dir()

    volumes, energies = [], []
    last_atom = None
    for job in job_files:
        try:
            atom = read(os.path.join(wd, job + ".pwo"))
        except Exception:
            return f"Job {job} is not finished or failed."
        volumes.append(atom.get_volume())
        energies.append(atom.get_potential_energy())
        last_atom = atom

    plt.plot(volumes, energies, "o-")
    plt.xlabel("Volume (A^3)")
    plt.ylabel("Energy (eV)")
    plt.title("Volume vs Energy")
    plt.savefig(os.path.join(wd, "volume_vs_energy.png"))
    plt.close()

    eos = EquationOfState(volumes, energies)
    v0, e0, B = eos.fit()
    lc = v0 ** (1 / 3)

    # Persist to a JSON ledger
    json_file = os.path.join(wd, "..", "lattice_constant.json")
    lc_dict = {}
    if os.path.exists(json_file):
        with open(json_file, "r") as f:
            try:
                lc_dict = json.load(f)
            except Exception:
                pass
    lc_dict[str(last_atom.symbols)] = lc
    with open(json_file, "w") as f:
        json.dump(lc_dict, f)

    return f"The lattice constant is {lc} Angstrom"


@mcp.tool()
def calculate_formation_energy(
    slab_file: str,
    adsorbate_file: str,
    system_file: str,
) -> str:
    """
    Calculate adsorption/formation energy: E_system - N_slab*E_slab_per_atom - E_adsorbate.

    Args:
        slab_file: Slab calculation filename (ending in .pwi, without .pwo)
        adsorbate_file: Adsorbate calculation filename (ending in .pwi)
        system_file: Slab+adsorbate calculation filename (ending in .pwi)
    """
    wd = get_working_dir()
    slab = read(os.path.join(wd, slab_file + ".pwo"))
    adsorbate = read(os.path.join(wd, adsorbate_file + ".pwo"))
    system = read(os.path.join(wd, system_file + ".pwo"))

    slab_e_per_atom = slab.get_potential_energy() / len(slab)
    ads_e = adsorbate.get_potential_energy()
    sys_e = system.get_potential_energy()

    slab_species = slab.numbers[0]
    n_slab_in_system = system.numbers.tolist().count(slab_species)
    formation_e = sys_e - slab_e_per_atom * n_slab_in_system - ads_e
    return f"The formation energy is {formation_e} eV"


@mcp.tool()
def get_convergence_suggestions(
    filename: str,
    question: str,
) -> str:
    """
    Analyze a QE job that had issues (didn't converge, inaccurate) and suggest fixes.
    Reads the .pwi and .pwo files and provides expert suggestions.

    Args:
        filename: QE input filename ending in .pwi
        question: Your question (e.g. 'Why did this job not converge?')
    """
    wd = get_working_dir()
    suggestion = ""

    for ext in [filename, filename + ".pwo"]:
        path = os.path.join(wd, ext)
        if os.path.exists(path):
            with open(path, "r") as f:
                content = f.read()
            suggestion += f"\n--- Content of {ext} ---\n{content[:5000]}\n"

    if not suggestion:
        return f"No files found for {filename}. Check that the job has run."

    suggestion += (
        f"\nQuestion: {question}\n"
        "Please analyze the input/output above and suggest parameter changes to fix the issue. "
        "Never suggest lowering accuracy (e.g. loosening conv_thr)."
    )
    return suggestion


@mcp.tool()
def analyze_beef_result(
    slab_file: str,
    adsorbate_file: str,
    ontop_file: str,
    fcc_file: str,
) -> str:
    """
    Analyze BEEF-vdW ensemble results for adsorption energy uncertainty.

    Args:
        slab_file: Clean slab BEEF calculation file
        adsorbate_file: Adsorbate-only BEEF calculation file
        ontop_file: Slab+adsorbate (ontop site) BEEF calculation file
        fcc_file: Slab+adsorbate (fcc site) BEEF calculation file
    """
    wd = get_working_dir()
    dir_name = wd.split("/")[-1]

    paths = [slab_file, adsorbate_file, ontop_file, fcc_file]
    resolved = []
    for p in paths:
        r = p
        if not r.startswith(dir_name) and not r.startswith(f"./{dir_name}") and not r.startswith("/"):
            r = os.path.join(wd, r) + ".pwo"
        resolved.append(r)
        try:
            read(r)
        except Exception:
            if os.path.exists(r):
                return f"{p} did not finish successfully."
            return f"Invalid path: {p}."

    slab_e = read_BEEF_output(resolved[0])
    if slab_e == "WrongCalc":
        return "Run slab ensemble with BEEF-vdW on relaxed structure first."
    ads_e = read_BEEF_output(resolved[1])
    if ads_e == "WrongCalc":
        return "Run adsorbate ensemble with BEEF-vdW on relaxed structure first."
    ontop_e = read_BEEF_output(resolved[2])
    if ontop_e == "WrongCalc":
        return "Run ontop ensemble with BEEF-vdW on relaxed structure first."
    fcc_e = read_BEEF_output(resolved[3])
    if fcc_e == "WrongCalc":
        return "Run fcc ensemble with BEEF-vdW on relaxed structure first."

    # Plot
    try:
        ads_fcc = fcc_e - slab_e - ads_e
        ads_ontop = ontop_e - slab_e - ads_e
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.hist(ads_fcc, bins=50, color="blue", alpha=0.7, label="FCC")
        ax.axvline(ads_fcc.mean(), color="k", linestyle=":", linewidth=2, label="FCC mean")
        ax.hist(ads_ontop, bins=50, color="red", alpha=0.7, label="Ontop")
        ax.axvline(ads_ontop.mean(), color="k", linestyle="-.", linewidth=2, label="Ontop mean")
        plt.legend()
        plt.xlabel("Adsorption Energy (eV)")
        plt.ylabel("Frequency")
        plt.savefig(os.path.join(wd, "energy_distribution.png"), dpi=300, bbox_inches="tight")
        plt.close()
    except Exception:
        pass

    ontop_form = ontop_e - slab_e - ads_e
    fcc_form = fcc_e - slab_e - ads_e
    diff = ontop_form - fcc_form

    if diff.all() > 0:
        return f"FCC is more stable than ontop by average {diff.mean():.4f} eV"
    elif diff.all() < 0:
        return f"Ontop is more stable than FCC by average {abs(diff.mean()):.4f} eV"
    return f"{sum(diff > 0)} functionals prefer FCC, {sum(diff < 0)} prefer ontop"


@mcp.tool()
def get_files_in_dir(dir_path: str, file_extension: str = "") -> str:
    """
    List files in a subdirectory of the working directory.

    Args:
        dir_path: Relative directory path within the working directory
        file_extension: Filter by extension (e.g. '.pwi'). Empty string for all files.
    """
    wd = get_working_dir()
    full_path = os.path.join(wd, dir_path)
    files = []
    for f in os.listdir(full_path):
        if f.endswith(file_extension):
            files.append(f)
    return "\n".join(files) if files else "No matching files found."


@mcp.tool()
def read_file(input_file: str) -> str:
    """
    Read the contents of a file in the working directory.

    Args:
        input_file: Filename relative to the working directory
    """
    wd = get_working_dir()
    path = os.path.join(wd, input_file)
    with open(path, "r") as f:
        return f.read()


# ── Local job execution ────────────────────────────────────────────────────


@mcp.tool()
async def run_jobs_locally(job_files: list[str], nprocs: int = 1) -> str:
    """
    Run QE jobs locally using pw.x on this machine.

    Runs each job sequentially with `mpirun -np nprocs pw.x` (or plain pw.x if
    nprocs=1). Use this when you don't have access to an HPC cluster.

    Args:
        job_files: List of .pwi filenames in the working directory to run.
        nprocs: Number of MPI processes to use (default 1).
    """
    import asyncio
    import shutil

    wd = get_working_dir()
    if not job_files:
        return "No jobs provided."

    pw_x = shutil.which("pw.x")
    if pw_x is None:
        return "pw.x not found in PATH. Install Quantum ESPRESSO first."

    use_mpi = nprocs > 1 and shutil.which("mpirun") is not None
    original_jobs = list(job_files)
    succeeded = []
    failed = []

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"

    for job in original_jobs:
        input_path = os.path.join(wd, job)
        output_path = input_path + ".pwo"

        if not os.path.exists(input_path):
            failed.append((job, "input file not found"))
            continue

        if os.path.exists(output_path):
            # Already has output — treat as done
            succeeded.append(job)
            continue

        if use_mpi:
            cmd = ["mpirun", "-np", str(nprocs), pw_x, "-i", input_path]
        else:
            cmd = [pw_x, "-i", input_path]

        try:
            with open(output_path, "w") as out_f:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=out_f, stderr=asyncio.subprocess.PIPE,
                    cwd=wd, env=env,
                )
                try:
                    _, stderr = await asyncio.wait_for(proc.communicate(), timeout=3600)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    failed.append((job, "timed out after 3600s"))
                    continue
            if proc.returncode != 0:
                failed.append((job, stderr.decode()[-500:]))
            else:
                succeeded.append(job)
        except Exception as e:
            failed.append((job, str(e)))

    msg = f"{len(succeeded)}/{len(original_jobs)} jobs succeeded."
    if failed:
        fail_details = "; ".join(f"{j}: {err[:100]}" for j, err in failed)
        msg += f" Failed: {fail_details}"
    return msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Force initialization so config errors surface immediately
    get_working_dir()
    mcp.run(transport="stdio")

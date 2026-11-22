"""AtomAgents MCP Server — exposes LAMMPS simulation tools and resources."""

import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .config import get_atomagents_root

# --- Tool implementations ---
from .tools.setup import create_working_folder, create_potential_file, create_crystal
from .tools.lattice import lattice_constant_simulation
from .tools.elastic import elastic_constant_simulation
from .tools.surface import surface_energy_simulation
from .tools.stacking_fault import stacking_fault_simulation
from .tools.dislocation import create_screw_dislocation, neb_screw_simulation
from .tools.fracture import critical_stress_intensity
from .tools.utilities import suggest_orientation, list_potentials

# --- Resource implementations ---
from .resources.potentials import list_all_potentials, get_potential_metadata
from .resources.templates import list_templates, get_template_content
from .resources.results import list_result_files, read_result_file
from .resources.reference import list_reference_images, get_reference_image_path


server = Server("atomagents-simulations")


# ============================================================
# Tool definitions
# ============================================================

TOOL_DEFINITIONS = [
    Tool(
        name="create_working_folder",
        description="Create a working directory for simulation output. Choose a descriptive name for the project.",
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {
                    "type": "string",
                    "description": "A descriptive name for the project's working directory."
                }
            },
            "required": ["working_folder"]
        }
    ),
    Tool(
        name="create_potential_file",
        description=(
            "Write the LAMMPS potential.inp configuration file. "
            "Use ../potential_repository/ before the potential file name. "
            "Examples: pair_style='eam/alloy', pair_coeff='* * ../potential_repository/Al99.eam.alloy Al' for EAM; "
            "pair_style='mlip ../potential_repository/NbMo.mtp', pair_coeff='* *' for MTP."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {
                    "type": "string",
                    "description": "Working directory for the project."
                },
                "pair_style_text": {
                    "type": "string",
                    "description": "LAMMPS pair_style, e.g. 'eam/alloy', 'eam/fs', 'meam', or 'mlip ../potential_repository/NbMo.mtp'."
                },
                "pair_coeff_text": {
                    "type": "string",
                    "description": "LAMMPS pair_coeff arguments. Use ../potential_repository/ before potential filenames. E.g. '* * ../potential_repository/Al99.eam.alloy Al'."
                }
            },
            "required": ["working_folder", "pair_style_text", "pair_coeff_text"]
        }
    ),
    Tool(
        name="create_crystal",
        description=(
            "Generate an FCC or BCC crystal structure as a LAMMPS data file. "
            "The lattice constant should be computed by lattice_constant_simulation first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string", "description": "Working directory."},
                "output_name": {"type": "string", "description": "Output filename (use .lmp extension)."},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"], "description": "Lattice type."},
                "lat_const": {"type": "number", "description": "Lattice constant in Angstrom."},
                "conc_1": {"type": "integer", "description": "Concentration of first element in %."},
                "conc_2": {"type": "integer", "description": "Concentration of second element in %. 0 for unary non-MTP."},
                "mtp_pot": {"type": "boolean", "description": "True for MTP potential, False otherwise."},
                "orient_x": {"type": "array", "items": {"type": "integer"}, "description": "Crystal orientation along x, e.g. [1, -1, 1]."},
                "orient_y": {"type": "array", "items": {"type": "integer"}, "description": "Crystal orientation along y."},
                "orient_z": {"type": "array", "items": {"type": "integer"}, "description": "Crystal orientation along z."},
                "size_x": {"type": "integer", "description": "Crystal size in lattice units along x."},
                "size_y": {"type": "integer", "description": "Crystal size in lattice units along y."},
                "size_z": {"type": "integer", "description": "Crystal size in lattice units along z."}
            },
            "required": ["working_folder", "output_name", "lat_type", "lat_const",
                         "conc_1", "conc_2", "mtp_pot", "orient_x", "orient_y", "orient_z",
                         "size_x", "size_y", "size_z"]
        }
    ),
    Tool(
        name="lattice_constant_simulation",
        description=(
            "Compute the equilibrium lattice constant via energy minimization and pressure relaxation. "
            "The potential file must already exist (created by create_potential_file)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string", "description": "Working directory for results."},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"], "description": "Lattice type."},
                "lat_const_guess": {"type": "number", "description": "Approximate lattice constant guess in Angstrom."},
                "conc_1": {"type": "integer", "description": "Concentration of first element in %."},
                "conc_2": {"type": "integer", "description": "Concentration of second element in %. 0 for unary non-MTP."},
                "mtp_pot": {"type": "boolean", "description": "True for MTP potential."},
                "num_cpus": {"type": "integer", "description": "Number of MPI CPUs (default 4).", "default": 4},
                "thermo_time": {"type": "integer", "description": "Thermo output interval.", "default": 100},
                "dump_time": {"type": "integer", "description": "Dump output interval.", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "lat_const_guess", "conc_1", "conc_2", "mtp_pot"]
        }
    ),
    Tool(
        name="elastic_constant_simulation",
        description=(
            "Compute elastic constants (C11, C12, C44, etc.) in GPa via LAMMPS. "
            "Requires the potential file and the displace.mod template in 0_codes/."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string", "description": "Working directory."},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"], "description": "Lattice type."},
                "a": {"type": "number", "description": "Equilibrium lattice constant."},
                "conc_1": {"type": "integer", "description": "Concentration of first element in %."},
                "conc_2": {"type": "integer", "description": "Concentration of second element in %."},
                "mtp_pot": {"type": "boolean", "description": "True for MTP potential."},
                "thermo_time": {"type": "integer", "default": 100},
                "dump_time": {"type": "integer", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "a", "conc_1", "conc_2", "mtp_pot"]
        }
    ),
    Tool(
        name="surface_energy_simulation",
        description=(
            "Compute surface energy for a crystal plane in eV/A^2 and J/m^2. "
            "For crack problems, use the crack plane as the surface orientation. "
            "Each plane's result is also appended to <working_folder>/surface_energies.csv."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string"},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"]},
                "lat_const": {"type": "number", "description": "Lattice constant from lattice_constant_simulation."},
                "conc_1": {"type": "integer"},
                "conc_2": {"type": "integer"},
                "mtp_pot": {"type": "boolean"},
                "orient_x": {"type": "array", "items": {"type": "integer"}},
                "orient_y": {"type": "array", "items": {"type": "integer"}},
                "orient_z": {"type": "array", "items": {"type": "integer"}},
                "surface_orientation": {"type": "array", "items": {"type": "integer"}, "description": "Target free surface plane."},
                "surface_dir": {"type": "string", "enum": ["x", "y", "z"], "description": "Which axis is the surface direction."},
                "L_periodic": {"type": "number", "default": 30, "description": "Cell length along periodic directions (A)."},
                "L_free": {"type": "number", "default": 60, "description": "Cell length along free direction (A)."},
                "thermo_time": {"type": "integer", "default": 100},
                "dump_time": {"type": "integer", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "lat_const", "conc_1", "conc_2",
                         "mtp_pot", "orient_x", "orient_y", "orient_z",
                         "surface_orientation", "surface_dir"]
        }
    ),
    Tool(
        name="stacking_fault_simulation",
        description=(
            "Compute the generalized stacking fault energy curve. "
            "Returns relative shifts and potential energy per area in meV/A^2 and mJ/m^2."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string"},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"]},
                "a": {"type": "number", "description": "Lattice constant."},
                "conc_1": {"type": "integer"},
                "conc_2": {"type": "integer"},
                "mtp_pot": {"type": "boolean"},
                "orient_x": {"type": "array", "items": {"type": "integer"}, "description": "Shearing direction."},
                "orient_y": {"type": "array", "items": {"type": "integer"}},
                "orient_z": {"type": "array", "items": {"type": "integer"}, "description": "Stacking fault plane direction."},
                "shift_num": {"type": "integer", "default": 21, "description": "Number of points along SFE curve."},
                "thermo_time": {"type": "integer", "default": 100},
                "dump_time": {"type": "integer", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "a", "conc_1", "conc_2",
                         "mtp_pot", "orient_x", "orient_y", "orient_z"]
        }
    ),
    Tool(
        name="create_screw_dislocation",
        description=(
            "Create and relax a screw dislocation, producing a differential displacement (DD) map. "
            "Creates its own crystal structure internally."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string"},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"]},
                "lat_const": {"type": "number", "description": "Lattice constant from lattice_constant_simulation."},
                "conc_1": {"type": "integer"},
                "conc_2": {"type": "integer"},
                "mtp_pot": {"type": "boolean"},
                "orient_x": {"type": "array", "items": {"type": "integer"}, "description": "Dislocation glide direction, e.g. [1, 1, -2]."},
                "orient_y": {"type": "array", "items": {"type": "integer"}, "description": "Normal to dislocation plane, e.g. [1, 1, 0]."},
                "orient_z": {"type": "array", "items": {"type": "integer"}, "description": "Dislocation line direction, e.g. [1, 1, 1]."},
                "size_x": {"type": "integer", "default": 5},
                "size_y": {"type": "integer", "default": 7},
                "size_z": {"type": "integer", "default": 2},
                "thermo_time": {"type": "integer", "default": 100},
                "dump_time": {"type": "integer", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "lat_const", "conc_1", "conc_2",
                         "mtp_pot", "orient_x", "orient_y", "orient_z"]
        }
    ),
    Tool(
        name="neb_screw_simulation",
        description=(
            "Run NEB simulations to compute the Peierls barrier of a screw dislocation. "
            "Returns mean and std of barrier distribution in meV."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "working_folder": {"type": "string"},
                "lat_type": {"type": "string", "enum": ["fcc", "bcc"]},
                "lat_const": {"type": "number"},
                "orient_x": {"type": "array", "items": {"type": "integer"}},
                "orient_y": {"type": "array", "items": {"type": "integer"}},
                "orient_z": {"type": "array", "items": {"type": "integer"}},
                "size_x": {"type": "integer"},
                "size_y": {"type": "integer"},
                "size_z": {"type": "integer"},
                "conc_1": {"type": "integer"},
                "conc_2": {"type": "integer"},
                "mtp_pot": {"type": "boolean"},
                "system_name": {"type": "string", "description": "Name label, e.g. 'Nb' or 'Nb10W90'."},
                "seed_num": {"type": "integer", "description": "Random seed."},
                "num_replicas": {"type": "integer", "default": 10},
                "num_cpus": {"type": "integer", "default": 20},
                "num_samples": {"type": "integer", "default": 5, "description": "Random alloy samples (1 for unary)."},
                "thermo_time": {"type": "integer", "default": 100},
                "dump_time": {"type": "integer", "default": 1000}
            },
            "required": ["working_folder", "lat_type", "lat_const",
                         "orient_x", "orient_y", "orient_z",
                         "size_x", "size_y", "size_z",
                         "conc_1", "conc_2", "mtp_pot",
                         "system_name", "seed_num"]
        }
    ),
    Tool(
        name="critical_stress_intensity",
        description=(
            "Compute the critical stress intensity for cleavage (KIc) in MPa*m^0.5. "
            "Requires elastic constants (C11, C12, C44 in GPa) and surface energy (J/m^2)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "orient_x": {"type": "array", "items": {"type": "number"}, "description": "Crack propagation direction."},
                "orient_y": {"type": "array", "items": {"type": "number"}, "description": "Crack normal plane direction."},
                "orient_z": {"type": "array", "items": {"type": "number"}, "description": "Crack front direction."},
                "c11": {"type": "number", "description": "C11 elastic constant in GPa."},
                "c12": {"type": "number", "description": "C12 elastic constant in GPa."},
                "c44": {"type": "number", "description": "C44 elastic constant in GPa."},
                "gamma_s": {"type": "number", "description": "Surface energy in J/m^2 along crack plane."}
            },
            "required": ["orient_x", "orient_y", "orient_z", "c11", "c12", "c44", "gamma_s"]
        }
    ),
    Tool(
        name="suggest_orientation",
        description="Compute orthogonal crystal orientations given one or two known orientations.",
        inputSchema={
            "type": "object",
            "properties": {
                "orientation": {
                    "type": "array",
                    "description": "One or two crystal orientations. Single: [1,1,0]. Two: [[1,1,0],[0,0,1]]."
                }
            },
            "required": ["orientation"]
        }
    ),
    Tool(
        name="list_potentials",
        description="List all available interatomic potential files with their types and usage hints.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
]


# ============================================================
# Tool dispatch
# ============================================================

TOOL_HANDLERS = {
    "create_working_folder": lambda args: create_working_folder(**args),
    "create_potential_file": lambda args: create_potential_file(**args),
    "create_crystal": lambda args: create_crystal(**args),
    "lattice_constant_simulation": lambda args: lattice_constant_simulation(**args),
    "elastic_constant_simulation": lambda args: elastic_constant_simulation(**args),
    "surface_energy_simulation": lambda args: surface_energy_simulation(**args),
    "stacking_fault_simulation": lambda args: stacking_fault_simulation(**args),
    "create_screw_dislocation": lambda args: create_screw_dislocation(**args),
    "neb_screw_simulation": lambda args: neb_screw_simulation(**args),
    "critical_stress_intensity": lambda args: critical_stress_intensity(**args),
    "suggest_orientation": lambda args: suggest_orientation(**args),
    "list_potentials": lambda args: list_potentials(),
}


@server.list_tools()
async def handle_list_tools():
    return TOOL_DEFINITIONS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None):
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    try:
        # Change to AtomAgents root so relative paths work
        root = get_atomagents_root()
        original_cwd = os.getcwd()
        os.chdir(root)

        result = handler(arguments or {})

        os.chdir(original_cwd)

        return [TextContent(type="text", text=str(result))]
    except Exception as e:
        os.chdir(original_cwd)
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {e}")]


# ============================================================
# Resource definitions
# ============================================================

@server.list_resources()
async def handle_list_resources():
    return [
        Resource(
            uri="atomagents://potentials",
            name="Interatomic Potentials",
            description="List all available interatomic potential files with metadata and usage hints.",
            mimeType="application/json",
        ),
        Resource(
            uri="atomagents://templates",
            name="LAMMPS Templates",
            description="List LAMMPS template files (displace.mod, etc.).",
            mimeType="application/json",
        ),
        Resource(
            uri="atomagents://reference/screw-cores",
            name="Screw Dislocation Reference Cores",
            description="Reference images for dislocation core structure identification.",
            mimeType="application/json",
        ),
    ]


@server.list_resource_templates()
async def handle_list_resource_templates():
    return [
        ResourceTemplate(
            uriTemplate="atomagents://potentials/{name}",
            name="Potential Metadata",
            description="Metadata and usage hints for a specific interatomic potential.",
            mimeType="application/json",
        ),
        ResourceTemplate(
            uriTemplate="atomagents://templates/{name}",
            name="Template Content",
            description="Contents of a specific LAMMPS template file.",
            mimeType="text/plain",
        ),
        ResourceTemplate(
            uriTemplate="atomagents://results/{folder}",
            name="Simulation Results Folder",
            description="List files in a simulation results folder.",
            mimeType="application/json",
        ),
        ResourceTemplate(
            uriTemplate="atomagents://results/{folder}/{file}",
            name="Simulation Result File",
            description="Read a specific simulation result file.",
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri):
    uri_str = str(uri)

    # Static resources
    if uri_str == "atomagents://potentials":
        return list_all_potentials()
    elif uri_str == "atomagents://templates":
        return list_templates()
    elif uri_str == "atomagents://reference/screw-cores":
        return list_reference_images()

    # Parameterized resources
    if uri_str.startswith("atomagents://potentials/"):
        name = uri_str.split("atomagents://potentials/", 1)[1]
        return get_potential_metadata(name)

    elif uri_str.startswith("atomagents://templates/"):
        name = uri_str.split("atomagents://templates/", 1)[1]
        return get_template_content(name)

    elif uri_str.startswith("atomagents://results/"):
        path = uri_str.split("atomagents://results/", 1)[1]
        parts = path.split("/", 1)
        if len(parts) == 1:
            return list_result_files(parts[0])
        else:
            return read_result_file(parts[0], parts[1])

    return json.dumps({"error": f"Unknown resource URI: {uri_str}"})


# ============================================================
# Entry point
# ============================================================

async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()

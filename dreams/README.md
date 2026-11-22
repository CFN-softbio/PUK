# DREAMS → PUK (MCP servers)

Port of [DREAMS](https://github.com/BattModels/material_agent) (Wang et al.; LangGraph) to two MCP servers for
Quantum ESPRESSO DFT workflows. The Supervisor, the two ReAct workers, the state graph and the shared CANVAS are removed;
the Convergence Agent's embedded LLM call is replaced by a tool that returns the QE input and output for the coding agent to read.
Tool logic follows upstream commit `99c9d71`.

| Server | Tools |
|---|---|
| `dreams-dft` (17) | `init_structure_data`, `generate_surface_and_get_sites`, `generate_adsorbate`, `add_adsorbate_to_surface`, `find_pseudopotential`, `write_qe_script`, `generate_convergence_test`, `generate_eos_test`, `get_kspacing_ecutwfc`, `read_energy_from_output`, `calculate_lattice_constant`, `calculate_formation_energy`, `get_convergence_suggestions`, `analyze_beef_result`, `get_files_in_dir`, `read_file`, `run_jobs_locally` |
| `dreams-hpc` (3) | `read_file`, `add_resource_suggestion`, `submit_and_monitor_jobs` (SLURM via pysqa) |

## Layout

```
mcp_servers/        dft_server.py, hpc_server.py, shared.py
config/default.yaml PSEUDO_DIR and WORKING_DIR (relative to this directory)
pseudopotentials/   UPF files (not included; see below)
out/                Working directory for DFT jobs
experiments/        Prompts, outputs and analysis for each reproduced experiment
.mcp.json           Claude Code MCP registration
```

## Setup

```bash
conda env create -f environment.yml && conda activate puks-dreams
# Quantum ESPRESSO (pw.x) on PATH — the experiments used QE 7.5
mkdir -p pseudopotentials   # add UPF files, e.g. GBRV li_pbe_v1.4.uspp.F.UPF
claude                      # launched from this directory
```

The BCC Li run used the GBRV ultrasoft pseudopotential `li_pbe_v1.4.uspp.F.UPF`
(Garrity, Bennett, Rabe & Vanderbilt, Comput. Mater. Sci. 81, 446 (2014); https://www.physics.rutgers.edu/gbrv/).

`dreams-hpc` targets the original authors' SLURM cluster (partition names in `hpc_server.py`); local runs use `run_jobs_locally`.

## Experiments

| Folder | Paper | Prompt |
|---|---|---|
| `experiments/lattice-bcc-li/` | §2.1.3, Table 6, Fig. 3 | [prompt.md](experiments/lattice-bcc-li/prompt.md) |

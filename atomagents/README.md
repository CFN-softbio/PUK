# AtomAgents → PUK (MCP server)

Port of [AtomAgents](https://github.com/lamm-mit/AtomAgents) (Ghafarollahi & Buehler; AutoGen) to a single MCP server,
`atomagents-simulations`, with 12 tools. The LAMMPS scripts are taken unchanged from the original `AtomAgents.py`
(upstream commit `b0ef01f`). The 14 agents, nested group chats, RAG pipeline and the 11 orchestration-only functions are removed.

| Module | Tools |
|---|---|
| setup | `create_working_folder`, `create_potential_file`, `create_crystal` |
| utilities | `suggest_orientation`, `list_potentials` |
| lattice / elastic / surface / stacking_fault | `lattice_constant_simulation`, `elastic_constant_simulation`, `surface_energy_simulation`, `stacking_fault_simulation` |
| dislocation | `create_screw_dislocation`, `neb_screw_simulation` |
| fracture | `critical_stress_intensity` |

## Layout

```
atomagents-mcp/          Python package (server, tools, helpers)
potential_repository/    Interatomic potentials used in the experiments (see below)
0_codes/displace.mod     LAMMPS elastic-constant helper (from AtomAgents)
experiments/             Prompts, outputs and transcripts for each reproduced experiment
.mcp.json                Claude Code MCP registration
```

## Setup

Requirements: Python ≥ 3.10, LAMMPS on `PATH` as `lmp` (or `lmp_mpi`/`lmp_serial`) with `mpirun`.
The NbMo experiment needs LAMMPS built with the [MLIP-2](https://gitlab.com/ashapeev/mlip-2) interface (`pair_style mlip`).

```bash
pip install -e atomagents-mcp
claude          # launched from this directory; .mcp.json sets ATOMAGENTS_ROOT=.
```

Simulation folders are created in this directory.

## Experiments

| Folder | Paper | Prompt |
|---|---|---|
| `experiments/screw-dislocation-W/` | §2.1.1, Fig. 1 | [prompt.md](experiments/screw-dislocation-W/prompt.md) |
| `experiments/exp5-al-ni/` | App. B.1, Table 15 | [prompt.md](experiments/exp5-al-ni/prompt.md) |
| `experiments/exp6-nbmo/` | App. B.2, Table 16, Fig. 6 | [prompt.md](experiments/exp6-nbmo/prompt.md) |

## Potentials

Redistributed from the AtomAgents repository (Apache-2.0); cite the original authors.

| File | Source |
|---|---|
| `Al99.eam.alloy`, `Ni99.eam.alloy` | Mishin et al., Phys. Rev. B 59, 3393 (1999); NIST Interatomic Potentials Repository |
| `W_Zhou04.eam.alloy` | Zhou, Johnson & Wadley, Phys. Rev. B 69, 144113 (2004); NIST Interatomic Potentials Repository |
| `w_eam4.fs` | W EAM4 Finnis–Sinclair potential as distributed with AtomAgents |
| `NbMo.mtp` → `quaternary.mtp` | Moment tensor potential as distributed with AtomAgents |

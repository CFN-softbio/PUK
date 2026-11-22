# LAMMPS-Agents → PUK (MCP servers)

Port of [LAMMPS-Agents](https://github.com/ANL-NST/LAMMPS-Agents) (Vriza et al.; AutoGen/AG2) to seven MCP servers
exposing 31 tools. The group chat, speaker selection, the eleven agent roles and their system prompts, the reviewer loop
and the vision models are removed. Ported from upstream commit `2501f01` (MIT).

```
mcp-servers/
  structure-server/       crystal/alloy creation (ASE, atomsk)
  potential-server/       download EAM/SW/Tersoff potentials, OpenKIM, validation
  lammps-input-server/    LAMMPS inputs for lattice, elastic and melting calculations
  lammps-executor-server/ runs `lmp` locally
  results-server/         parses log.lammps; extracts lattice/elastic constants
  visualization-server/   OVITO renders, melting and elastic plots
  phonopy-server/         phonopy finite-displacement phonon dispersion
workspace/                simulation artifacts (git-ignored)
experiments/              prompts, outputs and transcripts for each reproduced experiment
.mcp.json                 Claude Code MCP registration
```

## Setup

- Python ≥ 3.10 with the packages in `mcp-servers/*/requirements.txt` (`mcp`, `ase`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `imageio`, `pyyaml`, `phonopy`; `ovito` optional)
- On `PATH`: `lmp` (LAMMPS), `atomsk`, `phonopy`. Override with `LAMMPS_PATH`, `ATOMSK_PATH`, `PHONOPY_PATH`.

```bash
claude          # launched from this directory; servers write to ./workspace
```

## Experiments

| Folder | Paper | Prompt |
|---|---|---|
| `experiments/melting-nicu/` | §2.1.2, Table 4, Fig. 2 | [prompt.md](experiments/melting-nicu/prompt.md) |
| `experiments/elastic-au/` | App. B.3, Table 17, Fig. 7 | [prompt.md](experiments/elastic-au/prompt.md) |
| `experiments/phonon-au/` | App. B.4, Fig. 8 | [prompt.md](experiments/phonon-au/prompt.md) |

The Au, Ni and Cu `*_u3.eam` potentials in the experiment folders are the Foiles, Baskes & Daw funcfl files
(Phys. Rev. B 33, 7983 (1986)) from the LAMMPS `potentials/` directory; the elastic-constant input templates
are from LAMMPS `examples/ELASTIC`. Both are distributed with LAMMPS under GPL-2.0.

# Portable Units of Knowledge

Code and data for *Portable Units of Knowledge for Framework-Free Scientific Agent Systems* (Mathur, 2026).

Four published multi-agent science systems are stripped of their orchestration layer and their scientific capabilities
are exposed as **Portable Units of Knowledge (PUKs)** — here, MCP servers — to a single coding agent (Claude Code).
Each case study contains the MCP server(s), the exact prompts used, and the outputs of every reproduced experiment.

| Case study | Original system | Framework | MCP servers / tools | Experiments |
|---|---|---|---|---|
| [`atomagents/`](atomagents/) | AtomAgents (Ghafarollahi & Buehler) | AutoGen | 1 / 12 | W screw dislocation; Al/Ni characterization; NbMo fracture toughness |
| [`lammps-agents/`](lammps-agents/) | LAMMPS-Agents (Vriza et al.) | AutoGen (AG2) | 7 / 31 | Ni–Cu melting point; Au elastic constants; Au phonon dispersion |
| [`dreams/`](dreams/) | DREAMS (Wang et al.) | LangGraph | 2 / 20 | BCC Li lattice constant |
| [`vision/`](vision/) | VISION (Mathur et al.) | Custom cogs | 1 / 37 | Natural-language beamline command (Box 1) |

## Running a case study

Each case-study directory is self-contained: install its dependencies (see its README), then launch Claude Code from that
directory so it picks up the local `.mcp.json`:

```bash
cd lammps-agents
claude
> Calculate the phonon dispersion for gold.
```

Re-runs recorded in this repository used headless sessions restricted to the case study's MCP servers:

```bash
claude -p "$(cat PROMPT.txt)" --model claude-opus-5-5 \
  --strict-mcp-config --mcp-config .mcp.json \
  --allowedTools <mcp servers> Read Write Edit Glob Grep Bash WebFetch WebSearch \
  --output-format stream-json --verbose > transcript.jsonl
```

## Experiment records

Every `experiments/<name>/` folder has a `prompt.md` with the prompt, how it was run, and a table of the output files.
Some runs also include the full session transcript (`transcript.jsonl`).
The four main-text experiments also have a `codex/` folder with the same experiment run in Codex using the same
MCP servers; see [`codex/README.md`](codex/README.md).

## Acknowledgements

The ports build on the original code of AtomAgents (Apache-2.0), LAMMPS-Agents (MIT), DREAMS / material_agent and VISION.
Interatomic potentials and LAMMPS input templates are credited in each case study's README.

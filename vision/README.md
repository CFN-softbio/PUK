# VISION → PUK (MCP server)

An MCP-server port of [VISION](https://github.com/CFN-softbio/VISION)'s beamline
cogs, built as a case study for the **PUKs** (Portable Units of Knowledge) paper.

VISION is a modular AI assistant for synchrotron-beamline operation (Mathur
et al. 2025). Its original implementation is an *assistant*: a `cog_manager`
dispatches natural-language input through hand-wired **workflows** that chain
specialized **cogs** (Transcriber → Classifier → Operator / Analyst / …),
communicating over MinIO, with per-cog dynamically-built system prompts.

This repo strips that orchestration and re-expresses the genuinely
domain-specific capability — the beamline API and analysis protocols — as a
single framework-agnostic **MCP server** (`server.py`). A frontier coding agent
(e.g. Claude Code) supplies the planning, control flow, tool selection, and
routing natively; no `cog_manager`, no workflows, and **no Classifier cog**.

## What maps to what

| VISION component | Status in the port | Replacement |
|---|---|---|
| Operator cog (NL → Bluesky code) | **Ported** | Hardware-control tools (beamline API) + `CLAUDE.md` conventions |
| Analyst cog (NL → SciAnalysis protocol) | **Ported** | Analysis-protocol tools |
| Note-taker / gpCAM / xiCAM hooks | **Ported** | `record_note` / `start_gpcam` / `launch_xicam` tools |
| Classifier cog (routing) | **Stripped** | Coding agent routes to the right tool natively |
| `cog_manager`, 3 workflows, MinIO queue | **Stripped** | Coding agent's native session/tool orchestration |
| Dynamic system-prompt builder | **Stripped** | Tool schemas + `CLAUDE.md` |
| Transcriber (fine-tuned Whisper) | Out of scope here | — |

## The server

One MCP server, `beamline` (`server.py`), whose tools are grouped by the cog
they replace:

- **Operator** — the 11-BM Bluesky/CMS API (`sam.measure`, `sam.xabs`,
  `sam.setLinkamTemperature`, `sam.align`, …). Each tool returns the canonical
  code snippet; the agent composes them (and writes any loops/conditionals).
- **Analyst** — SciAnalysis protocols (`circular_average`, `qr_image`,
  `linecut_qr`, …).
- **Notebook / gpCAM / xiCAM** — `record_note`, `start_gpcam`, `launch_xicam`.

## Install & run

```bash
pip install -e .          # installs mcp[cli]
python server.py          # stdio transport
```

Register it with a Claude Code session using the provided `.mcp.json` (place it
at the project root Claude Code is launched from, or import the entry into your
MCP config).

## Resources

- `resources/command_examples.json` — the Operator/Analyst command catalog (the PUK data).

## Experiments

| Folder | Paper | Prompt |
|---|---|---|
| `experiments/beamline-box1/` | §2.1.4, Fig. 4 | [prompt.md](experiments/beamline-box1/prompt.md) |

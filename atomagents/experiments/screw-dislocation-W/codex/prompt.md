# Screw dislocation in W (Codex)

**Paper:** Section 2.1.1
**Run:** Codex CLI 0.163.0 (`gpt-5.6-sol`), 2026-10-17, isolated session with the `atomagents-simulations` MCP server. Session log: `session.jsonl`

## Prompt

```
Compare the structure of 1/2⟨111⟩ screw dislocation in W using "W_Zhou04.eam.alloy" and "w_eam4.fs" EAM potentials. The dislocation line is aligned along [-1,1,1] direction, and dislocation glide and glide plane normal directions are [1,-1,2] and [1,1,0], respectively.
```

## Outputs

| Path | Contents |
|---|---|
| `W_screw_eam4/DD_plot.dislocated.initial.png` | Differential-displacement map, w_eam4 |
| `W_screw_Zhou04/DD_plot.dislocated.initial.png` | Differential-displacement map, W_Zhou04 |
| `*/relaxed_outputs.csv` | Bulk lattice relaxation |
| `*/dislocation.csv` | Relaxed dislocated cell (box, energy) |
| `*/lmp_*.in`, `*/log.lammps*` | LAMMPS inputs and logs |
| `session.jsonl` | Session log |

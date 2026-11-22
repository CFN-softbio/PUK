# Screw dislocation in W

**Paper:** Section 2.1.1, Figure 1(c,d)
**Run:** Claude Code, 2026-07-12, with the `atomagents-simulations` MCP server

## Prompt

```
Compare the structure of 1/2⟨111⟩ screw dislocation in W using "W_Zhou04.eam.alloy" and "w_eam4.fs" EAM potentials. The dislocation line is aligned along [-1,1,1] direction, and dislocation glide and glide plane normal directions are [1,-1,2] and [1,1,0], respectively.
```

## Outputs

| Path | Contents |
|---|---|
| `W_eam4_screw/DD_plot.dislocated.initial.png` | Differential-displacement map, compact core (Fig. 1c) |
| `W_Zhou04_screw/DD_plot.dislocated.initial.png` | Differential-displacement map, polarized core (Fig. 1d) |
| `*/relaxed_outputs.csv` | Bulk lattice relaxation |
| `*/dislocation.csv` | Relaxed dislocated cell (box, energy) |
| `*/lmp_*.in`, `*/log.lammps*` | LAMMPS inputs and logs |

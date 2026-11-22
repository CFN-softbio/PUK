# Experiment 6: Fracture toughness of NbMo alloys

**Paper:** Appendix B.2, Table 16, Figure 6(b)
**Run:** Claude Code, 2026-07-12/13, with the `atomagents-simulations` MCP server

## Prompt

The prompt of the original authors' released AutoGen notebook (`AtomAgents_exp_3.ipynb`):

```
Explore the effect of Nb concentration on the critical fracture toughness for the following crack systems in NbMo alloys:
(a) [100] crack propagation, [010] crack plane, and [001] crack front direction.
(b) [1-10] crack propagation, [111] crack plane, and [-1-12] crack front direction.
(c) [111] crack propagation, [11-2] crack plane, and [-110] crack front direction.
(d) [1-1-2] crack propagation, [110] crack plane, and [1-11] crack front direction.
Use NbMo.mtp moment tensor potential (Nb is the first element and Mo is the second element) and consider Nb concentration from 0 to 100 in intervals of 20. Also, for surface energy calculations, consider 50 Angstrom as the box size along free surfaces and 20 along other directions. Finally, plot the results as a function of Nb concentration and discuss them. What is the preferential crack plane in each system?
```

Follow-ups (restricting the reported results to systems (a) and (b), the two shown in the original paper):

```
ok no so assume we only had cases a and b. Edit the plot to only have those lines. And give me the discussion again assuming only case a and b
```
```
can you write the discussion out in a separate file
```

## Outputs

| Path | Contents |
|---|---|
| `KIc_vs_Nb.png`, `plot_KIc.py` | K_Ic vs Nb concentration for systems (a) and (b) (Fig. 6b) |
| `KIc_discussion.md` | The agent's discussion |
| `NbMo_Nb*/relaxed_outputs.csv`, `elastic_constants.csv` | Lattice and elastic constants per composition |
| `NbMo_Nb*/surface_energy_*.csv` | Surface-energy runs (last plane computed in each folder) |
| `NbMo_Nb*/lmp_*.in`, `log.lammps.*` | LAMMPS inputs and logs |

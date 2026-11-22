# Experiment 7: Elastic constants of FCC Au

**Paper:** Appendix B.3, Table 17, Figure 7(b)
**Run:** Claude Code, 2026-07-13, with the seven LAMMPS MCP servers

## Prompt

```
Calculate the elastic constants of gold using an EAM potential. Plot the elastic constants on a heatmap
```

## Outputs

| Path | Contents |
|---|---|
| `elastic_matrix.txt` | 6×6 elastic constant matrix (GPa) |
| `au_elastic_constants_heatmap.png` | Heatmap (Fig. 7b) |
| `in.elastic`, `init.mod`, `potential.mod`, `displace.mod` | LAMMPS input |
| `in.elastic.log` | LAMMPS log |
| `Au_u3.eam` | EAM potential |

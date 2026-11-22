# Experiment 5: Materials characterization (Al, Ni)

**Paper:** Appendix B.1, Table 15
**Run:** Claude Code (`claude-opus-5-5`), 2026-10-17, with the `atomagents-simulations` MCP server. Transcript: `transcript.jsonl`

## Prompt

```
Compute the equilibrium lattice constant, elastic constants (C11, C12, C44), and surface energy of the (100), (110), and (111) planes for pure Al using the `Al99.eam.alloy` potential. Then repeat the same for pure Ni using `Ni99.eam.alloy`. Report all values with units.
```

## Outputs

| Path | Contents |
|---|---|
| `{Al,Ni}_props/relaxed_outputs.csv` | Lattice constant |
| `{Al,Ni}_props/elastic_constants.csv` | C11, C12, C44, bulk/shear modulus, Poisson ratio |
| `{Al,Ni}_props/surface_energies.csv` | Surface energy of each plane |
| `{Al,Ni}_props/lmp_*.in`, `log.lammps.*` | LAMMPS inputs and logs |
| `transcript.jsonl` | Session transcript |

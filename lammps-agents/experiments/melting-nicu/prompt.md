# Melting point of FCC Ni–Cu

**Paper:** Section 2.1.2, Table 4, Figure 2(b)
**Run:** Claude Code, 2026-07-26, with the seven LAMMPS MCP servers

## Prompt

```
Calculate the melting point of FCC nickel-copper (Ni-Cu) alloy using LAMMPS molecular dynamics. Use the solid-liquid coexistence (interface) method: first build and relax the FCC crystal, then create a solid-liquid interface by freezing the top half and melting the bottom half at high temperature in NVT, and finally run a heating simulation that ramps the temperature from room temperature past the expected melting point. Plot potential energy and heat capacity versus temperature, and identify the melting point as the heat-capacity peak.
```

## Outputs

| Path | Contents |
|---|---|
| `cuni_fcc.lmp` | Ni50Cu50 FCC structure (1728 atoms) |
| `in.relax_cuni`, `in.relax_cuni.log` | Relaxation |
| `in.interface_cuni`, `in.interface_cuni.log` | Solid–liquid interface |
| `in.heat_ramp_cuni`, `in.heat_ramp_cuni.log` | Heating ramp 300 → 2100 K |
| `cuni_melting_analysis.png`, `exp_nicu_melt_reproduced.png` | Melting analysis (Fig. 2b); heat-capacity peak at 1813 K |
| `Ni_u3.eam`, `Cu_u3.eam` | EAM potentials |

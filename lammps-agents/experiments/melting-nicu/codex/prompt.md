# Melting point of FCC Ni–Cu (Codex)

**Paper:** Section 2.1.2
**Run:** Codex CLI 0.163.0 (`gpt-5.6-sol`), 2026-10-17, isolated session with the seven LAMMPS MCP servers. Session log: `session.jsonl`

## Prompt

```
Calculate the melting point of FCC nickel-copper (Ni-Cu) alloy using LAMMPS molecular dynamics. Use the solid-liquid coexistence (interface) method: first build and relax the FCC crystal, then create a solid-liquid interface by freezing the top half and melting the bottom half at high temperature in NVT, and finally run a heating simulation that ramps the temperature from room temperature past the expected melting point. Plot potential energy and heat capacity versus temperature, and identify the melting point as the heat-capacity peak.
```

## Outputs

| Path | Contents |
|---|---|
| `nicu50_fcc.lmp` | Ni50Cu50 FCC structure (4096 atoms) |
| `in.nicu_relax`, `in.nicu_relax.log` | Relaxation |
| `in.nicu_interface`, `in.nicu_interface.log` | Solid–liquid interface |
| `in.nicu_heat`, `in.nicu_heat.log` | Heating ramp 300 → 2000 K |
| `nicu_melting_analysis.png` | Melting analysis; heat-capacity peak at 1823 K |
| `Ni_u3.eam`, `Cu_u3.eam` | EAM potentials |
| `session.jsonl` | Session log |

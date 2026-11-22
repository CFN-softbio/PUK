# Experiment 8: Phonon dispersion of FCC Au

**Paper:** Appendix B.4, Figure 8(b)
**Run:** Claude Code (`claude-opus-5-5`), 2026-10-17, with the seven LAMMPS MCP servers. Transcript: `transcript.jsonl`

## Prompt

```
Calculate the phonon dispersion for gold.
```

## Outputs

| Path | Contents |
|---|---|
| `band.pdf`, `band.png` | Phonon dispersion along Γ–X–W–K–Γ–L–U (Fig. 8b) |
| `band.yaml`, `band.conf` | Band data and phonopy settings |
| `POSCAR`, `SPOSCAR`, `POSCAR-001`, `phonopy_disp.yaml`, `phonopy.yaml`, `FORCE_SETS` | phonopy inputs and forces |
| `au_structure.lmp`, `Au_u3.eam`, `disp-001/` | Structure, potential, LAMMPS force calculation |
| `transcript.jsonl` | Session transcript |

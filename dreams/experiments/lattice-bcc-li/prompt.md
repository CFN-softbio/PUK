# Lattice constant of BCC Li

**Paper:** Section 2.1.3, Table 6, Figure 3
**Run:** Claude Code, 2026-07-16, with the `dreams-dft` and `dreams-hpc` MCP servers; Quantum ESPRESSO 7.5

## Prompt

```
You are going to calculate the lattice constant for BCC Li through DFT. The experimental value
  is 3.451; use this to create the initial structure
```

## Outputs

| Path | Contents |
|---|---|
| `Li-bcc.xyz`, `Li_bcc_template.pwi` | Initial structure and QE template |
| `Li_bcc_template_k_*_ecutwfc_*.pwi[.pwo]` | Convergence test inputs and outputs |
| `df_k.csv`, `df_e.csv`, `convergence_test.csv` | Convergence errors (meV/atom) |
| `convergence_figure3.png`, `plot_convergence.py` | Convergence plot (Fig. 3) and the script that made it |
| `Li_bcc_template_{0.95,…,1.05}.pwi[.pwo]` | Equation-of-state inputs and outputs |
| `volume_vs_energy.png` | Equation of state |
| `lattice_constant.json` | Fitted lattice constant (3.4398 Å) |
| `eos_fit.json`, `fit_eos.py` | Lattice constant and bulk modulus from the EOS outputs |

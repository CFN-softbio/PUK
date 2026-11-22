# Lattice constant of BCC Li (Codex)

**Paper:** Section 2.1.3
**Run:** Codex CLI 0.163.0 (`gpt-5.6-sol`), 2026-10-17, isolated session with the `dreams-dft` and `dreams-hpc` MCP servers; Quantum ESPRESSO 7.5. Session log: `session.jsonl`

## Prompt

```
You are going to calculate the lattice constant for BCC Li through DFT. The experimental value
  is 3.451; use this to create the initial structure
```

Follow-up (after the agent created the initial structure and stopped):

```
go ahead and complete the calculation
```

## Outputs

| Path | Contents |
|---|---|
| `Li-bcc.xyz`, `Li_bcc.pwi` | Initial structure and QE template |
| `Li_bcc_k_*_ecutwfc_*.pwi[.pwo]` | Convergence test inputs and outputs |
| `df_k.csv`, `df_e.csv`, `convergence_test.csv`, `jobs_K_and_ecut.json` | Convergence errors (meV/atom) and job parameters |
| `Li_bcc_{0.95,…,1.05}.pwi[.pwo]` | Equation-of-state inputs and outputs |
| `volume_vs_energy.png` | Equation of state |
| `lattice_constant.json` | Fitted lattice constant (3.4414 Å) |
| `session.jsonl` | Session log |

# Critical Fracture Toughness (K_Ic) of NbMo Alloys — Systems (a) and (b)

Potential: `NbMo.mtp` (moment tensor potential, Nb = element 1, Mo = element 2)
Nb concentrations sampled: 0, 20, 40, 60, 80, 100 at.%
Surface-energy box sizes: L_free = 50 Å, L_periodic = 20 Å

Crack systems considered:
- **(a)** crack propagation [100], crack plane (010), crack front [001]
- **(b)** crack propagation [1-10], crack plane (111), crack front [-1-12]

---

## K_Ic values (MPa·m^{1/2})

| Nb (at.%) | (a) [100]/(010)/<001> | (b) [1-10]/(111)/<-1-12> | Preferential plane |
|---|---:|---:|:--|
| 0 (pure Mo) | 1.275 | **1.229** | (b) (111) |
| 20          | 1.270 | **1.212** | (b) (111) |
| 40          | 1.151 | **1.095** | (b) (111) |
| 60          | 0.947 | **0.897** | (b) (111) |
| 80          | 0.656 | **0.607** | (b) (111) |
| 100 (pure Nb)| 0.709 | **0.680** | (b) (111) |

Bold = lower K_Ic at that composition (easier to cleave).

---

## Discussion

### 1. Alloying dramatically softens fracture on both planes
K_Ic drops by nearly half — from ~1.25 MPa·m^{1/2} at pure Mo down to ~0.6 MPa·m^{1/2} near Nb ≈ 80 % — on both the (010) and (111) crack planes. The steepest reduction sits between 40 % and 80 % Nb.

The dominant driver of this fracture-toughness loss is the collapse of the shear elastic constant C_44 with Nb addition:

| Nb (at.%) | C_11 (GPa) | C_12 (GPa) | C_44 (GPa) |
|---|---:|---:|---:|
| 0   | 390.78 | 174.21 | 85.21 |
| 20  | 398.84 | 168.58 | 77.69 |
| 40  | 366.12 | 159.45 | 60.02 |
| 60  | 309.43 | 145.69 | 35.06 |
| 80  | 238.85 | 135.02 | 12.70 |
| 100 | 238.06 | 159.75 | 24.96 |

C_44 falls by more than 6× between 20 % and 80 % Nb — this is the well-known dynamical/elastic softening of the BCC lattice at intermediate Nb–Mo compositions, and it directly reduces the Griffith prefactor in K_Ic = sqrt(2·B·γ_s), where the elastic factor B depends on C_11, C_12, and C_44.

### 2. Slight recovery from 80 → 100 % Nb
Both curves rebound at pure Nb. Between Nb₈₀Mo₂₀ and pure Nb the surface energies decrease modestly, but C_44 recovers from 12.7 → 25.0 GPa. The net effect is that pure Nb is slightly tougher than Nb₈₀Mo₂₀. **Nb₈₀Mo₂₀ is therefore the most brittle composition studied, not pure Nb.**

### 3. Ordering (a) > (b) is preserved at every composition
System (b), whose crack plane is (111), has consistently lower K_Ic than system (a) with a (010) crack plane. The gap is small (~40–50 kPa·m^{1/2} in absolute terms, i.e. roughly 3–7 % of K_Ic) but robust across the whole concentration range.

This means:
- **(a) is always the tougher orientation.** It requires a higher stress intensity to cleave.
- **(b) is always the easier orientation.** A crack allowed to choose between the two geometries would prefer (b).

---

## Preferential cleavage plane in each system

### System (a): [100]/(010)/<001>
The (010) plane has the highest surface energy in this set (γ_s ≈ 2.84 J/m² at pure Mo, ≈ 2.34 J/m² at pure Nb). Combined with the anisotropic elastic prefactor along [100] loading, this yields the higher K_Ic at every composition. This is the harder-to-cleave orientation; a real crack would only propagate here if the geometry constrains it.

### System (b): [1-10]/(111)/<-1-12>
The (111) plane has a lower surface energy across all compositions (γ_s ≈ 2.72 J/m² at pure Mo down to ≈ 2.26 J/m² at pure Nb) and — together with the elastic anisotropy — produces the lower K_Ic. **(111) is therefore the preferential (lowest-energy) cleavage plane between the two options at every Nb concentration.**

---

## Take-away

Restricted to systems (a) and (b), **(b) with a (111) crack plane is the preferential cleavage system across the full 0–100 % Nb range.** Increasing Nb content sharply weakens both, with a minimum around Nb ≈ 80 % driven mainly by C_44 softening in the mid-composition regime.

Plot: `KIc_vs_Nb.png`

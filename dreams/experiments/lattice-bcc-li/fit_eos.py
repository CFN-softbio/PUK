"""
Re-fit the BCC Li equation of state from the five EOS Quantum ESPRESSO outputs.

The port's calculate_lattice_constant tool (like upstream DREAMS) uses ASE's
default EOS form (stabilized jellium, 'sj') and returns only a0. This script
reports a0 and the bulk modulus for both 'sj' and Birch-Murnaghan fits.

Usage:
    python fit_eos.py [run_dir] [output.json]

Defaults: run_dir = directory of this script, output = <run_dir>/eos_fit.json
"""

import glob
import json
import os
import sys

from ase.io import read
from ase.eos import EquationOfState
from ase.units import kJ


def fit(run_dir: str) -> dict:
    files = sorted(glob.glob(os.path.join(run_dir, "Li_bcc_template_[01].*.pwi.pwo")))
    atoms = [read(f, format="espresso-out") for f in files]
    volumes = [a.get_volume() for a in atoms]
    energies = [a.get_potential_energy() for a in atoms]
    natoms = len(atoms[0])

    results = {"files": [os.path.basename(f) for f in files], "natoms_per_cell": natoms}
    for form in ("sj", "birchmurnaghan"):
        v0, e0, B = EquationOfState(volumes, energies, eos=form).fit()
        results[form] = {
            "a0_angstrom": v0 ** (1 / 3),  # 2-atom conventional cubic cell
            "B0_GPa": B / kJ * 1.0e24,
            "E0_eV": e0,
        }
    return results


if __name__ == "__main__":
    run_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(run_dir, "eos_fit.json")
    res = fit(run_dir)
    with open(out, "w") as f:
        json.dump(res, f, indent=2)
    for form in ("sj", "birchmurnaghan"):
        print(f"{form:15s} a0 = {res[form]['a0_angstrom']:.5f} A   B0 = {res[form]['B0_GPa']:.2f} GPa")

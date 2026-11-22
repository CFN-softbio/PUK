"""Elastic constant simulation tool."""

import json
import os
import shutil

import numpy as np

from .setup import create_crystal
from ..helpers.lammps_runner import run_lammps_input
from ..helpers.parsers import parse_elastic_constants
from ..config import get_templates_dir


def elastic_constant_simulation(working_folder: str, lat_type: str, a: float,
                                conc_1: int, conc_2: int, mtp_pot: bool,
                                thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Compute elastic constants of the material.

    The potential file must already exist in the working folder.

    Args:
        working_folder: Working directory for simulation results.
        lat_type: "fcc" or "bcc".
        a: Equilibrium lattice constant.
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in % (0 for unary non-MTP).
        mtp_pot: True for MTP potential.
        thermo_time: Thermodynamic output interval.
        dump_time: Dump output interval.

    Returns:
        JSON string with elastic constants C11, C12, C13, ..., C66 in GPa.
    """
    os.makedirs(working_folder, exist_ok=True)

    assert conc_1 + conc_2 == 100, 'the concentrations should sum up to 100.'

    if conc_1 == 0 or conc_2 == 0:
        total_samples = 1
    else:
        total_samples = 3

    C_11_all = []
    C_22_all = []
    C_33_all = []
    C_12_all = []
    C_13_all = []
    C_23_all = []
    C_44_all = []
    C_55_all = []
    C_66_all = []

    for num_samples in range(total_samples):
        input_data_file_name = create_crystal(
            working_folder, 'elastic_constant.lmp',
            lat_type, a, conc_1, conc_2, mtp_pot,
            [1, 0, 0], [0, 1, 0], [0, 0, 1], 5, 5, 5)

        bash_script = f'''
variable data_file string "{input_data_file_name}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}

shell cp ./0_codes/displace.mod ./{working_folder}/displace.mod

shell cd ./{working_folder}

variable displace_file string "displace.mod"

variable up equal 1.0e-6
variable atomjiggle equal 1.0e-5

units		metal
variable cfac equal 1.0e-4
variable cunits string GPa

variable etol equal 0.0
variable ftol equal 1.0e-5
variable maxiter equal 5000
variable maxeval equal 5000
variable dmax equal 1.0e-2

neighbor 1.0 nsq
neigh_modify once no every 1 delay 0 check yes

boundary	p p p

read_data ${{data_file}}
include ${{potential_file}}

change_box all triclinic

thermo		50
thermo_style custom step temp pe press pxx pyy pzz pxy pxz pyz lx ly lz vol
thermo_modify norm no

min_style	     cg
min_modify	     dmax ${{dmax}} line quadratic
fix 3 all box/relax  aniso 0.0
minimize ${{etol}} ${{ftol}} ${{maxiter}} ${{maxeval}}

variable tmp equal pxx
variable pxx0 equal ${{tmp}}
variable tmp equal pyy
variable pyy0 equal ${{tmp}}
variable tmp equal pzz
variable pzz0 equal ${{tmp}}
variable tmp equal pyz
variable pyz0 equal ${{tmp}}
variable tmp equal pxz
variable pxz0 equal ${{tmp}}
variable tmp equal pxy
variable pxy0 equal ${{tmp}}

variable tmp equal lx
variable lx0 equal ${{tmp}}
variable tmp equal ly
variable ly0 equal ${{tmp}}
variable tmp equal lz
variable lz0 equal ${{tmp}}

variable d1 equal -(v_pxx1-${{pxx0}})/(v_delta/v_len0)*${{cfac}}
variable d2 equal -(v_pyy1-${{pyy0}})/(v_delta/v_len0)*${{cfac}}
variable d3 equal -(v_pzz1-${{pzz0}})/(v_delta/v_len0)*${{cfac}}
variable d4 equal -(v_pyz1-${{pyz0}})/(v_delta/v_len0)*${{cfac}}
variable d5 equal -(v_pxz1-${{pxz0}})/(v_delta/v_len0)*${{cfac}}
variable d6 equal -(v_pxy1-${{pxy0}})/(v_delta/v_len0)*${{cfac}}

displace_atoms all random ${{atomjiggle}} ${{atomjiggle}} ${{atomjiggle}} 87287 units box

unfix 3
write_restart restart.equil

variable dir equal 1
include ${{displace_file}}

variable dir equal 2
include ${{displace_file}}

variable dir equal 3
include ${{displace_file}}

variable dir equal 4
include ${{displace_file}}

variable dir equal 5
include ${{displace_file}}

variable dir equal 6
include ${{displace_file}}

variable C11all equal ${{C11}}
variable C22all equal ${{C22}}
variable C33all equal ${{C33}}

variable C12all equal 0.5*(${{C12}}+${{C21}})
variable C13all equal 0.5*(${{C13}}+${{C31}})
variable C23all equal 0.5*(${{C23}}+${{C32}})

variable C44all equal ${{C44}}
variable C55all equal ${{C55}}
variable C66all equal ${{C66}}

variable C14all equal 0.5*(${{C14}}+${{C41}})
variable C15all equal 0.5*(${{C15}}+${{C51}})
variable C16all equal 0.5*(${{C16}}+${{C61}})

variable C24all equal 0.5*(${{C24}}+${{C42}})
variable C25all equal 0.5*(${{C25}}+${{C52}})
variable C26all equal 0.5*(${{C26}}+${{C62}})

variable C34all equal 0.5*(${{C34}}+${{C43}})
variable C35all equal 0.5*(${{C35}}+${{C53}})
variable C36all equal 0.5*(${{C36}}+${{C63}})

variable C45all equal 0.5*(${{C45}}+${{C54}})
variable C46all equal 0.5*(${{C46}}+${{C64}})
variable C56all equal 0.5*(${{C56}}+${{C65}})

variable C11cubic equal (${{C11all}}+${{C22all}}+${{C33all}})/3.0
variable C12cubic equal (${{C12all}}+${{C13all}}+${{C23all}})/3.0
variable C44cubic equal (${{C44all}}+${{C55all}}+${{C66all}})/3.0

variable bulkmodulus equal (${{C11cubic}}+2*${{C12cubic}})/3.0
variable shearmodulus1 equal ${{C44cubic}}
variable shearmodulus2 equal (${{C11cubic}}-${{C12cubic}})/2.0
variable poissonratio equal 1.0/(1.0+${{C11cubic}}/${{C12cubic}})

print "========================================="
print "Components of the Elastic Constant Tensor"
print "========================================="

print "Elastic Constant C11all = ${{C11all}} ${{cunits}}"
print "Elastic Constant C22all = ${{C22all}} ${{cunits}}"
print "Elastic Constant C33all = ${{C33all}} ${{cunits}}"

print "Elastic Constant C12all = ${{C12all}} ${{cunits}}"
print "Elastic Constant C13all = ${{C13all}} ${{cunits}}"
print "Elastic Constant C23all = ${{C23all}} ${{cunits}}"

print "Elastic Constant C44all = ${{C44all}} ${{cunits}}"
print "Elastic Constant C55all = ${{C55all}} ${{cunits}}"
print "Elastic Constant C66all = ${{C66all}} ${{cunits}}"

print "Elastic Constant C14all = ${{C14all}} ${{cunits}}"
print "Elastic Constant C15all = ${{C15all}} ${{cunits}}"
print "Elastic Constant C16all = ${{C16all}} ${{cunits}}"

print "Elastic Constant C24all = ${{C24all}} ${{cunits}}"
print "Elastic Constant C25all = ${{C25all}} ${{cunits}}"
print "Elastic Constant C26all = ${{C26all}} ${{cunits}}"

print "Elastic Constant C34all = ${{C34all}} ${{cunits}}"
print "Elastic Constant C35all = ${{C35all}} ${{cunits}}"
print "Elastic Constant C36all = ${{C36all}} ${{cunits}}"

print "Elastic Constant C45all = ${{C45all}} ${{cunits}}"
print "Elastic Constant C46all = ${{C46all}} ${{cunits}}"
print "Elastic Constant C56all = ${{C56all}} ${{cunits}}"

print "========================================="
print "Average properties for a cubic crystal"
print "========================================="

print "Bulk Modulus = ${{bulkmodulus}} ${{cunits}}"
print "Shear Modulus 1 = ${{shearmodulus1}} ${{cunits}}"
print "Shear Modulus 2 = ${{shearmodulus2}} ${{cunits}}"
print "Poisson Ratio = ${{poissonratio}}"

thermo_style custom v_C11all v_C12all v_C13all v_C14all v_C15all v_C16all v_C22all v_C23all v_C24all v_C25all v_C26all v_C33all v_C34all v_C35all v_C36all v_C44all v_C45all v_C46all v_C55all v_C56all v_C66all v_bulkmodulus v_shearmodulus1 v_poissonratio

fix extra all print 1 "${{C11all}} ${{C12all}} ${{C13all}} ${{C14all}} ${{C15all}} ${{C16all}} ${{C22all}} ${{C23all}} ${{C24all}} ${{C25all}} ${{C26all}} ${{C33all}} ${{C34all}} ${{C35all}} ${{C36all}} ${{C44all}} ${{C45all}} ${{C46all}} ${{C55all}} ${{C56all}} ${{C66all}} ${{bulkmodulus}} ${{shearmodulus1}} ${{poissonratio}}" file "elastic_constants.csv" title "#C11 C12 C44 bulkmodulus shearmodulus poissonratio" screen no

run 0
        '''

        lammps_script = f'{working_folder}/lmp_elastic_constant_script.in'
        with open(lammps_script, 'w') as f:
            f.write(bash_script)

        result = run_lammps_input(
            lammps_script,
            log_path=f'./{working_folder}/log.lammps.elastic_constants',
            num_cpus=1)

        parsed = parse_elastic_constants(f'./{working_folder}/elastic_constants.csv')

        C_11_all.append(parsed['C11'])
        C_22_all.append(parsed['C22'])
        C_33_all.append(parsed['C33'])
        C_12_all.append(parsed['C12'])
        C_13_all.append(parsed['C13'])
        C_23_all.append(parsed['C23'])
        C_44_all.append(parsed['C44'])
        C_55_all.append(parsed['C55'])
        C_66_all.append(parsed['C66'])

    output_dict = {
        "C11 (GPa)": f'{np.mean(C_11_all):.2f}',
        "C12 (GPa)": f'{np.mean(C_12_all):.2f}',
        "C13 (GPa)": f'{np.mean(C_13_all):.2f}',
        "C22 (GPa)": f'{np.mean(C_22_all):.2f}',
        "C23 (GPa)": f'{np.mean(C_23_all):.2f}',
        "C33 (GPa)": f'{np.mean(C_33_all):.2f}',
        "C44 (GPa)": f'{np.mean(C_44_all):.2f}',
        "C55 (GPa)": f'{np.mean(C_55_all):.2f}',
        "C66 (GPa)": f'{np.mean(C_66_all):.2f}',
    }

    return json.dumps(output_dict)

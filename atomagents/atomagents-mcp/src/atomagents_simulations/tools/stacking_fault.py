"""Stacking fault energy simulation tool."""

import json
import os

import numpy as np

from .setup import create_crystal
from ..helpers.single_step import single_step_simulation
from ..helpers.lammps_runner import run_lammps_input


def stacking_fault_simulation(working_folder: str, lat_type: str, a: float,
                              conc_1: int, conc_2: int, mtp_pot: bool,
                              orient_x: list, orient_y: list, orient_z: list,
                              shift_num: int = 21,
                              thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Compute the generalized stacking fault energy curve.

    Args:
        working_folder: Working directory for results.
        lat_type: "fcc" or "bcc".
        a: Lattice constant from lattice_constant_simulation.
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in % (0 for unary non-MTP).
        mtp_pot: True for MTP potential.
        orient_x: Crystal orientation along x (shearing direction).
        orient_y: Crystal orientation along y.
        orient_z: Crystal orientation along z (stacking fault plane direction).
        shift_num: Number of points along the SFE curve (default 21).
        thermo_time: Thermodynamic output interval.
        dump_time: Dump output interval.

    Returns:
        JSON with relative shifts, potential energy per area in meV/A^2 and mJ/m^2.
    """
    os.makedirs(working_folder, exist_ok=True)

    size_x = 5
    size_y = 5
    size_z = 12

    input_data_file_name = create_crystal(
        working_folder, 'surface_energy.lmp',
        lat_type, a, conc_1, conc_2, mtp_pot,
        orient_x, orient_y, orient_z, size_x, size_y, size_z)

    res = json.loads(single_step_simulation(working_folder, input_data_file_name, size_x, size_y, size_z))
    Lz = res['Lz (A)']
    xlat = res['xlat (A)']

    pot_all = []
    pot_all_mj = []
    tau_all = []
    for tau_x in np.linspace(0, 1, shift_num):

        bash_script = f'''
clear
units metal
dimension 3
boundary p p p

shell cd ./{working_folder}

variable data_file string "{input_data_file_name}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}
variable dump_name string "dump.stacking_fault.x_{tau_x}"

read_data ${{data_file}}
include ${{potential_file}}

change_box all boundary p p s

variable zmid equal {Lz}/2-0.1

region top block INF INF INF INF ${{zmid}} INF units box
group top region top

variable tau_xx equal {tau_x}*{xlat}

displace_atoms top move ${{tau_xx}} 0  0 units box

compute peratom all pe/atom
compute pe all pe

thermo_style custom step temp pe vol press pxx pyy pzz fnorm
thermo_modify format float %5.5g
thermo ${{thermo_time}}

shell mkdir stacking_fault_energy

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./stacking_fault_energy/dump.out"
dump ${{dump_id}} all custom ${{dump_time}} ${{dump_out_name}}.* id type x y z c_peratom

variable p1 equal "step"
variable p2 equal "lx"
variable p3 equal "ly"
variable p4 equal "lz"
variable p5 equal "pe"
variable p6 equal "vol"

fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}}" file "stacking_fault.csv" title "#step a_x a_y a_z pe vol" screen no

fix xz_fixed all setforce 0.0 NULL 0.0

run 0

min_style fire
minimize 0 1e-5 20000 20000

undump ${{dump_id}}

dump dump_ all custom ${{dump_time}} ${{dump_out_name}}.* id type x y z c_peratom


reset_timestep 0
dump last_dump all custom 1 ${{dump_name}} id type x y z c_peratom
run 0

undump last_dump

unfix extra

    '''

        lammps_script = f'{working_folder}/lmp_stacking_fault.in'
        with open(lammps_script, 'w') as f:
            f.write(bash_script)

        result = run_lammps_input(
            lammps_script,
            log_path=f'./{working_folder}/log.lammps.stacking_fault',
            num_cpus=4)

        if result.returncode == 0:
            with open(f'./{working_folder}/stacking_fault.csv') as file:
                lines = file.readlines()

            init_data = lines[1].split(' ')
            final_data = lines[-1].split(' ')

            pot_energy_final = float(final_data[4])

            Lx = float(init_data[1])
            Ly = float(init_data[2])

            potential_energy_per_area = pot_energy_final * 1000 / (Lx * Ly)
            potential_energy_per_area_mj = potential_energy_per_area * 16.0218

            pot_all.append(potential_energy_per_area)
            pot_all_mj.append(potential_energy_per_area_mj)
            tau_all.append(tau_x)

        else:
            stderr = result.stderr.strip().split('\n')[-2:]
            return json.dumps(stderr, indent=4)

    tau_all = np.array(tau_all)
    pot_all = np.array(pot_all) - pot_all[0]
    pot_all_mj = np.array(pot_all_mj) - pot_all_mj[0]

    tau_all = [f"{num:.2f}" for num in tau_all]
    pot_all = [f"{num:.3f}" for num in pot_all]
    pot_all_mj = [f"{num:.3f}" for num in pot_all_mj]

    output_dict = {
        'relative shift': tau_all,
        'potential energy per area (meV/A^2)': pot_all,
        'potential energy per area (mJ/m^2)': pot_all_mj,
    }

    return json.dumps(output_dict)

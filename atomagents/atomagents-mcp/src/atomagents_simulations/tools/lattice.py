"""Lattice constant simulation tool."""

import json
import os

import numpy as np

from .setup import create_crystal
from ..helpers.lammps_runner import run_lammps_input


def lattice_constant_simulation(working_folder: str, lat_type: str,
                                lat_const_guess: float, conc_1: int, conc_2: int,
                                mtp_pot: bool, num_cpus: int = 4,
                                thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Compute the equilibrium lattice constant via energy minimization and pressure relaxation.

    The potential file must already exist in the working folder (created by create_potential_file).

    Args:
        working_folder: Working directory for simulation results.
        lat_type: "fcc" or "bcc".
        lat_const_guess: Approximate lattice constant guess (Angstrom).
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in % (0 for unary non-MTP).
        mtp_pot: True for MTP potential.
        num_cpus: Number of CPUs for MPI (default 4).
        thermo_time: Thermodynamic output interval (default 100).
        dump_time: Dump output interval (default 1000).

    Returns:
        JSON string with the computed lattice constant.
    """
    os.makedirs(working_folder, exist_ok=True)

    assert conc_1 + conc_2 == 100, 'the concentrations should sum up to 100.'

    if conc_1 != 0 and conc_1 != 100:
        total_samples = 3
    else:
        total_samples = 1

    nx = 10
    ny = 10
    nz = 10

    lat_all = []
    for num_samples in range(total_samples):

        if num_samples == 0:
            input_data_file_name = create_crystal(
                working_folder, 'lattice_constant_alloy.lmp',
                lat_type, lat_const_guess, conc_1, conc_2, mtp_pot,
                [1, 0, 0], [0, 1, 0], [0, 0, 1], nx, ny, nz)
        else:
            input_data_file_name = create_crystal(
                working_folder, 'lattice_constant_alloy.lmp',
                lat_type, np.mean(lat_all), conc_1, conc_2, mtp_pot,
                [1, 0, 0], [0, 1, 0], [0, 0, 1], nx, ny, nz)

        bash_script = f'''
clear
units metal
dimension 3
boundary p p p
atom_style atomic

shell cd ./{working_folder}

variable data_file string "{input_data_file_name}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}


read_data ${{data_file}}

include ${{potential_file}}

compute peratom all pe/atom
compute pe all pe

thermo_style custom step temp pe vol lx ly lz press pxx pyy pzz fnorm
thermo_modify format float %5.5g
thermo ${{thermo_time}}

shell mkdir dump_lattice_constant

reset_timestep 0
dump first_dump all custom 1 dump.lattice.initial.{num_samples} id type x y z c_peratom
run 0
undump first_dump

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./dump_lattice_constant/dump.out"
dump ${{dump_id}} all custom ${{dump_time}} ${{dump_out_name}}.* id type x y z c_peratom

variable p1 equal "step"
variable p2 equal "count(all)"
variable p3 equal "lx"
variable p4 equal "ly"
variable p5 equal "lz"
variable p6 equal "pe"
variable p7 equal "vol"

fix 1 all box/relax aniso 0
min_style cg
minimize 0 1e-5 2000 20000
unfix 1

min_style cg
minimize 0 1e-5 20000 20000

fix 1 all box/relax aniso 0
min_style cg
minimize 0 1e-5 2000 20000
unfix 1

min_style cg
minimize 0 1e-5 20000 20000

fix 1 all box/relax aniso 0
min_style cg
minimize 0 1e-5 2000 20000
unfix 1

min_style cg
minimize 0 1e-5 20000 20000


fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}} ${{p7}}" file "relaxed_outputs.csv" title "#step numb_atoms a_x a_y a_z pe vol" screen no

reset_timestep 0
dump last_dump all custom 1 dump.lattice.final.{num_samples} id type x y z c_peratom
run 0

unfix extra
undump last_dump
quit
        '''

        lammps_script = f'{working_folder}/lmp_lattice_constant_script.in'
        with open(lammps_script, 'w') as f:
            f.write(bash_script)

        result = run_lammps_input(
            lammps_script,
            log_path=f'./{working_folder}/log.lammps.lattice.constant.alloy',
            num_cpus=num_cpus)

        if result.returncode == 0:
            with open(f'./{working_folder}/relaxed_outputs.csv') as file:
                lines = file.readlines()

            last_data = lines[-1].split(' ')

            Lx = float(last_data[2])
            Ly = float(last_data[3])
            Lz = float(last_data[4])
            xlat = float(Lx / nx)
            ylat = float(Ly / ny)
            zlat = float(Lz / nz)

            lat_all.append(xlat)
            lat_all.append(ylat)
            lat_all.append(zlat)

            output_dict = {'lattice constant': f'{np.mean(lat_all):.3f}'}
            return json.dumps(output_dict)
        else:
            stderr = result.stderr.strip().split('\n')
            stdout = result.stdout.strip().split('\n')[-2:]
            return json.dumps([stderr, stdout], indent=4)

    # Should not reach here for single-sample case
    output_dict = {'lattice constant': f'{np.mean(lat_all):.3f}'}
    return json.dumps(output_dict)

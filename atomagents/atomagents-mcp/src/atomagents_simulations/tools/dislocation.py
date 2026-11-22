"""Screw dislocation creation and NEB Peierls barrier tools."""

import json
import os
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .setup import create_crystal
from ..helpers.screw_helpers import (
    create_screw_dislocation_initial,
    create_screw_dislocation_final,
    relax_screw_dislocation,
    generate_neb_dump_final,
)
from ..helpers.lammps_runner import run_lammps_input


def create_screw_dislocation(working_folder: str, lat_type: str, lat_const: float,
                             conc_1: int, conc_2: int, mtp_pot: bool,
                             orient_x: list, orient_y: list, orient_z: list,
                             size_x: int = 5, size_y: int = 7, size_z: int = 2,
                             thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Create and relax a screw dislocation, producing a differential displacement map.

    Does NOT require a crystal structure from create_crystal (creates its own).

    Args:
        working_folder: Working directory.
        lat_type: "fcc" or "bcc".
        lat_const: Lattice constant from lattice_constant_simulation.
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in %.
        mtp_pot: True for MTP potential.
        orient_x: Dislocation glide direction, e.g. [1, 1, -2].
        orient_y: Normal to dislocation plane, e.g. [1, 1, 0].
        orient_z: Dislocation line direction, e.g. [1, 1, 1].
        size_x: Crystal size along x in lattice units (default 5).
        size_y: Crystal size along y in lattice units (default 7).
        size_z: Crystal size along z in lattice units (default 2).
        thermo_time: Thermodynamic output interval.
        dump_time: Dump output interval.

    Returns:
        JSON with the dislocation data file name and DD map path.
    """
    b = np.sqrt(3) / 2 * lat_const

    input_data_file_name_without_dislocation = create_crystal(
        working_folder=working_folder,
        output_name='latice_pristine.lmp',
        lat_type=lat_type, lat_const=lat_const,
        conc_1=conc_1, conc_2=conc_2, mtp_pot=mtp_pot,
        orient_x=orient_x, orient_y=orient_y, orient_z=orient_z,
        size_x=size_x, size_y=size_y, size_z=size_z)

    initial_screw_dislocation_name = create_screw_dislocation_initial(
        working_folder, input_data_file_name_without_dislocation,
        'dislocated.initial.lmp', b, size_x, size_y)

    output_relax_initial = relax_screw_dislocation(
        working_folder, input_data_file_name_without_dislocation,
        initial_screw_dislocation_name, lat_const, b)

    DD_map_path = json.loads(output_relax_initial)["dislocation_displacement_plot_path"]

    output_dict = {
        "screw dislocation data file name": output_relax_initial,
        "path to DD map": DD_map_path,
    }

    return json.dumps(output_dict, indent=2)


def neb_screw_simulation(working_folder: str, lat_type: str, lat_const: float,
                         orient_x: list, orient_y: list, orient_z: list,
                         size_x: int, size_y: int, size_z: int,
                         conc_1: int, conc_2: int, mtp_pot: bool,
                         system_name: str, seed_num: int,
                         num_replicas: int = 10, num_cpus: int = 20,
                         num_samples: int = 5,
                         thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Run NEB simulations to compute the Peierls barrier of a screw dislocation.

    For alloys, several random samples are created. The function returns
    the mean and standard deviation of the barrier distribution.

    Args:
        working_folder: Working directory.
        lat_type: "fcc" or "bcc".
        lat_const: Lattice constant from lattice_constant_simulation.
        orient_x: Dislocation glide direction, e.g. [1, 1, -2].
        orient_y: Normal to dislocation plane, e.g. [1, 1, 0].
        orient_z: Dislocation line direction, e.g. [1, 1, 1].
        size_x: Crystal size along x in lattice units.
        size_y: Crystal size along y in lattice units.
        size_z: Crystal size along z in lattice units.
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in %.
        mtp_pot: True for MTP potential.
        system_name: Name label, e.g. "Nb" or "Nb10W90".
        seed_num: Random seed for structure generation.
        num_replicas: Number of NEB replicas (default 10).
        num_cpus: Number of CPUs for MPI (default 20).
        num_samples: Number of random alloy samples (default 5, 1 for unary).
        thermo_time: Thermodynamic output interval.
        dump_time: Dump output interval.

    Returns:
        JSON with barrier mean/std (meV) and energy change std (meV).
    """
    barrier_all = []
    MEP_all = []
    int_parameter_all = []

    b = np.sqrt(3) / 2 * lat_const

    assert num_cpus >= num_replicas, \
        "number of cpus should be greater than the number of replicas"
    assert num_cpus % num_replicas == 0, \
        "number of cpus should exactly be divisible by the number of replicas"

    if conc_1 == 0 or conc_1 == 100:
        num_samples = 1

    for num_sample in range(num_samples):

        np.random.seed(seed_num * (num_sample + 1))
        input_data_file_name_without_dislocation = create_crystal(
            working_folder=working_folder,
            output_name=f'latice_pristine.{num_sample}.lmp',
            lat_type=lat_type, lat_const=lat_const,
            conc_1=conc_1, conc_2=conc_2, mtp_pot=mtp_pot,
            orient_x=orient_x, orient_y=orient_y, orient_z=orient_z,
            size_x=size_x, size_y=size_y, size_z=size_z)

        initial_screw_dislocation_name = create_screw_dislocation_initial(
            working_folder, input_data_file_name_without_dislocation,
            f'dislocated.initial.{num_sample}', b, size_x, size_y)

        output_relax_initial = relax_screw_dislocation(
            working_folder, input_data_file_name_without_dislocation,
            initial_screw_dislocation_name, lat_const, b)

        pot_disl_initial = float(json.loads(output_relax_initial)["potential energy(meV)"])

        xchange = 4.1
        while True:
            while True:
                final_screw_dislocation_name = create_screw_dislocation_final(
                    working_folder, input_data_file_name_without_dislocation,
                    f'dislocated.final.{num_sample}', b, size_x, size_y,
                    xshift=xchange)

                output_relax_final = relax_screw_dislocation(
                    working_folder, input_data_file_name_without_dislocation,
                    final_screw_dislocation_name, lat_const, b)

                pot_disl_final = float(json.loads(output_relax_final)["potential energy(meV)"])

                if conc_1 != 0 and conc_1 != 100 and np.abs(pot_disl_final - pot_disl_initial) < 0.01:
                    xchange = xchange + 0.5
                else:
                    break

            initial_data_file = f'data.relaxed.{initial_screw_dislocation_name}'
            assert os.path.exists(f'{working_folder}/{initial_data_file}'), \
                'relaxed structure of initial dislocation does not exist.'
            final_dump_file = f'./{working_folder}/dump.relaxed.{final_screw_dislocation_name}'
            assert os.path.exists(final_dump_file), \
                'relaxed structure of final dislocation does not exist.'

            dump_neb_final = generate_neb_dump_final(
                working_folder, f'dump.relaxed.{final_screw_dislocation_name}')

            with open(f'{working_folder}/{initial_data_file}') as file:
                lines = file.readlines()
            lines = lines[5:8]
            Xmin = float(lines[0].strip().split()[0])
            Xmax = float(lines[0].strip().split()[1])
            Ymin = float(lines[1].strip().split()[0])
            Ymax = float(lines[1].strip().split()[1])
            Xmid = (Xmax + Xmin) / 2
            Ymid = (Ymax + Ymin) / 2

            bash_script = f'''variable energy_file string "neb_{system_name}_{num_sample}.csv"
print "#potential energy (eV)" file ${{energy_file}}
clear
units metal
dimension 3
boundary p s p
atom_style atomic
atom_modify map array sort 0 0.0

shell cd ./{working_folder}

variable u uloop {num_replicas} pad

variable data_file string "{initial_data_file}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}

read_data ${{data_file}}
include ${{potential_file}}


compute peratom all pe/atom
compute pe all pe

thermo_style custom step temp pe vol press pxx pyy pzz fnorm
thermo_modify format float %5.5g
thermo ${{thermo_time}}

shell mkdir NEB_simulation

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./NEB_simulation/dump.out"
dump ${{dump_id}} all custom ${{dump_time}} ${{dump_out_name}}.* id type x y z c_peratom

variable p1 equal "step"
variable p2 equal "lx"
variable p3 equal "ly"
variable p4 equal "lz"
variable p5 equal "pe"
variable p6 equal "vol"

fix extra all print 100 "$u ${{p5}}" append ${{energy_file}} title "#replica pe" screen no

timestep 0.001
min_style fire
thermo 10
thermo_style custom step temp pe ke press pxx pyy pzz pxy pxz pyz fnorm

fix 3 all neb 0.001
neb 0.0 0.001 1000 1000 100 final {dump_neb_final}

shell mkdir images

reset_timestep 0
dump 3 all custom 1 images/dump.initial.$u id type x y z c_peratom
dump_modify 3 format line "%d %d %.8e %.8e %.8e %.8e"
run 0
undump 3

print "finish"

unfix extra
        '''

            lammps_script = f'{working_folder}/lmp_neb_script.in'
            with open(lammps_script, 'w') as f:
                f.write(bash_script)

            num_extra = int(num_cpus / num_replicas)

            result = run_lammps_input(
                lammps_script,
                log_path=f'./{working_folder}/log.neb.lammps',
                num_cpus=num_cpus,
                extra_args=f'-partition {num_replicas}x{num_extra}')

            if result.returncode == 1:
                with open('log.neb.lammps.0') as file:
                    log_lines = file.readlines()
                # Try again with adjusted xchange
                xchange = xchange + 0.5
                continue
            else:
                with open(f'./{working_folder}/neb_{system_name}_{num_sample}.csv') as file:
                    neb_lines = file.readlines()

                energy_data = []
                for line in neb_lines[-num_replicas * 2 + 1::2]:
                    parts = line.split()
                    if len(parts) >= 2:
                        energy_data.append((int(parts[0]), float(f'{float(parts[1]) * 1000:.2f}')))

                energies = pd.DataFrame(energy_data, columns=['Index', 'Energy'])
                energies.set_index('Index', inplace=True)
                energies = energies.sort_index()
                energies['Energy'] = energies['Energy'] - energies['Energy'].iloc[0]
                barrier = max(energies['Energy'])
                DeltaE = energies['Energy'].iloc[-1]

                if barrier > 1:
                    barrier_all.append(barrier / size_z)
                    MEP_all.append(energies['Energy'] / size_z)
                    int_parameter_all.append(DeltaE)
                    break
                else:
                    xchange = xchange + 0.5

    # Save MEP plot
    for i in range(len(MEP_all)):
        plt.plot(MEP_all[i], '-', label=f'MEP {i+1}')
    plt.xlabel('replica')
    plt.ylabel('energy per b (meV/A)')
    plt.legend()
    plt.savefig(f'./{working_folder}/MEP_plot.png')
    plt.close()

    solute_screw_int_param = np.std(int_parameter_all)

    output_dict = {
        "barrier mean (meV)": f'{np.mean(barrier_all):.2f}',
        "barrier standard deviation (meV)": f'{np.std(barrier_all):.2f}',
        "energy change standard deviation (meV)": f'{solute_screw_int_param:.2f}',
        "MEP plot": f'./{working_folder}/MEP_plot.png',
    }

    return json.dumps(output_dict, indent=2)

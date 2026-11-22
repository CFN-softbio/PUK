"""Single-step LAMMPS simulation for basic property extraction."""

import json
import os

from .lammps_runner import run_lammps_input, check_lammps_result


def single_step_simulation(working_folder, input_data_file_name,
                           size_x, size_y, size_z,
                           thermo_time=100, dump_time=1000):
    """Run a zero-timestep LAMMPS simulation to extract cell dimensions.

    Returns JSON string with cell dimensions, volume, potential energy, and lattice parameters.
    """
    os.makedirs(working_folder, exist_ok=True)

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

thermo_style custom step temp pe vol press pxx pyy pzz fnorm
thermo_modify format float %5.5g
thermo ${{thermo_time}}

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "dump.out"

variable p1 equal "step"
variable p2 equal "count(all)"
variable p3 equal "lx"
variable p4 equal "ly"
variable p5 equal "lz"
variable p6 equal "pe"
variable p7 equal "vol"


fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}} ${{p7}}" file "outputs.csv" title "#step numb_atoms a_x a_y a_z pe vol" screen no

reset_timestep 0
run 0

unfix extra
    '''

    lammps_script = f'{working_folder}/lmp_single_step_script.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        lammps_script,
        log_path=f'./{working_folder}/log.lammps.single.step',
        num_cpus=1)

    if result.returncode == 0:
        with open(f'./{working_folder}/outputs.csv') as file:
            lines = file.readlines()

        last_data = lines[-1].split(' ')

        num_atoms = int(last_data[1])
        Lx = float(last_data[2])
        Ly = float(last_data[3])
        Lz = float(last_data[4])
        pot_energy = float(last_data[5])
        vol = float(last_data[6])
        xlat = float(Lx / size_x)
        ylat = float(Ly / size_y)
        zlat = float(Lz / size_z)

        output_dict = {
            "number of atoms": f'{num_atoms}',
            "Lx (A)": f'{Lx}',
            "Ly (A)": f'{Ly}',
            "Lz (A)": f'{Lz}',
            "volume (A^3)": f'{vol}',
            "pot_energy (eV)": f'{pot_energy}',
            "xlat (A)": f'{xlat}',
            "ylat (A)": f'{ylat}',
            "zlat (A)": f'{zlat}',
        }

        return json.dumps(output_dict)
    else:
        stderr_lines = result.stderr.strip().split('\n')
        return json.dumps(stderr_lines, indent=4)

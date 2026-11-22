"""Screw dislocation creation and relaxation helpers."""

import json
import os
import re

import numpy as np

from .crystal_ops import find_central_atoms, process_atoms
from .dd_map import create_DD_map
from .lammps_runner import run_lammps_input, check_lammps_result


def create_screw_dislocation_initial(working_folder, input_data_file_name_without_dislocation,
                                     output_name_with_dislocation, b, size_x, size_y,
                                     thermo_time=100, dump_time=1000):
    """Create the initial screw dislocation structure via LAMMPS.

    Returns the output_name_with_dislocation.
    """
    crystal_cell = f'./{working_folder}/{input_data_file_name_without_dislocation}'
    assert os.path.exists(crystal_cell), 'pristine data file does not exist.'

    _, specific_point_2, atoms = process_atoms(
        working_folder, input_data_file_name_without_dislocation, size_x, size_y)
    disl_x, disl_y = find_central_atoms(atoms, specific_point_2, 11)

    bash_script = f'''
clear
units metal
dimension 3
boundary p s p

shell cd ./{working_folder}

variable data_file string "{input_data_file_name_without_dislocation}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}

read_data ${{data_file}}
include ${{potential_file}}

change_box all triclinic

variable ymid equal {disl_y}

region bot_region block INF INF INF ${{ymid}} INF INF units box
region top_region block INF INF ${{ymid}} INF INF INF units box

group bot region bot_region
group top region top_region

variable Xmin_t equal bound(top,xmin)+4.01
variable Xmax_t equal bound(top,xmax)-4.01

variable bz equal {b}

displace_atoms top ramp z -${{bz}} 0 x ${{Xmin_t}} ${{Xmax_t}} units box

reset_timestep 0
dump last_dump all custom 1 dump.unrelaxed.{output_name_with_dislocation} id type x y z
run 0
undump last_dump

write_data data.unrelaxed.{output_name_with_dislocation}
'''
    lammps_script = f'{working_folder}/lmp_screw_script_initial.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        lammps_script,
        log_path=f'./{working_folder}/log.lammps_screw_initial',
        num_cpus=1)
    check_lammps_result(result)

    return output_name_with_dislocation


def create_screw_dislocation_final(working_folder, input_data_file_name_without_dislocation,
                                   output_name_with_dislocation, b, size_x, size_y,
                                   xshift, thermo_time=100, dump_time=1000):
    """Create the final screw dislocation structure (shifted) via LAMMPS.

    Returns the output_name_with_dislocation.
    """
    crystal_cell = f'./{working_folder}/{input_data_file_name_without_dislocation}'
    assert os.path.exists(crystal_cell), 'pristine data file does not exist.'

    _, specific_point_2, atoms = process_atoms(
        working_folder, input_data_file_name_without_dislocation, size_x, size_y)
    disl_x, disl_y = find_central_atoms(atoms, specific_point_2, 11)

    bash_script = f'''
clear
units metal
dimension 3
boundary p s p

shell cd ./{working_folder}

variable data_file string "{input_data_file_name_without_dislocation}"
variable potential_file string "potential.inp"
variable thermo_time equal {thermo_time}
variable dump_time equal {dump_time}

read_data ${{data_file}}
include ${{potential_file}}

change_box all triclinic

variable ymid equal {disl_y}

region bot_region block INF INF INF ${{ymid}} INF INF units box
region top_region block INF INF ${{ymid}} INF INF INF units box

group bot region bot_region
group top region top_region

variable change_xt equal 4.01+{xshift}

variable Xmin_t equal bound(top,xmin)+${{change_xt}}
variable Xmax_t equal bound(top,xmax)-4.01


variable bz equal {b}

displace_atoms top ramp z -${{bz}} 0 x ${{Xmin_t}} ${{Xmax_t}} units box

reset_timestep 0
dump last_dump all custom 1 dump.unrelaxed.{output_name_with_dislocation} id type x y z
run 0
undump last_dump

write_data data.unrelaxed.{output_name_with_dislocation}
'''
    lammps_script = f'{working_folder}/lmp_screw_script_final.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        lammps_script,
        log_path=f'./{working_folder}/log.lammps_screw_final',
        num_cpus=1)
    check_lammps_result(result)

    return output_name_with_dislocation


def relax_screw_dislocation(working_folder, input_data_file_name_without_dislocation,
                            input_data_file_name_with_dislocation, a, b,
                            thermo_time=100, dump_time=1000):
    """Relax a screw dislocation structure and produce a DD map.

    Returns JSON string with dimensions, potential energy, and DD map path.
    """
    os.makedirs(working_folder, exist_ok=True)

    unrelaxed_data_file_name = f'data.unrelaxed.{input_data_file_name_with_dislocation}'

    with open(f'{working_folder}/{unrelaxed_data_file_name}') as file:
        lines = file.readlines()
    lines_bounds = lines[5:8]
    Xmin = float(lines_bounds[0].strip().split()[0])
    Xmax = float(lines_bounds[0].strip().split()[1])
    Ymin = float(lines_bounds[1].strip().split()[0])
    Ymax = float(lines_bounds[1].strip().split()[1])
    Xmid = (Xmax + Xmin) / 2
    Ymid = (Ymax + Ymin) / 2

    bash_script = f'''
clear
units metal
dimension 3
boundary p s p

shell cd ./{working_folder}

variable data_file string "{unrelaxed_data_file_name}"
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

shell mkdir relax_screw_dislocation

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./relax_screw_dislocation/dump.out"
dump ${{dump_id}} all custom ${{dump_time}} ${{dump_out_name}}.* id type x y z c_peratom

variable p1 equal "step"
variable p2 equal "lx"
variable p3 equal "ly"
variable p4 equal "lz"
variable p5 equal "pe"
variable p6 equal "vol"

fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}}" file "dislocation.csv" title "#step a_x a_y a_z pe vol" screen no


variable iii loop 5
variable tol equal 0.1

reset_timestep 0
label min

fix min1 all box/relax x 0.0 z 0.0 xz 0.0 vmax 0.001
min_style cg
minimize 0 1e-4 2000 2000
unfix min1
min_style cg
minimize 0 1e-4 20000 20000

variable press_x equal abs(pxx)
variable press_z equal abs(pzz)
variable press_xz equal abs(pxz)
variable Fn equal "fnorm"

if "${{Fn}} < 1e-4 && ${{press_x}} < ${{tol}} && ${{press_z}} < ${{tol}} && ${{press_xz}} < ${{tol}}" then "jump SELF exit_label"

next iii
jump SELF min

label exit_label

undump ${{dump_id}}

reset_timestep 0
dump last_dump all custom 1 dump.relaxed.{input_data_file_name_with_dislocation} id type x y z c_peratom
run 0

write_data data.relaxed.{input_data_file_name_with_dislocation}

undump last_dump
unfix extra

quit
    '''

    lammps_script = f'{working_folder}/lmp_relax_screw_script.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        f'{working_folder}/lmp_relax_screw_script.in',
        log_path=f'./{working_folder}/log.lammps.relax_screw',
        num_cpus=4)

    if result.returncode == 0:
        pristine_data_file = f'{working_folder}/{input_data_file_name_without_dislocation}'
        dislocation_dump_file = f'dump.relaxed.{input_data_file_name_with_dislocation}'
        plot_path = create_DD_map(
            working_folder, a, b, Xmid, Ymid,
            pristine_data_file, dislocation_dump_file,
            input_data_file_name_with_dislocation)

        with open(f'./{working_folder}/dislocation.csv') as file:
            csv_lines = file.readlines()

        init_data = csv_lines[1].split(' ')
        final_data = csv_lines[-1].split(' ')

        pot_energy_final = float(final_data[4])
        Lx = float(init_data[1])
        Ly = float(init_data[2])
        Lz = float(init_data[3])

        potential_energy = pot_energy_final * 1000

        output_dict = {
            "Lx (A)": f'{Lx:.2f}',
            "Ly (A)": f'{Ly:.2f}',
            "Lz (A)": f'{Lz:.2f}',
            "potential energy(meV)": f'{potential_energy:.5f}',
            "dislocation_displacement_plot_path": plot_path
        }

        return json.dumps(output_dict)
    else:
        stderr_lines = result.stderr.strip().split('\n')[-2:]
        return json.dumps(stderr_lines, indent=4)


def generate_neb_dump_final(working_folder, final_dump_name):
    """Convert a LAMMPS dump file to NEB final configuration format.

    Returns the name of the generated NEB dump file.
    """
    with open(f'./{working_folder}/{final_dump_name}') as file:
        lines = file.readlines()

    init_index = None
    num_atoms_index = None

    for i, line in enumerate(lines):
        if re.search('ITEM: ATOMS', line):
            init_index = i
        if re.search('ITEM: NUMBER OF ATOMS', line):
            num_atoms_index = i

    if init_index is None or num_atoms_index is None:
        raise ValueError("Could not find the required indices in the file.")

    num_atoms = int(lines[num_atoms_index + 1].strip().split()[0])

    new_lines = []
    new_lines.append(f'{num_atoms}\n')
    for i in range(init_index + 1, init_index + 1 + num_atoms):
        line = lines[i].rstrip().split()
        new_lines.append(f'{line[0]} {line[2]} {line[3]} {line[4]}\n')

    with open(f'./{working_folder}/dump.neb.{final_dump_name}', 'w') as file:
        file.writelines(new_lines)

    return f'dump.neb.{final_dump_name}'

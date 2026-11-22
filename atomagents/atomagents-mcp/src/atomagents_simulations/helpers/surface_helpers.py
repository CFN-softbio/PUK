"""Surface energy periodic and free boundary LAMMPS simulations."""

from .lammps_runner import run_lammps_input, check_lammps_result


def surface_energy_periodic(working_folder, input_data_file_name, thermo_time, dump_time):
    """Run a periodic-boundary surface energy simulation.

    Returns:
        (pot_energy_initial, Lx, Ly, Lz, relaxed_data_file_name)
    """
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

shell mkdir surface_energy

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./surface_energy/dump.out"

variable p1 equal "step"
variable p2 equal "lx"
variable p3 equal "ly"
variable p4 equal "lz"
variable p5 equal "pe"
variable p6 equal "vol"

fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}}" file "surface_energy_periodic.csv" title "#step a_x a_y a_z pe vol" screen no

min_style cg
minimize 0 1e-5 20000 20000

fix 1 all box/relax aniso 0
min_style cg
minimize 0 1e-5 2000 20000
unfix 1

reset_timestep 0
run 0

unfix extra

write_data data.surface.energy.periodic.lmp
    '''

    lammps_script = f'{working_folder}/lmp_surface_energy_periodic_script.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        lammps_script,
        log_path=f'./{working_folder}/log.lammps.surface_energy_periodic',
        num_cpus=4)
    check_lammps_result(result)

    with open(f'./{working_folder}/surface_energy_periodic.csv') as file:
        lines = file.readlines()

    init_data = lines[-1].split(' ')

    pot_energy_initial = float(init_data[4])
    Lx = float(init_data[1])
    Ly = float(init_data[2])
    Lz = float(init_data[3])

    return pot_energy_initial, Lx, Ly, Lz, 'data.surface.energy.periodic.lmp'


def surface_energy_free(working_folder, input_data_file_name, surface_dir, thermo_time, dump_time):
    """Run a free-boundary surface energy simulation.

    Returns the final potential energy.
    """
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
variable surface_dir string {surface_dir}
variable xxx string "x"
variable yyy string "y"
variable zzz string "z"


read_data ${{data_file}}
include ${{potential_file}}

compute peratom all pe/atom
compute pe all pe

thermo_style custom step temp pe vol press pxx pyy pzz fnorm
thermo_modify format float %5.5g
thermo ${{thermo_time}}

shell mkdir surface_energy

variable dump_id equal 1
variable N equal 100
variable dump_out_name string "./surface_energy/dump.out"

variable p1 equal "step"
variable p2 equal "lx"
variable p3 equal "ly"
variable p4 equal "lz"
variable p5 equal "pe"
variable p6 equal "vol"

fix extra all print 100 "${{p1}} ${{p2}} ${{p3}} ${{p4}} ${{p5}} ${{p6}}" file "surface_energy_free.csv" title "#step a_x a_y a_z pe vol" screen no

if "${{surface_dir}}==${{xxx}} " then "change_box all boundary s p p"
if "${{surface_dir}}==${{yyy}} " then "change_box all boundary p s p"
if "${{surface_dir}}==${{zzz}} " then "change_box all boundary p p s"

min_style cg
minimize 0 1e-5 20000 20000

reset_timestep 0
run 0

unfix extra
    '''

    lammps_script = f'{working_folder}/lmp_surface_energy_free_script.in'
    with open(lammps_script, 'w') as f:
        f.write(bash_script)

    result = run_lammps_input(
        lammps_script,
        log_path=f'./{working_folder}/log.lammps.surface_energy_free',
        num_cpus=1)
    check_lammps_result(result)

    with open(f'./{working_folder}/surface_energy_free.csv') as file:
        lines = file.readlines()

    final_data = lines[-1].split(' ')
    pot_energy_final = float(final_data[4])

    return pot_energy_final

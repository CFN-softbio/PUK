"""Surface energy simulation tool."""

import json
import os

import numpy as np

from .setup import create_crystal
from ..helpers.single_step import single_step_simulation
from ..helpers.surface_helpers import surface_energy_periodic, surface_energy_free


def _append_surface_record(working_folder, conc_1, conc_2, surface_orientation, surface_dir, sample,
                           nx, ny, nz, Lx, Ly, Lz, pe_periodic, pe_free,
                           gamma_ev, gamma_j):
    """Append one plane/sample result to <working_folder>/surface_energies.csv."""
    path = os.path.join(working_folder, 'surface_energies.csv')
    write_header = not os.path.exists(path)
    plane = '[' + ','.join(str(int(v)) for v in surface_orientation) + ']'
    with open(path, 'a') as f:
        if write_header:
            f.write('conc_1,conc_2,plane,surface_dir,sample,nx,ny,nz,Lx,Ly,Lz,'
                    'pe_periodic_eV,pe_free_eV,gamma_eV_per_A2,gamma_J_per_m2\n')
        f.write(f'{conc_1},{conc_2},"{plane}",{surface_dir},{sample},{nx},{ny},{nz},{Lx},{Ly},{Lz},'
                f'{pe_periodic},{pe_free},{gamma_ev},{gamma_j}\n')


def surface_energy_simulation(working_folder: str, lat_type: str, lat_const: float,
                              conc_1: int, conc_2: int, mtp_pot: bool,
                              orient_x: list, orient_y: list, orient_z: list,
                              surface_orientation: list, surface_dir: str,
                              L_periodic: float = 30, L_free: float = 60,
                              thermo_time: int = 100, dump_time: int = 1000) -> str:
    """Compute surface energy for a specific crystal plane.

    Args:
        working_folder: Working directory for results.
        lat_type: "fcc" or "bcc".
        lat_const: Lattice constant from lattice_constant_simulation.
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in %.
        mtp_pot: True for MTP potential.
        orient_x: Crystal orientation along x.
        orient_y: Crystal orientation along y.
        orient_z: Crystal orientation along z.
        surface_orientation: The target free surface plane.
        surface_dir: Which axis is the free surface direction: "x", "y", or "z".
        L_periodic: Cell length along periodic directions (default 30 A).
        L_free: Cell length along free direction (default 60 A).
        thermo_time: Thermodynamic output interval.
        dump_time: Dump output interval.

    Returns:
        JSON string with surface energy in eV/A^2 and J/m^2.
    """
    os.makedirs(working_folder, exist_ok=True)

    assert conc_1 + conc_2 == 100, 'the concentrations should sum up to 100.'

    if conc_1 != 0 and conc_1 != 100:
        total_samples = 3
    else:
        total_samples = 1

    create_crystal(working_folder, 'unit_lattice.lmp',
                   lat_type, lat_const,
                   conc_1, conc_2, mtp_pot,
                   orient_x, orient_y, orient_z,
                   10, 10, 10)

    res_step = json.loads(single_step_simulation(working_folder, 'unit_lattice.lmp', 10, 10, 10))

    xlat = float(res_step['xlat (A)'])
    ylat = float(res_step['ylat (A)'])
    zlat = float(res_step['zlat (A)'])

    if surface_dir == 'x':
        nx = int(np.ceil(L_free / xlat))
        ny = int(np.ceil(L_periodic / ylat))
        nz = int(np.ceil(L_periodic / zlat))
    elif surface_dir == 'y':
        nx = int(np.ceil(L_periodic / xlat))
        ny = int(np.ceil(L_free / ylat))
        nz = int(np.ceil(L_periodic / zlat))
    elif surface_dir == 'z':
        nx = int(np.ceil(L_periodic / xlat))
        ny = int(np.ceil(L_periodic / ylat))
        nz = int(np.ceil(L_free / zlat))
    else:
        raise ValueError(f"surface_dir must be 'x', 'y', or 'z', got '{surface_dir}'")

    assert np.dot(orient_x, orient_y) == 0, 'orient_x and orient_y are not orthogonal.'
    assert np.dot(orient_x, orient_z) == 0, 'orient_x and orient_z are not orthogonal.'
    assert np.dot(orient_y, orient_z) == 0, 'orient_y and orient_z are not orthogonal.'

    if surface_dir == 'x':
        assert (np.abs(orient_x[0]) == np.abs(surface_orientation[0]) and
                np.abs(orient_x[1]) == np.abs(surface_orientation[1]) and
                np.abs(orient_x[2]) == np.abs(surface_orientation[2])), \
            f'x direction is not aligned with surface orientation {surface_orientation}.'
    elif surface_dir == 'y':
        assert (np.abs(orient_y[0]) == np.abs(surface_orientation[0]) and
                np.abs(orient_y[1]) == np.abs(surface_orientation[1]) and
                np.abs(orient_y[2]) == np.abs(surface_orientation[2])), \
            f'y direction is not aligned with surface orientation {surface_orientation}.'
    elif surface_dir == 'z':
        assert (np.abs(orient_z[0]) == np.abs(surface_orientation[0]) and
                np.abs(orient_z[1]) == np.abs(surface_orientation[1]) and
                np.abs(orient_z[2]) == np.abs(surface_orientation[2])), \
            f'z direction is not aligned with surface orientation {surface_orientation}.'

    surface_energy_all = []
    surface_energy_mj_all = []
    for num_samples in range(total_samples):
        input_data_file_name = create_crystal(
            working_folder, 'surface_energy.lmp',
            lat_type, lat_const,
            conc_1, conc_2, mtp_pot,
            orient_x, orient_y, orient_z,
            nx, ny, nz)

        pot_energy_init, Lx, Ly, Lz, relaxed_structure = surface_energy_periodic(
            working_folder, input_data_file_name, thermo_time, dump_time)
        pot_energy_final = surface_energy_free(
            working_folder, relaxed_structure, surface_dir, thermo_time, dump_time)

        if surface_dir == 'x':
            surface_energy = (pot_energy_final - pot_energy_init) / (2 * Ly * Lz)
        elif surface_dir == 'y':
            surface_energy = (pot_energy_final - pot_energy_init) / (2 * Lx * Lz)
        elif surface_dir == 'z':
            surface_energy = (pot_energy_final - pot_energy_init) / (2 * Lx * Ly)

        surface_energy_mj = surface_energy * 16.0218

        surface_energy_all.append(surface_energy)
        surface_energy_mj_all.append(surface_energy_mj)

        # surface_energy_{periodic,free}.csv are overwritten by every call, so keep
        # one summary row per plane and sample
        _append_surface_record(working_folder, conc_1, conc_2, surface_orientation, surface_dir, num_samples,
                               nx, ny, nz, Lx, Ly, Lz, pot_energy_init, pot_energy_final,
                               surface_energy, surface_energy_mj)

    output_dict = {
        'surface energy (eV/A^2)': f'{np.mean(surface_energy_all):.3f}',
        'surface energy (J/m^2)': f'{np.mean(surface_energy_mj_all):.3f}'
    }

    return json.dumps(output_dict)

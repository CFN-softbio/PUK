"""Setup tools: create_working_folder, create_potential_file, create_crystal."""

import json
import os
import re

import numpy as np
from ase.io import lammpsdata
from ase.lattice.cubic import BodyCenteredCubic, FaceCenteredCubic

from ..helpers.crystal_ops import gcd_of_vector


def create_working_folder(working_folder: str) -> str:
    """Create a working directory for simulation output.

    Args:
        working_folder: Name for the project's working directory.

    Returns:
        Confirmation message with the folder name.
    """
    os.makedirs(working_folder, exist_ok=True)
    return f"Working folder: {working_folder}"


def create_potential_file(working_folder: str, pair_style_text: str, pair_coeff_text: str) -> str:
    """Write the LAMMPS potential.inp configuration file.

    Args:
        working_folder: Working directory for the project.
        pair_style_text: Interatomic potential pair style,
            e.g. "eam/alloy" for EAM, "mlip ../potential_repository/NbMo.mtp" for MTP.
        pair_coeff_text: Pair coefficient line,
            e.g. "* * ../potential_repository/Al99.eam.alloy Al" for EAM,
            "* *" for MTP (no argument needed).

    Returns:
        Path to the created potential file.
    """
    os.makedirs(working_folder, exist_ok=True)

    content = f'pair_style {pair_style_text} \npair_coeff {pair_coeff_text}'

    assert re.search('../potential_repository/', content), \
        "../potential_repository/ not defined in pair_style or pair_coeff"
    assert re.search(r'\* \*', content), "pair_coeff must have * *"

    if re.search('pair_coeff pair_coeff', content):
        raise TypeError(
            "The function returned an extra 'pair_coeff' string. "
            "Only one 'pair_coeff * *' is expected. "
            "Please provide pair_coeff_text without 'pair_coeff'.")
    if re.search('pair_style pair_style', content):
        raise TypeError("pair_style is repeated!")

    filename = f'./{working_folder}/potential.inp'
    with open(filename, 'w') as file:
        file.write(content)

    return filename


def create_crystal(working_folder: str, output_name: str, lat_type: str,
                   lat_const: float, conc_1: int, conc_2: int, mtp_pot: bool,
                   orient_x: list, orient_y: list, orient_z: list,
                   size_x: int, size_y: int, size_z: int) -> str:
    """Generate an FCC or BCC crystal structure as a LAMMPS data file.

    Args:
        working_folder: Working directory.
        output_name: Name of the output file (use .lmp extension).
        lat_type: "fcc" or "bcc".
        lat_const: Lattice constant (should be computed by lattice_constant_simulation).
        conc_1: Concentration of first element in %.
        conc_2: Concentration of second element in %.
        mtp_pot: True for MTP potential, False otherwise.
        orient_x: Crystal orientation along x, e.g. [1, -1, 1].
        orient_y: Crystal orientation along y.
        orient_z: Crystal orientation along z.
        size_x: Crystal size in lattice units along x.
        size_y: Crystal size in lattice units along y.
        size_z: Crystal size in lattice units along z.

    Returns:
        The output file name.
    """
    os.makedirs(working_folder, exist_ok=True)

    # Validate orthogonality
    if np.dot(orient_x, orient_y) == 0 and (np.dot(orient_x, orient_z) != 0 or np.dot(orient_y, orient_z) != 0):
        orient_3 = list(np.cross(orient_x, orient_y))
        gcd = gcd_of_vector(orient_3)
        if gcd != 0:
            orient_3 = [int(xxx / gcd) for xxx in orient_3]
        raise ValueError(f"the orientations are not orthogonal. Choose orient_z as {orient_3}")

    elif np.dot(orient_x, orient_z) == 0 and (np.dot(orient_x, orient_y) != 0 or np.dot(orient_z, orient_y) != 0):
        orient_3 = list(np.cross(orient_z, orient_x))
        gcd = gcd_of_vector(orient_3)
        if gcd != 0:
            orient_3 = [int(xxx / gcd) for xxx in orient_3]
        raise ValueError(f"the orientations are not orthogonal. Choose orient_y as {orient_3}")

    elif np.dot(orient_y, orient_z) == 0 and (np.dot(orient_y, orient_x) != 0 or np.dot(orient_z, orient_x) != 0):
        orient_3 = list(np.cross(orient_y, orient_z))
        gcd = gcd_of_vector(orient_3)
        if gcd != 0:
            orient_3 = [int(xxx / gcd) for xxx in orient_3]
        raise ValueError(f"the orientations are not orthogonal. Choose orient_x as {orient_3}")

    assert conc_1 + conc_2 == 100, 'the sum of concentrations should be 100'

    file_output_name = f'./{working_folder}/{output_name}'

    try:
        os.remove(file_output_name)
    except FileNotFoundError:
        pass

    def _make_atoms(lat_type, orient_x, orient_y, orient_z, size_x, size_y, size_z, lat_const):
        if lat_type == 'bcc':
            return BodyCenteredCubic(directions=[orient_x, orient_y, orient_z],
                                    size=(size_x, size_y, size_z),
                                    symbol='X', latticeconstant=lat_const)
        elif lat_type == 'fcc':
            return FaceCenteredCubic(directions=[orient_x, orient_y, orient_z],
                                    size=(size_x, size_y, size_z),
                                    symbol='X', latticeconstant=lat_const)
        else:
            raise ValueError(f"Unknown lattice type: {lat_type}")

    if conc_1 == 100:
        atoms = _make_atoms(lat_type, orient_x, orient_y, orient_z, size_x, size_y, size_z, lat_const)
        lammpsdata.write_lammps_data(file_output_name, atoms)

        with open(file_output_name) as file:
            lines = file.readlines()
        new_lines = []
        for line in lines:
            if re.search(r'Atoms # atomic', line):
                new_lines.append('Masses\n\n')
                new_lines.append('1 1\n\n')
            new_lines.append(line)
        with open(file_output_name, 'w') as file:
            file.writelines(new_lines)

    elif conc_2 == 100:
        assert mtp_pot, 'It sounds you have MTP potential. If not set conc_1=100 and conc_2=0'
        atoms = _make_atoms(lat_type, orient_x, orient_y, orient_z, size_x, size_y, size_z, lat_const)
        atoms.symbols[0] = 'Nb'
        lammpsdata.write_lammps_data(file_output_name, atoms)

        with open(file_output_name) as file:
            lines = file.readlines()
        new_lines = []
        for line in lines:
            if re.search(r' 1   1', line):
                parts = re.split(r'(\s+)', line)
                parts[4] = '2'
                line = ''.join(parts)
            if re.search(r'Atoms # atomic', line):
                new_lines.append('Masses\n\n')
                new_lines.append('1 1\n')
                new_lines.append('2 1\n\n')
            new_lines.append(line)
        with open(file_output_name, 'w') as file:
            file.writelines(new_lines)

    else:  # conc_1 != 100 and conc_1 != 0
        atoms = _make_atoms(lat_type, orient_x, orient_y, orient_z, size_x, size_y, size_z, lat_const)
        atom_indices = np.random.permutation(len(atoms))
        atoms.symbols[atom_indices[:int(len(atoms) * conc_1 / 100)]] = 'X'
        atoms.symbols[atom_indices[int(len(atoms) * conc_1 / 100):len(atoms)]] = 'Y'
        lammpsdata.write_lammps_data(file_output_name, atoms)

        with open(file_output_name) as file:
            lines = file.readlines()
        new_lines = []
        for line in lines:
            if re.search(r'Atoms # atomic', line):
                new_lines.append('Masses\n\n')
                new_lines.append('1 1\n')
                new_lines.append('2 1\n\n')
            new_lines.append(line)
        with open(file_output_name, 'w') as file:
            file.writelines(new_lines)

    return output_name

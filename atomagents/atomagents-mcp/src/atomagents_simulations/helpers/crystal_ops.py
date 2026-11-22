"""Crystal structure helper operations."""

import re
import math
from functools import reduce

import numpy as np
import pandas as pd


def gcd_of_vector(vector):
    """Compute the GCD of all components of an integer vector."""
    if isinstance(vector, np.ndarray):
        vector = vector.tolist()
    return reduce(math.gcd, [int(v) for v in vector])


def cross_orientations(orient_1: list, orient_2: list) -> list:
    """Compute the cross product of two crystal orientations, reduced by GCD."""
    orient_3 = list(np.cross(orient_1, orient_2))
    gcd = gcd_of_vector(orient_3)
    if gcd != 0:
        orient_3 = [int(x / gcd) for x in orient_3]
    return orient_3


def b_calculator(lattice_constant: float, B_miller: float) -> float:
    """Compute Burgers vector magnitude.

    Args:
        lattice_constant: Lattice constant in Angstrom.
        B_miller: Magnitude of Burgers miller index,
            e.g. sqrt(3)/2 for 1/2[111] dislocation.
    """
    return round(B_miller * lattice_constant, 2)


def format_columns(line, widths):
    """Format a line of data with fixed column widths."""
    formatted_line = []
    for i, element in enumerate(line):
        formatted_line.append(f"{element:<{widths[i]}}")
    return ' '.join(formatted_line).rstrip() + '\n'


def random_alloy_solutes(input_file: str, concentration_1: int):
    """Randomly assign solute types in a LAMMPS data file.

    Args:
        input_file: Path to LAMMPS data file to modify in-place.
        concentration_1: Concentration of the first element in %.
    """
    with open(input_file, 'r') as file:
        lines = file.readlines()

    init_index = None
    num_atoms_index = None

    for i, line in enumerate(lines):
        if re.search('Atoms # atomic', line):
            init_index = i
        if re.search('atoms', line):
            num_atoms_index = i

    if init_index is None or num_atoms_index is None:
        raise ValueError("Could not find the required indices in the file.")

    num_atoms = int(lines[num_atoms_index].strip().split()[0])

    new_lines = []

    atom_indices = np.random.permutation(num_atoms)
    atom_types = np.zeros(num_atoms)
    atom_types[atom_indices[:int(num_atoms * concentration_1 / 100)]] = 1
    atom_types[atom_indices[int(num_atoms * concentration_1 / 100):num_atoms]] = 2

    new_lines.extend(lines[:init_index + 2])

    column_widths = [8, 4] + [15] * (len(lines[init_index + 2].split()) - 2)

    k = 0
    for i in range(init_index + 2, init_index + 2 + num_atoms):
        new_line = lines[i].rstrip().split()
        new_line[1] = str(int(atom_types[k]))
        new_lines.append(format_columns(new_line, column_widths))
        k += 1
    new_lines.extend(lines[init_index + 2 + num_atoms:])

    output_string = ''.join(new_lines)

    with open(input_file, 'w') as file:
        file.write(output_string)


def find_central_atoms(atoms, specific_point, threshold_distance=4):
    """Find the three central atoms nearest to a specific point.

    Returns the dislocation center [x, y] coordinates.
    """
    df = pd.DataFrame(atoms, columns=['atom_id', 'atom_x', 'atom_y', 'atom_z'])
    df['distance'] = np.sqrt((df['atom_x'] - specific_point[0])**2 +
                             (df['atom_y'] - specific_point[1])**2)

    close_atoms = df[df['distance'] <= threshold_distance]
    assert len(close_atoms) >= 3, "nearest atoms are less than 3"

    sorted_close_atoms = close_atoms.sort_values(by='distance')
    sorted_close_atom_ids = sorted_close_atoms['atom_id'].tolist()

    id_remove = []
    coords = sorted_close_atoms[['atom_x', 'atom_y']].values

    for i in range(len(sorted_close_atom_ids)):
        for j in range(i + 1, len(sorted_close_atom_ids)):
            if np.all(np.abs(coords[i] - coords[j]) < 0.01):
                id_remove.append(sorted_close_atom_ids[j])

    sorted_close_atom_ids = [id for id in sorted_close_atom_ids if id not in id_remove]

    id_central_atoms = sorted_close_atom_ids[:3]

    xxx = sorted_close_atoms.loc[sorted_close_atoms['atom_id'].isin(id_central_atoms), 'atom_x'].values
    yyy = sorted_close_atoms.loc[sorted_close_atoms['atom_id'].isin(id_central_atoms), 'atom_y'].values

    dislocation_cent = [np.mean(xxx), min(yyy) + 1/3 * (max(yyy) - min(yyy))]
    return dislocation_cent


def process_atoms(working_folder, data_file, size_x, size_y):
    """Read a LAMMPS data file and extract atom positions and cell centers.

    Returns:
        (atom_cent_1, atom_cent_2, atom_list) where atom_list is
        [[id, x, y, z], ...].
    """
    with open(f'./{working_folder}/{data_file}') as file:
        lines = file.readlines()

    init_index = None
    num_atoms_index = None
    num_x = None
    num_y = None

    for i, line in enumerate(lines):
        if re.search('Atoms', line):
            init_index = i
        if re.search('atoms', line):
            num_atoms_index = i
        if re.search('xlo xhi', line):
            num_x = i
        if re.search('ylo yhi', line):
            num_y = i

    if init_index is None or num_atoms_index is None or num_x is None or num_y is None:
        raise ValueError("Could not find the required indices in the file.")

    xlo, xhi = float(lines[num_x].strip().split()[0]), float(lines[num_x].strip().split()[1])
    ylo, yhi = float(lines[num_y].strip().split()[0]), float(lines[num_y].strip().split()[1])

    xcent = (xlo + xhi)
    ycent = (ylo + yhi)

    unitx = (xhi - xlo) / size_x / 3
    unity = (yhi - ylo) / size_y / 2

    atom_cent_1 = [(xcent) / 2, (ycent - unity) / 2]
    atom_cent_2 = [(xcent) / 2 + unitx, (ycent - unity) / 2]

    num_atoms = int(lines[num_atoms_index].strip().split()[0])

    new_lines = []
    for i in range(init_index + 2, init_index + 2 + num_atoms):
        line = lines[i].rstrip().split()
        new_lines.append([int(line[0]), float(line[2]), float(line[3]), float(line[4])])

    return atom_cent_1, atom_cent_2, new_lines

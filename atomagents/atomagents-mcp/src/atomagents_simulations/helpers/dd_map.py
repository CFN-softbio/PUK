"""Differential displacement map creation for screw dislocations."""

import numpy as np
import matplotlib.pyplot as plt
import atomman as am


def create_DD_map(working_folder: str, a: float, b: float,
                  xmid: float, ymid: float,
                  pristine_data_file: str, dislocation_dump_file: str,
                  input_data_file_name_with_dislocation: str) -> str:
    """Create a differential displacement map and save as PNG.

    Args:
        working_folder: Working directory path.
        a: Lattice constant in Angstrom.
        b: Burgers vector magnitude in Angstrom.
        xmid: X center of the view region.
        ymid: Y center of the view region.
        pristine_data_file: Path to the pristine LAMMPS data file.
        dislocation_dump_file: Filename of the relaxed dislocation dump.
        input_data_file_name_with_dislocation: Name label for the output.

    Returns:
        Path to the saved DD map PNG file.
    """
    vburger = np.array([0.0, 0.0, b])

    base_system = am.load('atom_data', f'{pristine_data_file}')
    disl_system = am.load('atom_dump', f'./{working_folder}/{dislocation_dump_file}')

    xlim = (-6 + xmid, 6 + xmid)
    ylim = (-8 + ymid, 5 + ymid)

    neighb_cutoff = 0.9 * a
    base_system.pbc = (False, False, True)

    zlim = (-0.01, -0.01 + b)
    am.defect.differential_displacement(
        base_system, disl_system, vburger,
        cutoff=neighb_cutoff, xlim=xlim, ylim=ylim, zlim=zlim,
        display_final_pos=True, plot_scale=3
    )

    label = input_data_file_name_with_dislocation.replace('.lmp', '')
    plot_path = f'./{working_folder}/DD_plot.{label}.png'
    plt.savefig(plot_path)
    plt.close()

    return plot_path

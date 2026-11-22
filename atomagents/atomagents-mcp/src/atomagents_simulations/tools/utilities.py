"""Utility tools: suggest_orientation, list_potentials."""

import json
from pathlib import Path

import numpy as np

from ..helpers.crystal_ops import gcd_of_vector, cross_orientations
from ..config import get_potential_repository


def suggest_orientation(orientation: list) -> str:
    """Compute orthogonal crystal orientations given one or two known orientations.

    Given a single orientation, finds two additional orthogonal directions.
    Given two orientations, computes the third via cross product.

    Args:
        orientation: A list of one or two crystal orientations.
            Single: [[1, 1, 0]]
            Two: [[1, 1, 0], [0, 0, 1]]

    Returns:
        JSON string with three orthogonal crystal orientations.
    """
    if isinstance(orientation[0], (list, tuple)):
        # Multiple orientations provided
        if len(orientation) >= 2:
            o1 = list(orientation[0])
            o2 = list(orientation[1])
            o3 = cross_orientations(o1, o2)
            return json.dumps({"orient_x": o1, "orient_y": o2, "orient_z": o3})
        else:
            o1 = list(orientation[0])
    else:
        o1 = list(orientation)

    # Find simplest orthogonal vector
    o1_arr = np.array(o1)
    # Try standard basis vectors
    candidates = [[1, 0, 0], [0, 1, 0], [0, 0, 1],
                  [1, 1, 0], [1, 0, 1], [0, 1, 1],
                  [1, -1, 0], [1, 0, -1], [0, 1, -1]]

    o2 = None
    for c in candidates:
        if np.dot(o1_arr, np.array(c)) == 0:
            o2 = c
            break

    if o2 is None:
        # Construct orthogonal vector manually
        if o1[0] != 0:
            o2 = [-o1[1], o1[0], 0]
        else:
            o2 = [0, -o1[2], o1[1]]
        gcd = gcd_of_vector(o2)
        if gcd != 0:
            o2 = [int(x / gcd) for x in o2]

    o3 = cross_orientations(o1, o2)

    return json.dumps({"orient_x": o1, "orient_y": o2, "orient_z": o3})


def list_potentials() -> str:
    """List all available interatomic potential files with their types.

    Returns:
        JSON string with a list of potential files and metadata.
    """
    pot_dir = get_potential_repository()
    if not pot_dir.exists():
        return json.dumps({"error": f"Potential repository not found at {pot_dir}"})

    potentials = []
    for f in sorted(pot_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.'):
            suffix = f.suffix.lower()
            if suffix in ('.alloy', '.fs'):
                pot_type = 'EAM'
            elif suffix == '.meam' or f.name.endswith('.library.meam'):
                pot_type = 'MEAM'
            elif suffix == '.mtp':
                pot_type = 'MTP'
            elif suffix == '.sw':
                pot_type = 'Stillinger-Weber'
            else:
                pot_type = 'unknown'
            potentials.append({
                "name": f.name,
                "type": pot_type,
                "path": f"../potential_repository/{f.name}",
            })

    return json.dumps(potentials, indent=2)

"""Potential listing and metadata resources."""

import json
from pathlib import Path

from ..config import get_potential_repository


def list_all_potentials() -> str:
    """List all potential files with metadata."""
    pot_dir = get_potential_repository()
    if not pot_dir.exists():
        return json.dumps({"error": f"Potential repository not found at {pot_dir}"})

    potentials = []
    for f in sorted(pot_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.'):
            suffix = f.suffix.lower()
            size_kb = f.stat().st_size / 1024

            if suffix == '.alloy':
                pot_type = 'EAM/alloy'
                pair_style = 'eam/alloy'
                pair_coeff_example = f'* * ../potential_repository/{f.name} <Element1> <Element2>'
            elif suffix == '.fs':
                pot_type = 'EAM/fs'
                pair_style = 'eam/fs'
                pair_coeff_example = f'* * ../potential_repository/{f.name} <Element1> <Element2>'
            elif f.name.endswith('.library.meam'):
                pot_type = 'MEAM library'
                pair_style = 'meam'
                pair_coeff_example = f'* * ../potential_repository/{f.name} <Element> <atom_file>.meam <Element>'
                continue  # Library files are referenced by .meam files
            elif suffix == '.meam':
                pot_type = 'MEAM'
                pair_style = 'meam'
                lib_name = f.stem + '.library.meam'
                pair_coeff_example = f'* * ../potential_repository/{lib_name} <Element> ../potential_repository/{f.name} <Element>'
            elif suffix == '.mtp':
                pot_type = 'MTP (Machine-learned)'
                pair_style = f'mlip ../potential_repository/{f.name}'
                pair_coeff_example = '* *'
            elif suffix == '.sw':
                pot_type = 'Stillinger-Weber'
                pair_style = 'sw'
                pair_coeff_example = f'* * ../potential_repository/{f.name} <Element>'
            else:
                pot_type = 'unknown'
                pair_style = 'unknown'
                pair_coeff_example = ''

            potentials.append({
                "name": f.name,
                "type": pot_type,
                "size_kb": round(size_kb, 1),
                "pair_style": pair_style,
                "pair_coeff_example": pair_coeff_example,
            })

    return json.dumps(potentials, indent=2)


def get_potential_metadata(name: str) -> str:
    """Get metadata and usage hints for a specific potential."""
    pot_dir = get_potential_repository()
    pot_file = pot_dir / name

    if not pot_file.exists():
        return json.dumps({"error": f"Potential file '{name}' not found"})

    suffix = pot_file.suffix.lower()
    size_kb = pot_file.stat().st_size / 1024

    # Read first few lines for header info
    try:
        with open(pot_file, 'r', errors='replace') as f:
            header_lines = [f.readline().strip() for _ in range(5)]
    except Exception:
        header_lines = ["(binary file)"]

    if suffix == '.alloy':
        usage = {
            "pair_style": "eam/alloy",
            "pair_coeff": f"* * ../potential_repository/{name} <Element1> <Element2>",
            "mtp_pot": False,
        }
    elif suffix == '.fs':
        usage = {
            "pair_style": "eam/fs",
            "pair_coeff": f"* * ../potential_repository/{name} <Element1> <Element2>",
            "mtp_pot": False,
        }
    elif suffix == '.meam':
        stem = pot_file.stem
        lib_name = f"{stem}.library.meam"
        usage = {
            "pair_style": "meam",
            "pair_coeff": f"* * ../potential_repository/{lib_name} <Element> ../potential_repository/{name} <Element>",
            "mtp_pot": False,
        }
    elif suffix == '.mtp':
        usage = {
            "pair_style": f"mlip ../potential_repository/{name}",
            "pair_coeff": "* *",
            "mtp_pot": True,
        }
    elif suffix == '.sw':
        usage = {
            "pair_style": "sw",
            "pair_coeff": f"* * ../potential_repository/{name} <Element>",
            "mtp_pot": False,
        }
    else:
        usage = {"note": "Unknown potential type"}

    metadata = {
        "name": name,
        "size_kb": round(size_kb, 1),
        "header": header_lines,
        "usage": usage,
    }

    return json.dumps(metadata, indent=2)

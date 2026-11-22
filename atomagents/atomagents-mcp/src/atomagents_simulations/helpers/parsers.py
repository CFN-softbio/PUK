"""Parsers for LAMMPS output files (CSV, log, dump)."""


def parse_csv_last_line(filepath: str) -> list[str]:
    """Read a LAMMPS fix-print CSV file and return the last data line split by spaces."""
    with open(filepath) as f:
        lines = f.readlines()
    return lines[-1].split(' ')


def parse_csv_first_and_last(filepath: str) -> tuple[list[str], list[str]]:
    """Return (first_data_line, last_data_line) from a LAMMPS CSV file.

    Skips the header line (first line starting with #).
    """
    with open(filepath) as f:
        lines = f.readlines()
    return lines[1].split(' '), lines[-1].split(' ')


def parse_elastic_constants(filepath: str) -> dict:
    """Parse elastic constants CSV and return a dict of all values."""
    with open(filepath) as f:
        lines = f.readlines()
    final_data = lines[-1].split(' ')
    keys = ['C11', 'C12', 'C13', 'C14', 'C15', 'C16',
            'C22', 'C23', 'C24', 'C25', 'C26',
            'C33', 'C34', 'C35', 'C36',
            'C44', 'C45', 'C46',
            'C55', 'C56',
            'C66',
            'bulk_modulus', 'shear_modulus', 'poisson_ratio']
    return {k: float(v) for k, v in zip(keys, final_data)}

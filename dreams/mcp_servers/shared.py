"""
Shared configuration and utilities for DREAMS MCP servers.
Both the DFT and HPC servers import from here.
"""

import os
import sqlite3
import yaml
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Utility functions inlined from src/utils.py to avoid langchain_core dependency
# ---------------------------------------------------------------------------


def initialize_database(db_file):
    """Create the resource suggestions SQLite database."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS resources (
        filename TEXT PRIMARY KEY,
        partition TEXT,
        nnodes INTEGER,
        ntasks INTEGER,
        runtime INTEGER,
        submissionScript TEXT,
        outputFilename TEXT
    )
    ''')
    conn.commit()
    conn.close()


def add_to_database(resource_dict, db_file):
    """Insert or update resource suggestions."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    for filename, resources in resource_dict.items():
        cursor.execute('''
        INSERT OR REPLACE INTO resources (filename, partition, nnodes, ntasks, runtime, submissionScript, outputFilename)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename,
              resources['partition'],
              resources['nnodes'],
              resources['ntasks'],
              resources['runtime'],
              resources['submissionScript'],
              resources['outputFilename']))
    conn.commit()
    conn.close()


def create_pysqa_prerequisites(working_directory: str):
    """Create slurm.sh and queue.yaml for pysqa in the working directory."""
    with open(os.path.join(working_directory, "slurm.sh"), "w") as f:
        f.write(r"""#!/bin/bash
#SBATCH -J {{job_name}} # Job name
#SBATCH -n {{cores_max}} # Number of total cores
#SBATCH -N {{nodes_max}} # Number of nodes
#SBATCH --time={{run_time_max | int}}
#SBATCH -p {{partition}}
#SBATCH --mem-per-cpu={{memory_max}}M # Memory pool for all cores in MB
#SBATCH -e {{errNoutName}}.err #change the name of the err file
#SBATCH -o {{errNoutName}}.out # File to which STDOUT will be written %j is the job #

{{command}}

                   """)
    with open(os.path.join(working_directory, "queue.yaml"), "w") as f:
        f.write(r"""queue_type: SLURM
queue_primary: slurm
queues:
  slurm: {
    job_name: testPysqa,
    cores_max: 4,
    cores_min: 1,
    nodes_max: 1,
    memory_max: 2000,
    partition: venkvis-cpu,
    script: slurm.sh
    }
                   """)


def select_k_ecut(convergence_data: pd.DataFrame, error_threshold: float, natom: int):
    """Select optimal k-point spacing and ecutwfc from convergence test results."""
    min_kspacing = convergence_data['kspacing'].min()
    max_ecutwfc = convergence_data['ecutwfc'].max()

    df_kspacing = convergence_data.loc[convergence_data['kspacing'] == min_kspacing].sort_values(by='ecutwfc', ascending=True)
    df_kspacing['error'] = (df_kspacing['energy'] - df_kspacing.iloc[-1]['energy']).abs() / natom * 1000
    df_kspacing['Acceptable'] = df_kspacing['error'] < error_threshold
    ecutwfc_chosen = df_kspacing[df_kspacing['Acceptable']].iloc[0]['ecutwfc']
    finer_ecut = ecutwfc_chosen == max_ecutwfc

    df_ecutwfc = convergence_data.loc[convergence_data['ecutwfc'] == max_ecutwfc].sort_values(by='kspacing', ascending=False)
    df_ecutwfc['error'] = (df_ecutwfc['energy'] - df_ecutwfc.iloc[-1]['energy']).abs() / natom * 1000
    df_ecutwfc['Acceptable'] = df_ecutwfc['error'] < error_threshold
    k_chosen = df_ecutwfc[df_ecutwfc['Acceptable']].iloc[0]['kspacing']
    finer_kspacing = k_chosen == min_kspacing

    return k_chosen, ecutwfc_chosen, finer_ecut, df_kspacing, df_ecutwfc, finer_kspacing


def read_BEEF_output(file_path: str):
    """Read BEEF ensemble energies from a QE output file."""
    from ase.io import read as ase_read
    with open(file_path, 'r') as f:
        lines = f.readlines()
    atoms = ase_read(file_path)
    reference = atoms.get_potential_energy()
    start_index = 0
    end_index = 0
    for i, line in enumerate(lines):
        if 'BEEFens 2000 ensemble energies' in line:
            start_index = i + 1
        if 'BEEF-vdW xc energy contributions' in line:
            end_index = i - 2
    if start_index == 0 or end_index == 0:
        return "WrongCalc"
    energies = []
    for i in range(start_index, end_index + 1):
        energies.append(float(lines[i].split()[0]) + reference)
    return np.array(energies)


def load_config() -> dict:
    """Load configuration from DREAMS_CONFIG env var or default path."""
    config_path = os.environ.get(
        "DREAMS_CONFIG",
        os.path.join(PROJECT_ROOT, "config", "default.yaml"),
    )
    with open(config_path) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    # Relative paths in the config are relative to the project root
    for key in ("PSEUDO_DIR", "WORKING_DIR"):
        if not os.path.isabs(config[key]):
            config[key] = os.path.join(PROJECT_ROOT, config[key])
    return config


def init_working_dir(config: dict) -> str:
    """Ensure working directory exists and initialize resource DB."""
    working_dir = config["WORKING_DIR"]
    os.makedirs(working_dir, exist_ok=True)

    db_file = os.path.join(working_dir, "resource_suggestions.db")
    if not os.path.exists(db_file):
        initialize_database(db_file)

    return working_dir


# Module-level singletons -- initialized on first import
_config = None
_working_dir = None
_pseudo_dir = None


def get_config() -> dict:
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_working_dir() -> str:
    global _working_dir
    if _working_dir is None:
        _working_dir = init_working_dir(get_config())
    return _working_dir


def get_pseudo_dir() -> str:
    global _pseudo_dir
    if _pseudo_dir is None:
        _pseudo_dir = get_config()["PSEUDO_DIR"]
    return _pseudo_dir

#!/usr/bin/env python
"""
DREAMS HPC MCP Server

Exposes tools for SLURM job submission, resource suggestion, and monitoring
on the Artemis HPC cluster via the Model Context Protocol.
"""

import os
import json
import time
import sqlite3
from copy import deepcopy

from mcp.server.fastmcp import FastMCP

from mcp_servers.shared import (
    get_config, get_working_dir,
    initialize_database, create_pysqa_prerequisites,
)

from ase.io import read
from pysqa import QueueAdapter

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "dreams-hpc",
    instructions=(
        "DREAMS HPC server — tools for SLURM job resource planning, "
        "submission, and monitoring on the Artemis cluster.\n\n"
        "Artemis cluster specs:\n"
        "  Partitions: venkvis-cpu (48hr), venkvis-a100 (8hr), venkvis-h100 (8hr)\n"
        "  CPU nodes: 25x AMD 9654 (96 cores), 368 GB RAM\n"
        "  A100 nodes: 2x AMD 7513 (32 cores), 4x A100 SXM, 512 GB RAM\n"
        "  H100 nodes: 3x AMD 9654 (96 cores), 4x H100 SXM, 768 GB RAM\n\n"
        "Key rule: ntasks (number of MPI ranks) must equal the number of atoms in the system.\n"
        "QE submission template:\n"
        "  export OMP_NUM_THREADS=1\n"
        "  spack load quantum-espresso@7.2\n"
        "  mpirun pw.x -i input.pwi > input.pwi.pwo"
    ),
)


# ── HPC tools ─────────────────────────────────────────────────────────────


@mcp.tool()
def read_file(input_file: str) -> str:
    """
    Read the contents of a file in the working directory (e.g. a .pwi input file).

    Args:
        input_file: Filename relative to the working directory
    """
    wd = get_working_dir()
    path = os.path.join(wd, input_file)
    with open(path, "r") as f:
        return f.read()


@mcp.tool()
def add_resource_suggestion(
    qe_input_filename: str,
    partition: str,
    nnodes: int,
    ntasks: int,
    runtime: int,
    submission_script: str,
    output_filename: str,
) -> str:
    """
    Add a resource/submission suggestion for a QE job to the database.

    Call this for EACH job before calling submit_and_monitor_jobs.

    Args:
        qe_input_filename: The QE input filename (e.g. 'Li_bcc_k_0.2_ecutwfc_80.pwi')
        partition: SLURM partition (venkvis-cpu, venkvis-a100, venkvis-h100)
        nnodes: Number of nodes
        ntasks: Number of MPI tasks (must equal number of atoms in system)
        runtime: Wall time in minutes
        submission_script: Shell commands to run (without #SBATCH headers).
            Output filename must be <input_filename>.pwo.
            Example:
              export OMP_NUM_THREADS=1
              spack load quantum-espresso@7.2
              echo "Job started on `hostname` at `date`"
              mpirun pw.x -i input.pwi > input.pwi.pwo
              echo "Job Ended at `date`"
        output_filename: Expected output filename (e.g. 'input.pwi.pwo')
    """
    wd = get_working_dir()
    resource = {
        qe_input_filename: {
            "partition": "venkvis-cpu",
            "nnodes": 1,
            "ntasks": 48,
            "runtime": 2800,
            "submissionScript": submission_script,
            "outputFilename": output_filename,
        }
    }

    db_file = os.path.join(wd, "resource_suggestions.db")
    if not os.path.exists(db_file):
        initialize_database(db_file)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    for fname, res in resource.items():
        cursor.execute(
            """INSERT OR REPLACE INTO resources
               (filename, partition, nnodes, ntasks, runtime, submissionScript, outputFilename)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                fname,
                res["partition"],
                res["nnodes"],
                res["ntasks"],
                res["runtime"],
                res["submissionScript"],
                res["outputFilename"],
            ),
        )
    conn.commit()
    conn.close()
    return f"Resource suggestion for {qe_input_filename} saved."


@mcp.tool()
def submit_and_monitor_jobs(job_type: str = "DFT") -> str:
    """
    Submit all jobs in the resource_suggestions database to SLURM and wait for completion.

    Call add_resource_suggestion for every job BEFORE calling this tool. After
    submission the tool polls SLURM until every submitted job has finished,
    then reports which jobs produced valid .pwo output.

    Args:
        job_type: Type of job (e.g. 'DFT', 'LAMMPS')
    """
    wd = get_working_dir()
    db_file = os.path.join(wd, "resource_suggestions.db")

    if not os.path.exists(db_file):
        return "No resource_suggestions.db found. Use add_resource_suggestion first."

    # Load all resource suggestions
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM resources")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "No resource suggestions found. Use add_resource_suggestion first."

    resource_dict = {}
    job_list = []
    for row in rows:
        fname, partition, nnodes, ntasks, runtime, script, out_fname = row
        job_list.append(fname)
        resource_dict[fname] = {
            "partition": partition,
            "nnodes": nnodes,
            "ntasks": ntasks,
            "runtime": runtime,
            "submissionScript": script,
            "outputFilename": out_fname,
        }

    original_jobs = deepcopy(job_list)

    # Ensure pysqa prereqs exist
    if not os.path.exists(os.path.join(wd, "slurm.sh")) or not os.path.exists(
        os.path.join(wd, "queue.yaml")
    ):
        create_pysqa_prerequisites(wd)

    qa = QueueAdapter(directory=wd)
    queue_ids = []

    for input_file in job_list:
        if not os.path.exists(os.path.join(wd, input_file)):
            return f"Input file {input_file} not found."

        output_file = resource_dict[input_file]["outputFilename"]
        if os.path.exists(os.path.join(wd, output_file)):
            continue

        job_id = qa.submit_job(
            working_directory=wd,
            cores=resource_dict[input_file]["ntasks"],
            memory_max=2000,
            queue="slurm",
            job_name="agent_job",
            cores_max=resource_dict[input_file]["ntasks"],
            nodes_max=resource_dict[input_file]["nnodes"],
            partition=resource_dict[input_file]["partition"],
            run_time_max=resource_dict[input_file]["runtime"],
            command=resource_dict[input_file]["submissionScript"],
            errNoutName=input_file,
        )

        if job_id is None:
            return f"Job submission failed for {input_file}"
        queue_ids.append(job_id)
        time.sleep(1)

        # Rename the generated run script to avoid collision
        run_script = os.path.join(wd, "run_queue.sh")
        if os.path.exists(run_script):
            os.rename(run_script, os.path.join(wd, f"slurm_{input_file}.sh"))
        time.sleep(1)

    # Wait for all jobs to finish
    while True:
        running = sum(1 for qid in queue_ids if qa.get_status_of_job(process_id=qid))
        if running == 0:
            break
        time.sleep(5)

    time.sleep(10)  # wait for files to flush

    # Reset resource DB
    os.remove(db_file)
    time.sleep(1)
    initialize_database(db_file)
    time.sleep(1)

    # Check which jobs succeeded
    n_success = 0
    not_converged = []
    for job in original_jobs:
        try:
            tmp = read(os.path.join(wd, job + ".pwo"))
            tmp.get_potential_energy()
            n_success += 1
        except Exception:
            not_converged.append(job)

    if n_success == 0:
        return "All jobs failed. Investigate errors and regenerate."

    msg = f"All jobs finished. {n_success}/{len(original_jobs)} succeeded."
    if not_converged:
        msg += f" Did not converge: {not_converged}"
    return msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    get_working_dir()
    mcp.run(transport="stdio")

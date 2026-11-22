"""Simulation results browsing resources."""

import json
import os
from pathlib import Path


def list_result_files(folder: str) -> str:
    """List simulation output files in a results folder.

    Args:
        folder: Name of the simulation working folder.

    Returns:
        JSON list of files with names and sizes.
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        return json.dumps({"error": f"Folder '{folder}' not found"})

    files = []
    for f in sorted(folder_path.iterdir()):
        if f.is_file():
            files.append({
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "extension": f.suffix,
            })

    return json.dumps(files, indent=2)


def read_result_file(folder: str, filename: str) -> str:
    """Read a specific simulation result file (CSV, log, etc.).

    Args:
        folder: Name of the simulation working folder.
        filename: Name of the file to read.

    Returns:
        File contents as string, or JSON error.
    """
    filepath = Path(folder) / filename
    if not filepath.exists():
        return json.dumps({"error": f"File '{filepath}' not found"})

    try:
        content = filepath.read_text()
        # Truncate very large files
        if len(content) > 100000:
            content = content[:100000] + "\n... (truncated, file too large)"
        return content
    except Exception as e:
        return json.dumps({"error": f"Could not read file: {e}"})

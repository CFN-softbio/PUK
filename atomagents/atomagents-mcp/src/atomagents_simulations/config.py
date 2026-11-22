"""Configuration and path resolution for AtomAgents MCP server."""

import os
from pathlib import Path


def get_atomagents_root() -> Path:
    """Resolve the AtomAgents project root directory.

    Uses ATOMAGENTS_ROOT env var if set, otherwise assumes the MCP server
    lives at AtomAgents/atomagents-mcp/ and the root is one level up.
    """
    env_root = os.environ.get("ATOMAGENTS_ROOT")
    if env_root:
        return Path(env_root).resolve()
    # Default: parent of atomagents-mcp/
    return Path(__file__).resolve().parents[3]


def get_potential_repository() -> Path:
    """Path to the interatomic potential files."""
    return get_atomagents_root() / "potential_repository"


def get_templates_dir() -> Path:
    """Path to the LAMMPS template files (0_codes/)."""
    return get_atomagents_root() / "0_codes"

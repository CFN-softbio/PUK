"""LAMMPS template file resources."""

import json
from pathlib import Path

from ..config import get_templates_dir


def list_templates() -> str:
    """List available LAMMPS template files."""
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        return json.dumps({"error": f"Templates directory not found at {templates_dir}"})

    templates = []
    for f in sorted(templates_dir.iterdir()):
        if f.is_file() and not f.name.startswith('.') and not f.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            templates.append({
                "name": f.name,
                "size_bytes": f.stat().st_size,
            })

    return json.dumps(templates, indent=2)


def get_template_content(name: str) -> str:
    """Read and return the contents of a LAMMPS template file."""
    templates_dir = get_templates_dir()
    template_file = templates_dir / name

    if not template_file.exists():
        return json.dumps({"error": f"Template '{name}' not found"})

    try:
        content = template_file.read_text()
    except Exception as e:
        return json.dumps({"error": f"Could not read template: {e}"})

    return content

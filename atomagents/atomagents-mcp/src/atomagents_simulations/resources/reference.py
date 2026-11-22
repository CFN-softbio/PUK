"""Reference image resources (screw dislocation cores, etc.)."""

import base64
import json
from pathlib import Path

from ..config import get_templates_dir


def list_reference_images() -> str:
    """List available reference images."""
    templates_dir = get_templates_dir()
    if not templates_dir.exists():
        return json.dumps({"error": f"Templates directory not found at {templates_dir}"})

    images = []
    for f in sorted(templates_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg'):
            images.append({
                "name": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
            })

    return json.dumps(images, indent=2)


def get_reference_image_path(name: str) -> str:
    """Get the absolute path to a reference image.

    Args:
        name: Image filename (e.g. "screw_cores.png").

    Returns:
        JSON with the absolute path, or error.
    """
    templates_dir = get_templates_dir()
    image_path = templates_dir / name

    if not image_path.exists():
        return json.dumps({"error": f"Reference image '{name}' not found"})

    return json.dumps({"path": str(image_path.resolve())})

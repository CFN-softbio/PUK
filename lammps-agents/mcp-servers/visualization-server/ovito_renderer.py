"""OVITO-based dump file rendering and analysis."""

import os


def render_dump_frame(workspace: str, dump_file: str, output_image: str = "frame.png",
                      frame_number: str = "last",
                      image_width: int = 1600, image_height: int = 1200) -> dict:
    """Render a single frame from a LAMMPS dump file to PNG using OVITO.

    Args:
        workspace: Absolute path to workspace directory.
        dump_file: Dump file name.
        output_image: Output PNG filename.
        frame_number: Frame index (int) or "last".
        image_width: Image width in pixels.
        image_height: Image height in pixels.

    Returns:
        dict with success, filepath, frame_rendered, total_frames, atom_count.
    """
    dump_path = os.path.join(workspace, dump_file)
    output_path = os.path.join(workspace, output_image)

    if not os.path.exists(dump_path):
        return {"success": False, "error": f"Dump file not found: {dump_file}"}

    try:
        import warnings
        warnings.filterwarnings("ignore", message=".*OVITO.*PyPI")

        from ovito.io import import_file
        from ovito.modifiers import ComputePropertyModifier
        from ovito.vis import Viewport

        pipe = import_file(dump_path, multiple_frames=True)
        total_frames = pipe.num_frames

        # Resolve frame number
        if frame_number == "last":
            frame_idx = total_frames - 1
        else:
            frame_idx = int(frame_number)
            if frame_idx < 0 or frame_idx >= total_frames:
                return {"success": False,
                        "error": f"Frame {frame_idx} out of range (0-{total_frames - 1})"}

        # Check particle properties for radius handling
        frame_data = pipe.compute(frame_idx)
        props = list(frame_data.particles.keys())
        atom_count = frame_data.particles.count

        if "Radius" not in props:
            if "radius" in props:
                pipe.modifiers.append(ComputePropertyModifier(
                    output_property="Radius", expressions="radius"))
            else:
                pipe.modifiers.append(ComputePropertyModifier(
                    output_property="Radius", expressions="1.0"))

        pipe.add_to_scene()
        try:
            vp = Viewport(type=Viewport.Type.Front)
            vp.camera_dir = (0.0, -1.0, 0.0)
            vp.zoom_all()

            vp.render_image(
                filename=output_path,
                size=(image_width, image_height),
                frame=frame_idx,
                background=(1, 1, 1),
            )
        finally:
            pipe.remove_from_scene()

        if not os.path.exists(output_path):
            return {"success": False, "error": "Output image was not created"}

        file_size = os.path.getsize(output_path)
        return {
            "success": True,
            "filepath": output_path,
            "filename": output_image,
            "file_size": file_size,
            "frame_rendered": frame_idx,
            "total_frames": total_frames,
            "atom_count": atom_count,
            "image_size": f"{image_width}x{image_height}",
            "particle_properties": props,
        }

    except ImportError as e:
        return {"success": False, "error": f"OVITO not installed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Rendering error: {e}"}


def render_multiple_frames(workspace: str, dump_file: str, frame_count: int = 5,
                            output_prefix: str = "frame",
                            image_width: int = 1600, image_height: int = 1200) -> dict:
    """Render multiple frames from a LAMMPS dump file.

    Renders evenly spaced frames across the trajectory.

    Args:
        workspace: Absolute path to workspace directory.
        dump_file: Dump file name.
        frame_count: Number of frames to render.
        output_prefix: Prefix for output PNG filenames.
        image_width: Image width in pixels.
        image_height: Image height in pixels.

    Returns:
        dict with success, rendered_frames list, failed_frames list.
    """
    dump_path = os.path.join(workspace, dump_file)
    if not os.path.exists(dump_path):
        return {"success": False, "error": f"Dump file not found: {dump_file}"}

    try:
        import warnings
        warnings.filterwarnings("ignore", message=".*OVITO.*PyPI")
        from ovito.io import import_file

        pipe = import_file(dump_path, multiple_frames=True)
        total_frames = pipe.num_frames
    except ImportError as e:
        return {"success": False, "error": f"OVITO not installed: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Error reading dump: {e}"}

    actual_count = min(frame_count, total_frames)
    if total_frames <= 1:
        indices = [0]
    else:
        indices = [int(i * (total_frames - 1) / (actual_count - 1)) for i in range(actual_count)]

    rendered = []
    failed = []

    for idx in indices:
        output_name = f"{output_prefix}_{idx:04d}.png"
        result = render_dump_frame(workspace, dump_file, output_name, str(idx),
                                    image_width, image_height)
        if result.get("success"):
            rendered.append({"frame": idx, "filename": output_name, "file_size": result["file_size"]})
        else:
            failed.append({"frame": idx, "error": result.get("error", "Unknown error")})

    return {
        "success": len(rendered) > 0,
        "total_frames": total_frames,
        "rendered_frames": rendered,
        "failed_frames": failed,
        "rendered_count": len(rendered),
        "failed_count": len(failed),
    }


def create_dump_animation(workspace: str, dump_file: str,
                           output_gif: str = "animation.gif",
                           frame_count: int = 10,
                           duration: float = 0.5) -> dict:
    """Create a GIF animation from LAMMPS dump file frames.

    Args:
        workspace: Absolute path to workspace directory.
        dump_file: Dump file name.
        output_gif: Output GIF filename.
        frame_count: Number of frames to include.
        duration: Duration of each frame in seconds.

    Returns:
        dict with success, filepath, frame_count_used, file_size.
    """
    try:
        import imageio
    except ImportError:
        return {"success": False, "error": "imageio not installed: pip install imageio"}

    # Render frames using a temp prefix
    prefix = "_anim_temp"
    render_result = render_multiple_frames(workspace, dump_file, frame_count, prefix)

    if not render_result.get("success"):
        return {"success": False, "error": render_result.get("error", "Failed to render frames")}

    rendered = render_result["rendered_frames"]
    if not rendered:
        return {"success": False, "error": "No frames were rendered"}

    # Assemble GIF
    frame_paths = [os.path.join(workspace, f["filename"]) for f in rendered]
    images = [imageio.imread(p) for p in frame_paths if os.path.exists(p)]

    gif_path = os.path.join(workspace, output_gif)
    imageio.mimsave(gif_path, images, duration=duration)

    # Clean up temp frame files
    for p in frame_paths:
        if os.path.exists(p):
            os.remove(p)

    file_size = os.path.getsize(gif_path)
    return {
        "success": True,
        "filepath": gif_path,
        "filename": output_gif,
        "file_size": file_size,
        "frame_count_used": len(images),
        "duration_per_frame": duration,
    }


def analyze_dump_file(workspace: str, dump_file: str) -> dict:
    """Extract metadata from a LAMMPS dump file.

    Args:
        workspace: Absolute path to workspace directory.
        dump_file: Dump file name.

    Returns:
        dict with total_frames, atom_count, box_dimensions, particle_properties, file_size.
    """
    dump_path = os.path.join(workspace, dump_file)

    if not os.path.exists(dump_path):
        return {"success": False, "error": f"Dump file not found: {dump_file}"}

    file_size = os.path.getsize(dump_path)

    try:
        import warnings
        warnings.filterwarnings("ignore", message=".*OVITO.*PyPI")

        from ovito.io import import_file

        pipe = import_file(dump_path, multiple_frames=True)
        total_frames = pipe.num_frames
        frame0 = pipe.compute(0)

        atom_count = frame0.particles.count
        props = list(frame0.particles.keys())
        box = frame0.cell
        box_dims = [float(box.matrix[i, i]) for i in range(3)]

        return {
            "success": True,
            "dump_file": dump_file,
            "total_frames": total_frames,
            "atom_count": atom_count,
            "particle_properties": props,
            "box_dimensions": box_dims,
            "file_size": file_size,
        }

    except ImportError:
        # Fallback: parse dump file text
        return _analyze_dump_text(dump_path, dump_file, file_size)
    except Exception as e:
        return {"success": False, "error": f"Analysis error: {e}"}


def _analyze_dump_text(dump_path: str, dump_file: str, file_size: int) -> dict:
    """Fallback text-based dump analysis when OVITO is not available."""
    total_frames = 0
    atom_count = None
    properties = []

    with open(dump_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped == "ITEM: TIMESTEP":
                total_frames += 1
            elif stripped.startswith("ITEM: NUMBER OF ATOMS") and atom_count is None:
                next_line = next(f, "").strip()
                try:
                    atom_count = int(next_line)
                except ValueError:
                    pass
            elif stripped.startswith("ITEM: ATOMS") and not properties:
                parts = stripped.split()
                properties = parts[2:]  # Skip "ITEM:" and "ATOMS"

    return {
        "success": True,
        "dump_file": dump_file,
        "total_frames": total_frames,
        "atom_count": atom_count,
        "particle_properties": properties,
        "box_dimensions": None,
        "file_size": file_size,
        "note": "Text-based analysis (OVITO not available)",
    }

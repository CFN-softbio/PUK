"""Elastic constants heatmap visualization."""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


def plot_elastic_constants(workspace: str, matrix_file: str = "elastic_matrix.txt",
                           output_image: str = "elastic_constants_visualization.png") -> dict:
    """Create a 6x6 Cij heatmap from an elastic matrix file.

    Args:
        workspace: Absolute path to workspace directory.
        matrix_file: Name of the 6x6 elastic matrix text file.
        output_image: Output PNG filename.

    Returns:
        dict with success, filepath, file_size, matrix_shape.
    """
    matrix_path = os.path.join(workspace, matrix_file)
    output_path = os.path.join(workspace, output_image)

    if not os.path.exists(matrix_path):
        return {"success": False, "error": f"Matrix file not found: {matrix_file}"}

    matrix = np.loadtxt(matrix_path)

    if matrix.shape != (6, 6):
        return {"success": False, "error": f"Expected 6x6 matrix, got {matrix.shape}"}

    fig, ax = plt.subplots(figsize=(8, 8))

    labels = [f"C{i+1}" for i in range(6)]
    mask = matrix == 0

    sns.heatmap(matrix, annot=True, fmt=".1f", cmap="viridis",
                xticklabels=labels, yticklabels=labels,
                mask=mask, ax=ax, cbar_kws={"label": "GPa"})
    ax.set_title("Elastic Constants Matrix (GPa)")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    file_size = os.path.getsize(output_path)
    return {
        "success": True,
        "filepath": output_path,
        "filename": output_image,
        "file_size": file_size,
        "matrix_shape": list(matrix.shape),
    }

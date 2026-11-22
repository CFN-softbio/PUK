"""Melting point analysis visualization."""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter


def parse_lammps_thermo(filepath: str) -> dict | None:
    """Parse Step/Temp/PE columns from a LAMMPS log or output file.

    Returns dict with numpy arrays: step, temperature, pair_energy, total_energy, volume, pressure.
    Returns None if no valid data found.
    """
    with open(filepath, "r") as f:
        lines = f.readlines()

    data_lines = []
    in_data = False

    for line in lines:
        stripped = line.strip()
        if "Step" in stripped and "Temp" in stripped:
            in_data = True
            continue
        if any(k in stripped for k in ["Loop time", "Performance:", "MPI task timing"]):
            in_data = False
            continue
        if not in_data or not stripped:
            continue

        values = stripped.split()
        try:
            step = float(values[0])
            temp = float(values[1])
            pe = float(values[2]) if len(values) > 2 else 0.0
            te = float(values[3]) if len(values) > 3 else pe
            vol = float(values[4]) if len(values) > 4 else 0.0
            press = float(values[5]) if len(values) > 5 else 0.0
            data_lines.append([step, temp, pe, te, vol, press])
        except (ValueError, IndexError):
            continue

    if not data_lines:
        return None

    data = np.array(data_lines)
    return {
        "step": data[:, 0],
        "temperature": data[:, 1],
        "pair_energy": data[:, 2],
        "total_energy": data[:, 3],
        "volume": data[:, 4],
        "pressure": data[:, 5],
    }


def analyze_melting_behavior(temperature, energy, pressure):
    """Compute binned heat capacity and pressure fluctuation analysis.

    Returns dict with melting_temp_heat_capacity, binned_analysis, pressure_analysis.
    """
    results = {}

    sort_idx = np.argsort(temperature)
    temp_sorted = temperature[sort_idx]
    eng_sorted = energy[sort_idx]
    press_sorted = pressure[sort_idx]

    # Binned heat capacity
    n_bins = min(50, len(temp_sorted) // 10)
    if n_bins < 5:
        return results

    temp_bins = np.linspace(temp_sorted.min(), temp_sorted.max(), n_bins)
    energy_binned = []
    temp_binned = []

    for i in range(len(temp_bins) - 1):
        mask = (temp_sorted >= temp_bins[i]) & (temp_sorted < temp_bins[i + 1])
        if np.sum(mask) > 0:
            energy_binned.append(np.mean(eng_sorted[mask]))
            temp_binned.append(np.mean(temp_sorted[mask]))

    if len(energy_binned) < 5:
        return results

    energy_binned = np.array(energy_binned)
    temp_binned = np.array(temp_binned)

    dE = np.gradient(energy_binned)
    dT = np.gradient(temp_binned)
    heat_cap = dE / dT

    if len(heat_cap) > 7:
        heat_cap_smooth = savgol_filter(heat_cap, 7, 3)
    else:
        heat_cap_smooth = heat_cap

    peak_idx = np.argmax(heat_cap_smooth)
    results["melting_temp_heat_capacity"] = float(temp_binned[peak_idx])
    results["binned_analysis"] = {
        "temperature": temp_binned,
        "energy": energy_binned,
        "heat_capacity": heat_cap_smooth,
    }

    # Pressure fluctuation analysis
    if np.any(press_sorted != 0) and np.std(press_sorted) > 1e-6:
        temp_windows = np.linspace(temp_sorted.min(), temp_sorted.max(), 20)
        pressure_std = []
        temp_centers = []

        for i in range(len(temp_windows) - 1):
            mask = (temp_sorted >= temp_windows[i]) & (temp_sorted < temp_windows[i + 1])
            if np.sum(mask) > 5:
                pressure_std.append(np.std(press_sorted[mask]))
                temp_centers.append((temp_windows[i] + temp_windows[i + 1]) / 2)

        if len(pressure_std) > 3:
            pressure_std = np.array(pressure_std)
            temp_centers = np.array(temp_centers)
            if len(pressure_std) > 5:
                pressure_smooth = savgol_filter(pressure_std, 5, 2)
            else:
                pressure_smooth = pressure_std

            baseline = np.mean(pressure_smooth[: len(pressure_smooth) // 3])
            sig_increase = pressure_smooth > 2 * baseline
            if np.any(sig_increase):
                idx = np.where(sig_increase)[0][0]
                results["melting_temp_pressure_fluctuations"] = float(temp_centers[idx])

            results["pressure_analysis"] = {
                "temperature": temp_centers,
                "pressure_std": pressure_smooth,
            }

    return results


def _create_simple_plots(fig, temp, potential_energy, analysis):
    """2-panel layout: PE scatter + heat capacity."""
    label_fs = 14
    title_fs = 16
    tick_fs = 12

    # Plot 1: PE vs Temperature
    ax1 = fig.add_subplot(1, 2, 1)
    if len(temp) > 0 and len(potential_energy) > 0 and np.any(potential_energy != 0):
        ax1.scatter(temp, potential_energy, c="#dc2626", alpha=0.6, s=80,
                    edgecolors="#991b1b", linewidth=0.6, label="MD Trajectory")
        ax1.set_xlabel("Temperature (K)", fontsize=label_fs)
        ax1.set_ylabel("Potential Energy (eV)", fontsize=label_fs)
        ax1.set_title("Potential Energy vs Temperature", fontsize=title_fs, pad=20)
        ax1.legend(fontsize=tick_fs)
        ax1.grid(True, alpha=0.3, linestyle="--")
        ax1.tick_params(axis="both", labelsize=tick_fs)
    else:
        ax1.text(0.5, 0.5, "No potential energy data available",
                 ha="center", va="center", transform=ax1.transAxes, fontsize=label_fs)
        ax1.set_title("Potential Energy vs Temperature", fontsize=title_fs)

    # Plot 2: Heat Capacity
    ax2 = fig.add_subplot(1, 2, 2)
    if "binned_analysis" in analysis:
        binned = analysis["binned_analysis"]
        ax2.plot(binned["temperature"], binned["heat_capacity"],
                 color="#f97316", linewidth=3, label="Heat Capacity")
        if "melting_temp_heat_capacity" in analysis:
            mt = analysis["melting_temp_heat_capacity"]
            ax2.axvline(mt, color="#dc2626", linestyle="--", alpha=0.8, linewidth=2,
                        label=f"Peak: {mt:.0f} K")
        ax2.legend(fontsize=tick_fs)
        ax2.set_xlabel("Temperature (K)", fontsize=label_fs)
        ax2.set_ylabel("Heat Capacity (eV/K)", fontsize=label_fs)
        ax2.set_title("Heat Capacity Analysis", fontsize=title_fs, pad=20)
        ax2.grid(True, alpha=0.3, linestyle="--")
        ax2.tick_params(axis="both", labelsize=tick_fs)
    else:
        ax2.text(0.5, 0.5, "Insufficient data for\nheat capacity analysis",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=label_fs)
        ax2.set_title("Heat Capacity Analysis", fontsize=title_fs)


def _create_comprehensive_plots(fig, temp, potential_energy, pressure, analysis,
                                system_name, num_atoms, material):
    """4-panel layout: PE scatter, heat capacity, pressure analysis, summary."""
    # Plot 1: PE vs Temperature (top row spanning both columns)
    ax1 = fig.add_subplot(2, 2, (1, 2))
    if len(temp) > 0 and len(potential_energy) > 0 and np.any(potential_energy != 0):
        ax1.scatter(temp, potential_energy, c="#dc2626", alpha=0.6, s=80,
                    edgecolors="#991b1b", linewidth=0.6, label="MD Trajectory")
        ax1.set_xlabel("Temperature (K)", fontsize=14)
        ax1.set_ylabel("Potential Energy (eV)", fontsize=14)
        ax1.set_title("Molecular Dynamics: Potential Energy vs Temperature",
                       fontsize=16, pad=20)
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3, linestyle="--")
        ax1.tick_params(axis="both", labelsize=12)
        x_margin = (temp.max() - temp.min()) * 0.05
        y_margin = (potential_energy.max() - potential_energy.min()) * 0.05
        ax1.set_xlim(temp.min() - x_margin, temp.max() + x_margin)
        ax1.set_ylim(potential_energy.min() - y_margin, potential_energy.max() + y_margin)
    else:
        ax1.text(0.5, 0.5, "No potential energy data available",
                 ha="center", va="center", transform=ax1.transAxes, fontsize=14)
        ax1.set_title("Potential Energy vs Temperature", fontsize=16)

    # Plot 2: Heat Capacity (bottom left)
    ax2 = fig.add_subplot(2, 2, 3)
    if "binned_analysis" in analysis:
        binned = analysis["binned_analysis"]
        ax2.plot(binned["temperature"], binned["heat_capacity"],
                 color="#f97316", linewidth=3, label="Heat Capacity")
        if "melting_temp_heat_capacity" in analysis:
            mt = analysis["melting_temp_heat_capacity"]
            ax2.axvline(mt, color="#dc2626", linestyle="--", alpha=0.8, linewidth=2,
                        label=f"Peak: {mt:.0f} K")
        ax2.legend(fontsize=10)
        ax2.set_xlabel("Temperature (K)", fontsize=12)
        ax2.set_ylabel("Heat Capacity (eV/K)", fontsize=12)
        ax2.set_title("Heat Capacity Analysis", fontsize=14)
        ax2.grid(True, alpha=0.3, linestyle="--")
        ax2.tick_params(axis="both", labelsize=10)
    else:
        ax2.text(0.5, 0.5, "Insufficient data for\nheat capacity analysis",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=12)
        ax2.set_title("Heat Capacity Analysis", fontsize=14)

    # Plot 3: Summary (bottom right)
    ax3 = fig.add_subplot(2, 2, 4)
    ax3.axis("off")

    lines = ["MELTING ANALYSIS SUMMARY", "=" * 35, ""]
    if system_name:
        lines.append(f"System: {system_name}")
    if material:
        lines.append(f"Material: {material}")
    if num_atoms:
        lines.append(f"Atoms: {num_atoms}")
    if system_name or material or num_atoms:
        lines.append("")

    if len(temp) > 0:
        lines.append(f"Data points: {len(temp)}")
        lines.append(f"Temp range: {temp.min():.0f} - {temp.max():.0f} K")
        if len(potential_energy) > 0 and np.any(potential_energy != 0):
            lines.append(f"PE range: {potential_energy.min():.1f} - {potential_energy.max():.1f} eV")
        lines.append("")
        lines.append("Melting estimates:")
        found = False
        if "melting_temp_heat_capacity" in analysis:
            lines.append(f"  Heat capacity peak: {analysis['melting_temp_heat_capacity']:.0f} K")
            found = True
        if "melting_temp_pressure_fluctuations" in analysis:
            lines.append(f"  Pressure fluct.: {analysis['melting_temp_pressure_fluctuations']:.0f} K")
            found = True
        if not found:
            lines.append("  No clear melting point detected")
    else:
        lines.append("No data available")

    ax3.text(0.05, 0.95, "\n".join(lines), transform=ax3.transAxes, fontsize=10,
             verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=1", facecolor="#f8f9fa",
                       edgecolor="#dee2e6", alpha=0.9))


def plot_melting_analysis(workspace: str, log_file: str = "log.lammps",
                          output_image: str = "melting_analysis.png",
                          plot_style: str = "simple",
                          system_name: str | None = None,
                          num_atoms: int | None = None,
                          material: str | None = None) -> dict:
    """Create melting point analysis plots from a LAMMPS log/output file.

    Args:
        workspace: Absolute path to workspace directory.
        log_file: LAMMPS log or output file name.
        output_image: Output PNG filename.
        plot_style: "simple" (2-panel) or "comprehensive" (4-panel with summary).
        system_name: Optional system description for comprehensive plot.
        num_atoms: Optional atom count for comprehensive plot.
        material: Optional material name for comprehensive plot.

    Returns:
        dict with success, filepath, data_points, melting_estimates, analysis_summary.
    """
    filepath = os.path.join(workspace, log_file)
    output_path = os.path.join(workspace, output_image)

    if not os.path.exists(filepath):
        return {"success": False, "error": f"Log file not found: {log_file}"}

    data = parse_lammps_thermo(filepath)
    if data is None:
        return {"success": False, "error": "No valid thermo data found in log file"}

    temp = data["temperature"]
    potential_energy = data["pair_energy"]
    pressure = data["pressure"]

    # Filter out initial equilibration (first 300 K above minimum)
    if len(temp) > 0:
        threshold = temp.min() + 300
        mask = temp >= threshold
        if np.sum(mask) > 10:
            temp = temp[mask]
            potential_energy = potential_energy[mask]
            pressure = pressure[mask]

    analysis = {}
    if len(temp) > 10 and len(potential_energy) > 10:
        analysis = analyze_melting_behavior(temp, potential_energy, pressure)

    if plot_style == "comprehensive":
        fig = plt.figure(figsize=(16, 10), facecolor="white")
        _create_comprehensive_plots(fig, temp, potential_energy, pressure, analysis,
                                    system_name, num_atoms, material)
    else:
        fig = plt.figure(figsize=(12, 5), facecolor="white")
        _create_simple_plots(fig, temp, potential_energy, analysis)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    file_size = os.path.getsize(output_path)

    melting_estimates = {}
    if "melting_temp_heat_capacity" in analysis:
        melting_estimates["heat_capacity_peak_K"] = analysis["melting_temp_heat_capacity"]
    if "melting_temp_pressure_fluctuations" in analysis:
        melting_estimates["pressure_fluctuation_K"] = analysis["melting_temp_pressure_fluctuations"]

    return {
        "success": True,
        "filepath": output_path,
        "filename": output_image,
        "file_size": file_size,
        "data_points": len(temp),
        "temperature_range": [float(temp.min()), float(temp.max())] if len(temp) > 0 else [],
        "melting_estimates": melting_estimates,
        "plot_style": plot_style,
    }

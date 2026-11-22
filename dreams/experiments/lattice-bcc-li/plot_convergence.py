"""
Reproduce Figure 3 of the DREAMS paper (Wang et al., 2025) from the
convergence-test CSVs written by get_kspacing_ecutwfc.

Reads df_k.csv (ecutwfc sweep at fixed kspacing) and df_e.csv (kspacing sweep
at fixed ecutwfc) from the working directory, plots energy error (meV/atom)
against each swept parameter, and draws the 1 meV/atom convergence threshold
that the DFT agent applies to select production parameters.

Usage:
    python plot_convergence.py [working_dir] [output.png]

Defaults: working_dir = ./out, output = ./out/convergence_figure3.png
"""

import os
import sys

import matplotlib.pyplot as plt
import pandas as pd


THRESHOLD_MEV = 1.0  # 1 meV/atom, per the DREAMS paper


def _load(wd: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_k = pd.read_csv(os.path.join(wd, "df_k.csv"))
    df_e = pd.read_csv(os.path.join(wd, "df_e.csv"))
    # df_e is stored coarsest-first (highest kspacing first); reorder for clarity
    df_e = df_e.sort_values("kspacing", ascending=True).reset_index(drop=True)
    df_k = df_k.sort_values("ecutwfc", ascending=True).reset_index(drop=True)
    return df_k, df_e


def plot(wd: str = "out", out_path: str = None) -> str:
    if out_path is None:
        out_path = os.path.join(wd, "convergence_figure3.png")

    df_k, df_e = _load(wd)
    held_k = df_k["kspacing"].iloc[0]
    held_ecut = df_e["ecutwfc"].iloc[0]

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12, 4.8))

    # (a) ecutwfc sweep, kspacing held constant
    ax_a.plot(df_k["ecutwfc"], df_k["error"], "o-", color="tab:blue", markersize=8, linewidth=2.5)
    ax_a.axhline(THRESHOLD_MEV, color="tab:red", linestyle="--", linewidth=2, label="1 meV/atom threshold")
    ax_a.set_xlabel("Plane-wave cutoff, ecutwfc (Ry)", fontsize=16)
    ax_a.set_ylabel("Energy error (meV/atom)", fontsize=16)
    ax_a.set_title(f"(a) ecutwfc sweep  (k-spacing fixed at {held_k} Å$^{{-1}}$)", fontsize=16)
    ax_a.tick_params(axis="both", which="major", labelsize=14)
    ax_a.grid(True, alpha=0.3)
    ax_a.legend(fontsize=13, loc="best")

    # (b) kspacing sweep, ecutwfc held constant
    ax_b.plot(df_e["kspacing"], df_e["error"], "s-", color="tab:green", markersize=8, linewidth=2.5)
    ax_b.axhline(THRESHOLD_MEV, color="tab:red", linestyle="--", linewidth=2, label="1 meV/atom threshold")
    ax_b.set_xlabel("k-point spacing (Å$^{-1}$)", fontsize=16)
    ax_b.set_ylabel("Energy error (meV/atom)", fontsize=16)
    ax_b.set_title(f"(b) k-spacing sweep  (ecutwfc fixed at {held_ecut} Ry)", fontsize=16)
    ax_b.tick_params(axis="both", which="major", labelsize=14)
    ax_b.grid(True, alpha=0.3)
    ax_b.legend(fontsize=13, loc="best")

    fig.suptitle("Convergence test: BCC Li — MCP port", fontsize=18)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    return out_path


if __name__ == "__main__":
    wd = sys.argv[1] if len(sys.argv) > 1 else "out"
    out = sys.argv[2] if len(sys.argv) > 2 else None
    path = plot(wd, out)
    print(f"Saved: {path}")

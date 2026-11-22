"""VISION beamline MCP server.

A single-file MCP port of VISION's beamline cogs, for the PUKs case study. It
exposes the NSLS-II 11-BM (CMS) beamline capability as MCP tools; a frontier
coding agent supplies the planning, control flow, and routing that VISION's
cog_manager, workflows, and Classifier cog used to do.

Each tool returns the canonical Bluesky/SciAnalysis code snippet for one
operation, matching the formatting of VISION's ground-truth evaluation dataset.
The deterministic formatting lives in the tools; parameter extraction, tool
selection, and any loops/conditionals are the coding agent's job (see CLAUDE.md).

Tool groups map to the original cogs:
  * Operator  -> hardware control (measure, motors, temperature, align, ...)
  * Analyst   -> SciAnalysis protocols (circular_average, q images, linecuts)
  * Notebook  -> record_note
  * gpCAM / xiCAM -> launch hooks

Run:  python server.py     # stdio transport
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("beamline")


def _num(value) -> str:
    """Render a number the way the beamline ground-truth code does: integers and
    integer-valued floats without a trailing '.0' (sam.measure(5), not 5.0)."""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value)


# ===========================================================================
# Operator: hardware control (VISION Operator cog)
# ===========================================================================

# --- Sample initialization ---

@mcp.tool()
def initialize_sample(name: str) -> str:
    """Create the sample object for a NEW sample. Must precede any measurement or
    motor movement. Use when the user names a new sample."""
    return f"sam = Sample('{name}')"


@mcp.tool()
def set_sample_name(name: str) -> str:
    """Update the name of the already-initialized sample."""
    return f"sam.name = '{name}'"


# --- Measurement ---

@mcp.tool()
def measure(exposure_time: float) -> str:
    """Measure and SAVE the current sample for exposure_time seconds."""
    return f"sam.measure({_num(exposure_time)})"


@mcp.tool()
def snap(exposure_time: float) -> str:
    """Measure WITHOUT saving (a quick 'snap') for exposure_time seconds. Use when
    the user says not to save the data."""
    return f"sam.snap({_num(exposure_time)})"


@mcp.tool()
def measure_incident_angle(angle: float, exposure_time: float) -> str:
    """Measure at a single grazing-incidence angle (deg) for exposure_time s."""
    return f"sam.measureIncidentAngle({_num(angle)}, exposure_time={_num(exposure_time)})"


@mcp.tool()
def measure_incident_angles(angles: list[float], exposure_time: float) -> str:
    """Measure at several grazing-incidence angles (deg), each for exposure_time s."""
    angle_list = "[" + ", ".join(_num(a) for a in angles) + "]"
    return f"sam.measureIncidentAngles(angles={angle_list}, exposure_time={_num(exposure_time)})"


@mcp.tool()
def measure_time_series(exposure_time: float, num_frames: int, wait_time: float) -> str:
    """Repeated ('time series') measurement: num_frames frames of exposure_time s,
    waiting wait_time s between them. Use num_frames=9999 for 'forever'."""
    return f"sam.measureTimeSeries({_num(exposure_time)}, {_num(num_frames)}, {_num(wait_time)})"


@mcp.tool()
def series_measure(num_frames: int, exposure_time: float,
                   exposure_period: float, wait_time: float) -> str:
    """Low-overhead fast measurement series: num_frames frames of exposure_time s
    taken every exposure_period s. Prefer for 'very fast measurements with little
    overhead'."""
    return (
        "sam.series_measure("
        f"num_frames={_num(num_frames)}, exposure_time={_num(exposure_time)}, "
        f"exposure_period={_num(exposure_period)}, wait_time={_num(wait_time)})"
    )


@mcp.tool()
def measure_spots(num_spots: int, translation_amount: float,
                  axis: str, exposure_time: float) -> str:
    """Measure num_spots positions, stepping translation_amount mm along axis
    ('x' or 'y') between spots, exposure_time s per spot."""
    return (
        "sam.measureSpots("
        f"num_spots={_num(num_spots)}, translation_amount={_num(translation_amount)}, "
        f"axis='{axis}', exposure_time={_num(exposure_time)})"
    )


# --- Motors (absolute) ---

@mcp.tool()
def move_x_abs(position: float) -> str:
    """Move the sample X motor TO an absolute position (mm)."""
    return f"sam.xabs({_num(position)})"


@mcp.tool()
def move_y_abs(position: float) -> str:
    """Move the sample Y motor TO an absolute position (mm)."""
    return f"sam.yabs({_num(position)})"


@mcp.tool()
def set_incident_angle(angle: float) -> str:
    """Set the incident (theta) angle TO an absolute value (deg)."""
    return f"sam.thabs({_num(angle)})"


@mcp.tool()
def set_phi_abs(angle: float) -> str:
    """Rotate the sample phi motor TO an absolute angle (deg)."""
    return f"sam.phiabs({_num(angle)})"


# --- Motors (relative) ---

@mcp.tool()
def move_x_rel(offset: float) -> str:
    """Move the sample X motor BY a relative offset (mm)."""
    return f"sam.xr({_num(offset)})"


@mcp.tool()
def move_y_rel(offset: float) -> str:
    """Move the sample Y motor BY a relative offset (mm). 'Up' is +Y."""
    return f"sam.yr({_num(offset)})"


@mcp.tool()
def move_theta_rel(offset: float) -> str:
    """Change the incident (theta) angle BY a relative offset (deg)."""
    return f"sam.thr({_num(offset)})"


@mcp.tool()
def move_phi_rel(offset: float) -> str:
    """Rotate the sample phi motor BY a relative offset (deg)."""
    return f"sam.phir({_num(offset)})"


@mcp.tool()
def set_origin(axes: list[str]) -> str:
    """Record the current position of the given axes (e.g. ['x','y','th']) as the
    origin."""
    axis_list = "[" + ", ".join(f"'{a}'" for a in axes) + "]"
    return f"sam.setOrigin({axis_list})"


@mcp.tool()
def where_sample() -> str:
    """Report the current sample motor positions (check the sample motors)."""
    return "wsam()"


@mcp.tool()
def align() -> str:
    """Run the automated sample alignment routine."""
    return "sam.align()"


# --- Temperature (Linkam stage) ---

@mcp.tool()
def set_ramp_rate(rate: float) -> str:
    """Set the Linkam heating/cooling ramp rate (deg/min)."""
    return f"sam.setLinkamRate({_num(rate)})"


@mcp.tool()
def set_temperature(temperature: float) -> str:
    """Set the Linkam target temperature (deg C) WITHOUT changing the ramp rate."""
    return f"sam.setLinkamTemperature({_num(temperature)})"


@mcp.tool()
def get_temperature() -> str:
    """Read the current sample (Linkam) temperature."""
    return "sam.linkamTemperature()"


# For a temperature target, compose set_ramp_rate then set_temperature. When no
# ramp is specified ("heat to X" / "go to X directly"), use the fast default
# rate of 30 deg/min first -- see CLAUDE.md.


# --- Safety / misc ---

@mcp.tool()
def abort() -> str:
    """Abort the running plan and close the beam (emergency stop)."""
    return "RE.abort()\nbeam.off()"


@mcp.tool()
def select_detector(detector: str) -> str:
    """Select the active area detector (e.g. 'pilatus800', 'pilatus2M')."""
    return f"detselect({detector})"


# ===========================================================================
# Analyst: SciAnalysis protocols (VISION Analyst cog)
# ===========================================================================

@mcp.tool()
def thumbnails() -> str:
    """Show thumbnail previews of the measured data ('how does the measurement
    look')."""
    return "thumbnails"


@mcp.tool()
def circular_average() -> str:
    """1D circular average (azimuthal integration along the rings): the go-to for
    'check the 1D curve' / 'where is the peak'."""
    return "circular_average"


@mcp.tool()
def q_image() -> str:
    """Convert the detector image to reciprocal (q) space."""
    return "q_image"


@mcp.tool()
def qr_image() -> str:
    """Produce the qr reciprocal-space image."""
    return "qr_image"


@mcp.tool()
def sector_average() -> str:
    """Compute the sector average."""
    return "sector_average"


@mcp.tool()
def linecut_qr(qz: float) -> str:
    """Horizontal linecut along qr at a fixed qz."""
    return f"linecut_qr {qz}"


@mcp.tool()
def linecut_qz(qr: float) -> str:
    """Vertical linecut along qz at a fixed qr."""
    return f"linecut_qz {qr}"


@mcp.tool()
def linecut_angle(q: float) -> str:
    """Angular (azimuthal) linecut at a fixed q -- the angular intensity variation
    for a fixed q."""
    return f"linecut_angle {q}"


@mcp.tool()
def circular_average_q2I_fit() -> str:
    """Circular average followed by a q^2*I peak fit (locate the peak precisely)."""
    return "circular_average_q2I_fit"


# ===========================================================================
# Notebook / gpCAM / xiCAM (VISION note-taker + existing-tool hooks)
# ===========================================================================

@mcp.tool()
def record_note(text: str) -> str:
    """Record a free-form observation or log entry (logging, writing, general
    observations). NOT for hardware control or data analysis."""
    return f"NOTE RECORDED: {text}"


@mcp.tool()
def start_gpcam() -> str:
    """Launch gpCAM (a.k.a. Tsuchinoko) for an autonomous experiment. Use ONLY
    when the user explicitly asks for gpCAM or Tsuchinoko."""
    return "gpcam"


@mcp.tool()
def launch_xicam() -> str:
    """Launch xiCAM for interactive data visualization. Use ONLY when the user
    explicitly asks for xiCAM (or xi-cam)."""
    return "xicam"


if __name__ == "__main__":
    mcp.run()

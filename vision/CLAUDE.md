# VISION beamline operation — workflow knowledge

This project exposes the NSLS-II 11-BM (CMS) beamline as MCP servers. When a user
gives a natural-language beamline instruction, translate it into executable
Bluesky/SciAnalysis Python by **selecting the right MCP tools and supplying the
parameters**. The tools return the canonical code snippet for each operation;
you compose them into the final program.

This file is the portable "workflow knowledge" that in the original VISION system
lived inside the Operator/Analyst cog system prompts. It is not orchestration —
it is domain convention.

## Routing (what the Classifier cog used to do)

Pick the capability from the user's intent — no separate classifier step:

- **beamline-operator** — any hardware control (measure, move motors, set
  temperature, align, initialize sample).
- **beamline-analysis** — data-analysis requests on the measured 2D scattering
  data (circular average, q images, linecuts, peak fitting).
- **beamline-notebook** — logging, writing, or recording an observation.
- **gpcam** — only when the user explicitly says gpCAM or Tsuchinoko.
- **xicam** — only when the user explicitly says xiCAM.

## Operator code conventions

The generated code must match these conventions (they mirror the beamline's
`profile_collection` usage and VISION's ground-truth dataset):

- **Sample object.** Measurements and moves act on `sam`. Only emit
  `sam = Sample('name')` when a *new* sample is named; otherwise assume `sam`
  already exists.
- **Motors.** Absolute vs relative matters: "move x *to* 1.5" → `sam.xabs(1.5)`;
  "move x *by* 1.5" → `sam.xr(1.5)`. "Up" is +Y (`sam.yr`). "Incident angle"
  is the theta motor (`thabs`/`thr`).
- **Numbers.** Render integer-valued numbers without a decimal point:
  `sam.measure(5)`, not `sam.measure(5.0)`.
- **Temperature.** Compose `set_ramp_rate` then `set_temperature`. A target with
  an explicit ramp → `sam.setLinkamRate(rate)` then
  `sam.setLinkamTemperature(target)`. A target with *no* ramp ("heat to X",
  "go to X directly") → use the fast default ramp: `sam.setLinkamRate(30)` then
  `sam.setLinkamTemperature(X)`.
- **Multiple simple actions.** Emit one statement per line (e.g.
  `sam.xr(-0.5)` then `sam.align()`); a single line with `;` is also acceptable.

## Control flow (you author this natively)

The MCP tools cover single beamline operations. Loops, timing, and conditionals
are ordinary Python that you write around the tool outputs, using `numpy` and
`time`:

- **Fixed-duration repeat.** "Measure 1s every 10s for 1 min":
  ```python
  for ii in np.arange(6):
      sam.measure(1)
      time.sleep(9)
  ```
- **Spatial scan.** "Measure 1s, scan x from 0 to 1mm, step 0.2":
  ```python
  for xpos in np.arange(0, 1+0.2, 0.2):
      sam.xabs(xpos)
      sam.measure(1)
  ```
  Note the `stop + step` upper bound so the endpoint is included.
- **Condition-terminated loop.** "Measure 5s every minute until 100 deg":
  ```python
  while sam.linkamTemperature() < 100 - 0.1:
      t0 = time.time()
      sam.measure(5)
      elapsed = time.time() - t0
      if elapsed < 60:
          time.sleep(60 - elapsed)
  ```

## Analysis conventions

Analysis tools return a one-line SciAnalysis protocol name (optionally with a
parameter), e.g. `circular_average`, `qr_image`, `linecut_qr 0.1`. Return the
protocol string; parameter extraction (qz, qr, q) is your job.

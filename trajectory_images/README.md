# trajectory_images/

Six figures, one per trajectory shape, rendered by `plot_trajectory_shapes.py`.

| file | shape | provenance |
| --- | --- | --- |
| `01_line.png` | Line | **real** - `trajectories/line/line_fixed_orientation.npz` |
| `02_circle.png` | Circle | **real** - `trajectories/circle/circle_fixed_orientation.npz` |
| `03_figure_eight.png` | Figure-eight | **real** - `trajectories/figure8/figure8_fixed_orientation.npz` |
| `04_helix.png` | Helix | **real** - `trajectories/helix/helix_fixed_orientation.npz` |
| `05_free_form.png` | Free-form | **illustrative** - no dataset file exists |
| `06_challenge.png` | Challenge | **illustrative** - no dataset file exists |

## Provenance - read this before using the figures

`configs/trajectory_config.json:trajectory_types` defines exactly four shapes:
`line`, `circle`, `figure8`, `helix`. Figures 1-4 plot the `target_position` array of the
corresponding generated `.npz` file directly - no resampling, no smoothing, no synthetic data.
Both orientation variants share the same position path, so the fixed-orientation file is used.

**There is no `free-form` or `challenge` trajectory in this repository** - not in the configs,
the manifest, the generators, or `trajectories/`. Figures 5 and 6 are therefore drawn as
*illustrations of those two categories*, not as dataset contents, and both carry an explicit
`ILLUSTRATIVE` footer in the rendered image. They are constructed to be consistent with the
repo's own conventions rather than invented freely:

- the same anchor position `p0` and the same orthonormal path frame `(u, v, w)` as all 8
  generated trajectories (recovered numerically from the real `.npz` files - the recovered frame
  reproduces the stored circle and helix paths to a max error of 2.6e-6 m);
- `s = 0` maps to the anchor pose, as every generator guarantees;
- the same quintic time scaling `s(tau) = 10*tau^3 - 15*tau^4 + 6*tau^5` over 400 samples / 10.0 s;
- extents in the same 0.05-0.10 m band as the real shapes.

What they are *not*: they were **not** passed through the generation-time sequential-DLS
reachability check, so they carry no reachability guarantee. Do not cite them as benchmark
trajectories, and do not feed them to an evaluation pipeline.

- **Free-form** - a Catmull-Rom spline through 8 user-supplied waypoints with deliberately
  irregular curvature, i.e. what the `trajectories/custom/` CSV schema is for (the shipped
  `custom_trajectory_template.csv` itself has only 5 collinear waypoints, too sparse to draw
  as a shape).
- **Challenge** - a 5-petal rose `r(theta) = A*cos(5*theta)`, `theta = pi*s`, plus an
  out-of-plane term `H*sin(3*pi*s)*w`. The petals meet at a cusp, so the path reverses
  direction five times: a deliberate stress case for a tracking controller.

## Figure conventions (identical across all six)

- 3D view with a 0.115 m cube on every axis, so the shapes are directly comparable in size.
- Path colour = elapsed time, single-hue blue ramp (light = 0 s -> dark = 10 s). Because the
  time scaling is quintic, the ends are slow and the middle is fast; the colour is *time*, not
  arc length.
- Green circle = start (`s = 0`, the anchor). Orange square = end (`s = 1`). On a closed path
  the two coincide and a single marker is drawn, labelled `start = end`.
- Grey curve on the floor plane = the path projected downward; a depth cue only.
- Camera: figures 1, 2, 3 and 6 look nearly along the path-plane normal `w` so planar shapes
  read true; the helix uses a camera perpendicular to `w` so its pitch is visible; free-form
  uses an intermediate tilt. Shape geometry is identical regardless of camera.

## Regenerating

Needs only `numpy` and `matplotlib` (no MuJoCo, no `kinematics/` imports - the figures read
the committed `.npz` files):

```
python trajectory_images/plot_trajectory_shapes.py
```

The script writes all six PNGs at 200 dpi and is deterministic: no RNG is used anywhere, and
figures 5 and 6 are defined by hard-coded waypoints/coefficients, so repeated runs are
byte-stable for a given matplotlib version.

Note: `.venv/` in this repo was created on another machine (`pyvenv.cfg` points at
`C:\Users\user\...`), so `.venv\Scripts\python.exe` does not launch here; the figures above were
rendered with a system Python 3.11 (numpy 1.26.4, matplotlib 3.11.1).

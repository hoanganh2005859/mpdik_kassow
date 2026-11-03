"""Render 6 representative trajectory-shape figures for mpdik_kassow.

line / circle / figure8 / helix  -> plotted from the REAL generated .npz files.
free-form / challenge           -> illustrative shapes, built in the SAME anchor
                                   frame (p0, u, v, w) and the same quintic time
                                   scaling as the generators; NOT dataset files.
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import MaxNLocator
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from mpl_toolkits.mplot3d import proj3d

REPO = r"D:/data/nckh/mpdik_kassow"
OUT = REPO + "/trajectory_images"

# ---------------------------------------------------------------- design tokens
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8882"
GRID = "#e4e3df"
SHADOW = "#d8d7d2"
# sequential blue ramp (palette.md steps 250 -> 700), ordinal-safe on light surface
RAMP = ["#86b6ef", "#5598e7", "#2a78d6", "#256abf", "#184f95", "#0d366b"]
CMAP = LinearSegmentedColormap.from_list("seq_blue", RAMP)
START_C = "#1baf7a"
END_C = "#eb6834"

CUBE = 0.115  # m, identical axis span in every figure -> shapes stay comparable
# camera 17 deg off the path-plane normal w: shapes read true, depth is kept
VIEW_PLANE = (28.6, 103.7)    # 17 deg off the plane normal w -> planar shapes read true
VIEW_SIDE = (37.5, -42.4)     # camera perpendicular to w -> the helix pitch is visible
VIEW_TILT = (19.7, 108.5)     # 30 deg off w -> out-of-plane excursions read clearly


# ------------------------------------------------------- anchor frame (u, v, w)
def load(name):
    return np.load("{0}/trajectories/{1}/{1}_fixed_orientation.npz".format(REPO, name),
                   allow_pickle=False)


_line, _circ = load("line"), load("circle")
P0 = _line["target_position"][0].copy()
U = (_line["target_position"][-1] - P0) / 0.12
U /= np.linalg.norm(U)
_cc = np.array([0.6044920468, 0.0636909382, 0.4284425429])
_pq = np.array([np.interp(0.25, _circ["path_parameter_s"], _circ["target_position"][:, k])
                for k in range(3)])
V = (_pq - _cc) / 0.045
V = V - (U @ V) * U
V /= np.linalg.norm(V)
W = np.cross(U, V)


def frame_pts(a, b, c):
    """local (a, b, c) coords in the anchor frame -> world XYZ."""
    return P0 + np.outer(a, U) + np.outer(b, V) + np.outer(c, W)


def quintic(tau):
    return 10 * tau ** 3 - 15 * tau ** 4 + 6 * tau ** 5


S = quintic(np.linspace(0.0, 1.0, 400))   # same time scaling as the generators


# -------------------------------------------------- illustrative shapes 5 and 6
def free_form():
    """Catmull-Rom spline through 7 user-supplied waypoints (custom-schema style)."""
    wp = np.array([
        [0.000, 0.000, 0.000],
        [0.018, -0.022, 0.010],
        [0.042, -0.006, 0.026],
        [0.030, 0.028, 0.008],
        [0.002, 0.016, -0.016],
        [-0.022, 0.040, 0.002],
        [-0.044, 0.014, 0.020],
        [-0.030, -0.018, -0.006],
    ])
    ext = np.vstack([wp[0] + (wp[0] - wp[1]), wp, wp[-1] + (wp[-1] - wp[-2])])
    segs = len(wp) - 1
    t = S * segs
    i = np.clip(np.floor(t).astype(int), 0, segs - 1)
    f = (t - i)[:, None]
    q0, q1, q2, q3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
    pts = 0.5 * ((2 * q1) + (-q0 + q2) * f
                 + (2 * q0 - 5 * q1 + 4 * q2 - q3) * f ** 2
                 + (-q0 + 3 * q1 - 3 * q2 + q3) * f ** 3)
    return frame_pts(*pts.T), frame_pts(*wp.T)


def challenge():
    """5-petal rose (cusps at the centre) + out-of-plane oscillation."""
    amp, hgt = 0.050, 0.014
    th = np.pi * S
    r = amp * np.cos(5 * th)
    a = r * np.cos(th) - amp          # shift so s=0 lands on the anchor
    b = r * np.sin(th)
    c = hgt * np.sin(3 * np.pi * S)
    return frame_pts(a, b, c)


# ------------------------------------------------------------------- the 6 specs
FF, FF_WP = free_form()
SPECS = [
    dict(key="01_line", name="Line", pts=load("line")["target_position"],
         eq=r"$p(s)=p_0+s\,L\,\hat{u}$",
         meta="L = 0.120 m   |   open path   |   400 waypoints / 10.0 s",
         src="real"),
    dict(key="02_circle", name="Circle", pts=load("circle")["target_position"],
         eq=r"$p(s)=c+r\cos(2\pi s)\,\hat{u}+r\sin(2\pi s)\,\hat{v}$",
         meta="r = 0.045 m   |   closed path   |   400 waypoints / 10.0 s",
         lab_start=(-0.020, -0.062),
         src="real"),
    dict(key="03_figure_eight", name="Figure-eight", pts=load("figure8")["target_position"],
         eq=r"$p(s)=c+a\sin(2\pi s)\,\hat{u}+b\sin(4\pi s)\,\hat{v}$",
         meta="a = 0.050 m, b = 0.030 m   |   closed path   |   400 waypoints / 10.0 s",
         lab_start=(-0.085, 0.055),
         src="real"),
    dict(key="04_helix", name="Helix", pts=load("helix")["target_position"],
         eq=r"$p(s)=c+r\cos(2\pi s)\,\hat{u}+r\sin(2\pi s)\,\hat{v}+h(s-\frac{1}{2})\,\hat{w}$",
         meta="r = 0.040 m, h = 0.080 m   |   open path   |   400 waypoints / 10.0 s",
         view=VIEW_SIDE, src="real"),
    dict(key="05_free_form", name="Free-form", pts=FF, waypoints=FF_WP,
         eq=r"Catmull-Rom spline through user waypoints $\{p_i\}$",
         meta="8 waypoints   |   irregular curvature   |   open path   |   custom-trajectory schema",
         view=VIEW_TILT, lab_end=(-0.018, 0.032), src="illustrative"),
    dict(key="06_challenge", name="Challenge", pts=challenge(),
         eq=r"$r(\theta)=A\cos(5\theta),\ \theta=\pi s,\ +\,H\sin(3\pi s)\,\hat{w}$",
         meta="A = 0.050 m, H = 0.014 m   |   5 curvature reversals   |   stress test",
         lab_start=(-0.020, -0.030),
         src="illustrative"),
]


# ------------------------------------------------------------------- rendering
def render(spec):
    pts = np.asarray(spec["pts"], dtype=float)
    fig = plt.figure(figsize=(7.6, 6.4), dpi=200, facecolor=SURFACE)
    ax = fig.add_subplot(111, projection="3d", facecolor=SURFACE)

    ctr = (pts.min(0) + pts.max(0)) / 2.0
    lo, hi = ctr - CUBE / 2, ctr + CUBE / 2
    floor = lo[2]

    # recessive ground projection: depth cue only
    ax.plot(pts[:, 0], pts[:, 1], np.full(len(pts), floor),
            color=SHADOW, lw=1.2, zorder=1)

    # path: 2px line, sequential blue ramp encoding elapsed time 0 -> 10 s
    seg = np.stack([pts[:-1], pts[1:]], axis=1)
    lc = Line3DCollection(seg, cmap=CMAP, linewidths=2.0, zorder=3)
    lc.set_array(np.linspace(0, 1, len(seg)))
    ax.add_collection3d(lc)

    if "waypoints" in spec:
        wp = spec["waypoints"]
        ax.scatter(wp[:, 0], wp[:, 1], wp[:, 2], s=28, facecolor="none",
                   edgecolor=RAMP[4], linewidths=1.2, depthshade=False, zorder=4)

    closed = np.linalg.norm(pts[0] - pts[-1]) < 1e-6
    ax.scatter(*pts[0], s=95, color=START_C, edgecolor=SURFACE, linewidths=1.6,
               depthshade=False, zorder=6)
    if not closed:
        ax.scatter(*pts[-1], s=95, marker="s", color=END_C, edgecolor=SURFACE,
                   linewidths=1.6, depthshade=False, zorder=6)

    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=spec.get("view", VIEW_PLANE)[0],
                 azim=spec.get("view", VIEW_PLANE)[1])
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((0, 0, 0, 0))
        axis._axinfo["grid"].update(color=GRID, linewidth=0.6)
        axis.line.set_color(GRID)
    ax.set_xlabel("x  [m]", color=INK_MUTED, fontsize=8.5, labelpad=2)
    ax.set_ylabel("y  [m]", color=INK_MUTED, fontsize=8.5, labelpad=2)
    ax.set_zlabel("z  [m]", color=INK_MUTED, fontsize=8.5, labelpad=2)
    ax.tick_params(colors=INK_MUTED, labelsize=7.5, pad=0)
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_major_locator(MaxNLocator(4))

    inv = ax.transAxes.inverted()

    def label(point, text, color, off):
        dx, dy = off
        x2, y2, _ = proj3d.proj_transform(point[0], point[1], point[2], ax.get_proj())
        fx, fy = inv.transform(ax.transData.transform((x2, y2)))
        ax.text2D(fx + dx, fy + dy, text, transform=ax.transAxes, color=color,
                  fontsize=8.8, zorder=8, va="center",
                  ha="right" if dx < 0 else "left")

    if closed:
        label(pts[0], "start = end   s = 0 = 1   (anchor)", INK_2,
              spec.get("lab_start", (-0.020, 0.028)))
    else:
        label(pts[0], "start   s = 0   (anchor)", INK_2,
              spec.get("lab_start", (0.018, 0.028)))
        label(pts[-1], "end   s = 1", END_C, spec.get("lab_end", (-0.018, -0.028)))

    cb = fig.colorbar(lc, ax=ax, shrink=0.46, aspect=22, pad=0.10, ticks=[0, 0.5, 1])
    cb.ax.set_yticklabels(["0 s", "5 s", "10 s"], color=INK_2, fontsize=8)
    cb.set_label("elapsed time (quintic time scaling)", color=INK_2, fontsize=8.5)
    cb.outline.set_edgecolor(GRID)

    fig.text(0.055, 0.955, spec["name"], color=INK, fontsize=19, va="top")
    fig.text(0.055, 0.898, spec["eq"], color=INK_2, fontsize=11, va="top")
    fig.text(0.055, 0.858, spec["meta"], color=INK_MUTED, fontsize=8.8, va="top")
    if spec["src"] == "real":
        note = ("KR810 anchor frame (u, v, w)  |  plotted from the generated "
                ".npz waypoints")
        ncol = INK_MUTED
    else:
        note = ("ILLUSTRATIVE shape - same anchor frame and time scaling, "
                "no dataset file exists for it")
        ncol = END_C
    fig.text(0.055, 0.035, note, color=ncol, fontsize=8.2)
    fig.savefig("{0}/{1}.png".format(OUT, spec["key"]), facecolor=SURFACE,
                bbox_inches="tight", pad_inches=0.22)
    plt.close(fig)
    print("wrote", spec["key"] + ".png", "  bbox(m) =",
          np.round(pts.max(0) - pts.min(0), 4), "[" + spec["src"] + "]")


for sp in SPECS:
    render(sp)

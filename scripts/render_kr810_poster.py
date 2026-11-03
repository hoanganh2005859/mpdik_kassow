"""Poster-grade technical illustration of the Kassow KR810 (a810).

Photoreal rendering loses detail once a figure is shrunk into a poster column and
printed. This script instead produces a non-photorealistic (NPR) "technical
illustration": flat brand colours in a few cel bands, with inked contour lines,
on a transparent background.

Three MuJoCo passes feed the compositor, all rendered supersampled:

    colour        shading term, divided out against the known base colour
    depth         occlusion contours + surface normals for crease lines
    segmentation  per-geom id -> exact base colour, alpha mask, part boundaries

The ink lines come from the segmentation and depth buffers rather than from the
shading, so line weight stays constant and survives downscaling to print size.

Usage:
    python scripts/render_kr810_poster.py --livery kassow --pose upright
    python scripts/render_kr810_poster.py --livery all --views hero,front
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

REPO = Path(__file__).resolve().parents[1]
MODEL_XML = REPO / "assets" / "kr810.xml"
OUT_DIR = REPO / "renders" / "poster"

KASSOW_ORANGE = "#FF6C0A"  # URDF: rgba 1.0 0.4235 0.0392

# Per-mesh base colours. "collar" paints the two orange joint cylinders.
LIVERIES = {
    # Faithful to assets/kr810.urdf: charcoal shells, orange collars, steel flange.
    "onyx": {
        "a810_Base": "#23272B",
        "a810_Link2": "#33383D",
        "a810_Link3": "#33383D",
        "a810_Link4": "#33383D",
        "a810_Link5": "#33383D",
        "a810_Link6": "#33383D",
        "a810_Link7": "#33383D",
        "a810_ToolIO": "#B9C0C7",
        "collar": "#33383D",
    },
    # Black-and-orange poster livery: orange limbs, graphite joint housings.
    "kassow": {
        "a810_Base": "#22262A",
        "a810_Link2": "#FF6C0A",
        "a810_Link3": "#2B3035",
        "a810_Link4": "#FF6C0A",
        "a810_Link5": "#2B3035",
        "a810_Link6": "#FF6C0A",
        "a810_Link7": "#2B3035",
        "a810_ToolIO": "#C2C8CE",
        "collar": "#FF6C0A",
    },
    # Mostly orange, light joints - closest to the KUKA-style reference artwork.
    "signal": {
        "a810_Base": "#2B3035",
        "a810_Link2": "#FF6C0A",
        "a810_Link3": "#FF6C0A",
        "a810_Link4": "#FF6C0A",
        "a810_Link5": "#FF6C0A",
        "a810_Link6": "#FF6C0A",
        "a810_Link7": "#FF6C0A",
        "a810_ToolIO": "#D5DADF",
        "collar": "#FF6C0A",
    },
    # Orange limbs, graphite joint housings - largest orange area.
    "inverse": {
        "a810_Base": "#22262A",
        "a810_Link2": "#2B3035",
        "a810_Link3": "#FF6C0A",
        "a810_Link4": "#2B3035",
        "a810_Link5": "#FF6C0A",
        "a810_Link6": "#2B3035",
        "a810_Link7": "#FF6C0A",
        "a810_ToolIO": "#C2C8CE",
        "collar": "#2B3035",
    },
    # One colour per mesh, to see which shell is which.
    "debug": {
        "a810_Base": "#777777",
        "a810_Link2": "#E6194B",
        "a810_Link3": "#3CB44B",
        "a810_Link4": "#4363D8",
        "a810_Link5": "#F58231",
        "a810_Link6": "#911EB4",
        "a810_Link7": "#42D4F4",
        "a810_ToolIO": "#FFE119",
        "collar": "#000000",
    },
}

POSES = {
    # Tall S-curve, the way arm vendors shoot their own hero artwork.
    "upright": np.array([0.00, 0.62, 0.55, -0.70, 0.60, 0.55, 0.00]),
    # Wide arch, reads well across the top of a poster.
    "arch": np.array([0.55, 0.78, 0.00, 1.32, 0.00, 1.00, 0.00]),
    # Straight up, for a dimension / workspace figure.
    "zero": np.zeros(7),
}

# name, azimuth, elevation, framing margin (1.0 = silhouette touches the edges)
ALL_VIEWS = {
    "hero": (132.0, -7.0, 1.10),
    "front": (180.0, -4.0, 1.08),
    "side": (92.0, -4.0, 1.08),
    "top3q": (146.0, -24.0, 1.10),
}

# Cel bands: incident-light multipliers, darkest first.
SHADE_BANDS = np.array([0.58, 0.80, 1.00, 1.14])

INK = np.array([0.08, 0.09, 0.10])  # line colour, near-black


def _hex_to_rgb(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def build_model(livery: dict) -> mujoco.MjModel:
    """Flat-lit copy of the model, one named material per mesh."""
    root = ET.parse(MODEL_XML).getroot()
    asset = root.find("asset")
    worldbody = root.find("worldbody")

    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="8192", offheight="8192")
    ET.SubElement(visual, "quality", shadowsize="4096", offsamples="8", numslices="64")
    ET.SubElement(visual, "map", znear="0.02", zfar="40")
    # Flat, even light: the cel bands come from the compositor, not from here.
    ET.SubElement(visual, "headlight", ambient="0.62 0.62 0.62",
                  diffuse="0.34 0.34 0.34", specular="0.0 0.0 0.0")
    ET.SubElement(root, "statistic", center="0 0 0.6", extent="1.6")

    # White backdrop; the real alpha comes from the segmentation pass.
    ET.SubElement(asset, "texture", type="skybox", builtin="flat",
                  rgb1="1 1 1", rgb2="1 1 1", width="64", height="64")

    for name, colour in livery.items():
        rgb = _hex_to_rgb(colour)
        ET.SubElement(asset, "material", name=f"mat_{name}",
                      rgba=f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} 1",
                      specular="0.05", shininess="0.1", reflectance="0")

    # A soft top-left key so curved shells still read as curved.
    worldbody.insert(0, ET.Element("light", name="key", pos="-1.0 -1.4 3.0",
                                   dir="0.28 0.39 -0.88", directional="true",
                                   diffuse="0.42 0.42 0.42", specular="0 0 0",
                                   castshadow="false"))

    for geom in root.iter("geom"):
        mesh = geom.get("mesh")
        if mesh in livery:
            geom.set("material", f"mat_{mesh}")
        elif geom.get("type") == "cylinder":
            geom.set("material", "mat_collar")
        geom.attrib.pop("rgba", None)

    assets = {stl.name: stl.read_bytes()
              for stl in (MODEL_XML.parent / "meshes" / "a810").glob("*.stl")}
    return mujoco.MjModel.from_xml_string(ET.tostring(root, encoding="unicode"), assets)


def _camera_frame(azim_deg: float, elev_deg: float) -> tuple[np.ndarray, ...]:
    az, el = np.deg2rad(azim_deg), np.deg2rad(elev_deg)
    fwd = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    return fwd, right, np.cross(right, fwd)


def _fit_camera(cam, centres, radii, width, height, fovy_deg, margin, iterations=4):
    """Centre and tighten the camera on the arm's projected silhouette."""
    fwd, right, up = _camera_frame(cam.azimuth, cam.elevation)
    ty = np.tan(np.deg2rad(fovy_deg) / 2.0)
    tx = ty * width / height

    for _ in range(iterations):
        eye = np.asarray(cam.lookat) - cam.distance * fwd
        rel = centres - eye
        depth = np.clip(rel @ fwd, 1e-3, None)
        hx, hy = (rel @ right) / (depth * tx), (rel @ up) / (depth * ty)
        rx, ry = radii / (depth * tx), radii / (depth * ty)

        cx = 0.5 * ((hx + rx).max() + (hx - rx).min())
        cy = 0.5 * ((hy + ry).max() + (hy - ry).min())
        half = max((np.abs(hx - cx) + rx).max(), (np.abs(hy - cy) + ry).max())

        mid = float(depth.mean())
        cam.lookat[:] = np.asarray(cam.lookat) + mid * (cx * tx * right + cy * ty * up)
        cam.distance *= half * margin


def _normals_from_depth(depth: np.ndarray, mask: np.ndarray, fovy_deg: float):
    """View-space normals reconstructed from the linear depth buffer."""
    h, w = depth.shape
    ty = np.tan(np.deg2rad(fovy_deg) / 2.0)
    tx = ty * w / h

    # Everything stays float32: at supersampled poster sizes these buffers run
    # to hundreds of MB each, and float64 copies are what blow the memory up.
    z = np.where(mask, depth, np.nan).astype(np.float32)
    xs = ((2.0 * (np.arange(w) + 0.5) / w - 1.0) * tx).astype(np.float32)
    ys = ((1.0 - 2.0 * (np.arange(h) + 0.5) / h) * ty).astype(np.float32)
    pos = np.dstack([z * xs[None, :], z * ys[:, None], z])

    du = np.gradient(pos, axis=1)
    dv = np.gradient(pos, axis=0)
    del pos
    n = np.cross(du, dv)
    del du, dv
    norm = np.linalg.norm(n, axis=2, keepdims=True)
    np.divide(n, np.where(norm == 0, np.float32(1.0), norm), out=n)
    return np.nan_to_num(n, copy=False)


def _ink_mask(seg_id, depth, mask, fovy_deg, ss, crease_deg=32.0):
    """Silhouette, part-boundary, occlusion and crease lines, as a stroke mask."""
    def shift(a, dy, dx):
        return np.roll(np.roll(a, dy, axis=0), dx, axis=1)

    nbrs = [(0, 1), (1, 0), (1, 1), (1, -1)]

    # Outer silhouette: thicker stroke, like an inked contour.
    silhouette = mask & ~ndimage.binary_erosion(mask, iterations=max(1, ss))

    # Boundaries between different geoms, and self-occlusion steps in depth.
    inner = np.zeros_like(mask)
    both = mask.copy()
    for dy, dx in nbrs:
        other = shift(mask, dy, dx)
        pair = mask & other
        inner |= pair & (seg_id != shift(seg_id, dy, dx))
        step = np.abs(depth - shift(depth, dy, dx))
        inner |= pair & (step > 0.012 * np.where(depth > 0, depth, 1.0))
    inner &= both

    # Creases: sharp bends in the reconstructed surface.
    n = _normals_from_depth(depth, mask, fovy_deg)
    cos_lim = np.cos(np.deg2rad(crease_deg))
    crease = np.zeros_like(mask)
    for dy, dx in nbrs[:2]:
        dot = np.sum(n * shift(n, dy, dx), axis=2)
        crease |= mask & shift(mask, dy, dx) & (dot < cos_lim)
    del n
    crease = ndimage.binary_opening(crease, np.ones((2, 2)))

    thick = ndimage.binary_dilation(silhouette, iterations=ss)
    thin = ndimage.binary_dilation(inner | crease, iterations=max(1, ss - 1))
    return (thick | (thin & mask)).astype(np.float32)


def _cel_shade(colour, seg_id, mask, base_lut, ss):
    """Replace smooth shading with a few bands of the exact brand colour."""
    base = base_lut[np.clip(seg_id, 0, len(base_lut) - 1)]
    luma = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    lit = colour @ luma
    flat = np.clip(base @ luma, 1e-3, None)

    shade = np.clip(lit / flat, 0.0, 1.4)
    # Smooth first: STL facets otherwise shatter each band into speckle. The
    # weights keep the background from bleeding across the silhouette.
    w = mask.astype(np.float32)
    sigma = 2.6 * ss
    shade = (ndimage.gaussian_filter(shade * w, sigma) /
             np.maximum(ndimage.gaussian_filter(w, sigma), 1e-6))

    band = SHADE_BANDS[np.clip(np.digitize(shade, [0.70, 0.92, 1.06]), 0,
                               len(SHADE_BANDS) - 1)]
    out = np.clip(base * band[..., None], 0.0, 1.0)
    return np.where(mask[..., None], out, 1.0)


def _project(points, cam, width, height, fovy_deg) -> np.ndarray:
    """World points -> pixel coordinates of the same free camera."""
    fwd, right, up = _camera_frame(cam.azimuth, cam.elevation)
    eye = np.asarray(cam.lookat) - cam.distance * fwd
    rel = np.atleast_2d(points) - eye
    z = np.clip(rel @ fwd, 1e-6, None)

    ty = np.tan(np.deg2rad(fovy_deg) / 2.0)
    tx = ty * width / height
    ndc_x = (rel @ right) / (z * tx)
    ndc_y = (rel @ up) / (z * ty)
    return np.column_stack([(ndc_x + 1.0) * 0.5 * width,
                            (1.0 - ndc_y) * 0.5 * height])


def _driven_link_anchors(model, joint_ids, seg_id, mask, ss, fallback,
                         min_px=40):
    """Anchor each label on the shell that joint actually drives.

    Two anchors are wrong for a reader. A roll joint's URDF anchor is an
    arbitrary point on its axis, so for joints 1/3/5/7 it lands buried mid-limb
    where nothing appears to articulate. The parent/child shell seam is no
    better: it reads as belonging to the link below the joint. What a reader
    matches a number to is the casting the joint moves, so the leader points at
    the centroid of the geoms owned by the joint's child body.
    """
    # The centroid needs no supersampled precision; stride down and stay cheap.
    small_seg = seg_id[::ss, ::ss]
    small_mask = mask[::ss, ::ss]

    anchors = []
    for jid, default in zip(joint_ids, fallback):
        owned = (model.geom_bodyid == model.jnt_bodyid[jid])[small_seg]
        ys, xs = np.nonzero(owned & small_mask)
        if len(xs) < min_px:  # link hidden at this angle - keep the axis point
            anchors.append(default)
            continue
        cx, cy = xs.mean(), ys.mean()
        # A bent or partly occluded link can leave its centroid off the shell;
        # snap to the nearest pixel that really belongs to it.
        nearest = np.argmin((xs - cx) ** 2 + (ys - cy) ** 2)
        anchors.append(np.array([xs[nearest], ys[nearest]], float) * ss)
    return np.array(anchors)


def _load_font(size: int):
    for name in ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _place_labels(pts, mask, width, height, radius):
    """Horizontal callouts, alternating sides down the arm.

    The arm is a tall, narrow silhouette, so pushing labels away from the
    centroid piles them up at the top and bottom. Walking sideways instead
    keeps every leader short, horizontal and clear of the body.
    """
    clear = ndimage.distance_transform_edt(~mask)
    gap = radius * 1.45
    step = max(2.0, radius * 0.2)

    # Send each label out the side its own anchor already sits on. Alternating
    # by height instead crosses two leaders whenever neighbouring joints share
    # a height but sit on opposite sides of the limb.
    sides = np.where(pts[:, 0] >= np.median(pts[:, 0]), 1.0, -1.0)

    labels = []
    for p, side in zip(pts, sides):
        q = p.astype(float).copy()
        yi = int(np.clip(round(q[1]), 0, height - 1))
        for _ in range(4000):
            q[0] += side * step
            xi = int(round(q[0]))
            if not 0 <= xi < width:
                q[0] -= side * step
                break
            if clear[yi, xi] >= gap:
                break
        q[0] += side * radius * 0.4
        labels.append(q)

    # Spread labels that share a side vertically; the leaders stay horizontal.
    labels = np.array(labels)
    for _ in range(150):
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                if sides[i] != sides[j]:
                    continue
                dy = labels[i][1] - labels[j][1]
                if abs(dy) < 2.4 * radius:
                    push = (2.4 * radius - abs(dy)) * 0.5
                    direction = 1.0 if dy >= 0 else -1.0
                    labels[i][1] += push * direction
                    labels[j][1] -= push * direction

    margin = radius * 1.25
    labels[:, 0] = np.clip(labels[:, 0], margin, width - margin)
    labels[:, 1] = np.clip(labels[:, 1], margin, height - margin)
    return labels


def _annotate_joints(img, model, data, cam, mask, seg_id, ss, width, height,
                     fovy_deg):
    """Number the seven revolute axes with leader lines and orange discs."""
    ids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, f"joint_{i}")
           for i in range(1, 8)]
    axis_pts = _project(data.xanchor[ids], cam, width, height, fovy_deg)
    pts = _driven_link_anchors(model, ids, seg_id, mask, ss, axis_pts)

    radius = max(8, int(0.0145 * width))
    stroke = max(1, int(0.0018 * width))
    labels = _place_labels(pts, mask, width, height, radius)

    ink = tuple(int(c * 255) for c in INK) + (255,)
    disc = tuple(int(c * 255) for c in _hex_to_rgb(KASSOW_ORANGE)) + (255,)
    font = _load_font(int(radius * 1.3))

    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for n, (p, q) in enumerate(zip(pts, labels), start=1):
        v = q - p
        length = float(np.linalg.norm(v))
        end = q - v / length * radius if length > radius else q
        draw.line([tuple(p), tuple(end)], fill=ink, width=stroke)

        dot = radius * 0.22
        draw.ellipse([p[0] - dot, p[1] - dot, p[0] + dot, p[1] + dot], fill=ink)
        draw.ellipse([q[0] - radius, q[1] - radius, q[0] + radius, q[1] + radius],
                     fill=disc, outline=ink, width=stroke)
        draw.text(tuple(q), str(n), font=font, fill=(255, 255, 255, 255),
                  anchor="mm")

    return Image.alpha_composite(img, layer)


def render_view(model, data, name, azim, elev, margin, out_w, out_h, ss,
                base_lut, out_dir: Path, tag: str, annotate: bool = False) -> Path:
    width, height = out_w * ss, out_h * ss
    centres = data.geom_xpos.copy()
    radii = model.geom_rbound.copy()
    fovy = float(model.vis.global_.fovy)

    cam = mujoco.MjvCamera()
    cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    cam.azimuth, cam.elevation = azim, elev
    cam.lookat[:] = centres.mean(axis=0)
    cam.distance = 4.0 * float(radii.max() + np.ptp(centres, axis=0).max())
    _fit_camera(cam, centres, radii, width, height, fovy, margin)

    opt = mujoco.MjvOption()
    with mujoco.Renderer(model, height, width) as r:
        r.update_scene(data, cam, opt)
        colour = r.render().astype(np.float32) / 255.0

        r.enable_depth_rendering()
        r.update_scene(data, cam, opt)
        depth = r.render().astype(np.float32)
        r.disable_depth_rendering()

        r.enable_segmentation_rendering()
        r.update_scene(data, cam, opt)
        seg = r.render()
        r.disable_segmentation_rendering()

    seg_id = seg[:, :, 0]
    mask = seg_id >= 0
    seg_id = np.where(mask, seg_id, 0)

    flat = _cel_shade(colour, seg_id, mask, base_lut, ss)
    del colour
    ink = _ink_mask(seg_id, depth, mask, fovy, ss)
    del depth, seg
    rgb = flat * (1.0 - ink[..., None]) + INK * ink[..., None]
    alpha = np.clip(mask.astype(np.float32) + ink, 0.0, 1.0)

    rgba = np.dstack([rgb, alpha])
    img = Image.fromarray((rgba * 255).round().astype(np.uint8), "RGBA")
    if annotate:
        # Drawn supersampled, so the discs and leaders downsample smooth too.
        img = _annotate_joints(img, model, data, cam, mask, seg_id, ss,
                               width, height, fovy)
    img = img.resize((out_w, out_h), Image.LANCZOS)

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_axes" if annotate else ""
    out = out_dir / f"kr810_{tag}_{name}{suffix}.png"
    img.save(out, dpi=(300, 300))

    white = Image.new("RGB", img.size, "white")
    white.paste(img, mask=img.split()[3])
    white.save(out_dir / f"kr810_{tag}_{name}{suffix}_white.png", dpi=(300, 300))
    print(f"wrote {out}")
    return out


def render(livery_name: str, pose_name: str, views, out_w, out_h, ss,
           annotate: bool = False) -> list[Path]:
    livery = LIVERIES[livery_name]
    model = build_model(livery)
    data = mujoco.MjData(model)
    data.qpos[:7] = POSES[pose_name]
    mujoco.mj_forward(model, data)

    # Base colour per geom id, so the compositor can divide the shading out.
    base_lut = np.ones((model.ngeom, 3), dtype=np.float32)
    for gid in range(model.ngeom):
        base_lut[gid] = model.geom_rgba[gid, :3]
        mat = model.geom_matid[gid]
        if mat >= 0:
            base_lut[gid] = model.mat_rgba[mat, :3]

    tag = f"{livery_name}_{pose_name}"
    return [render_view(model, data, name, *ALL_VIEWS[name], out_w, out_h, ss,
                        base_lut, OUT_DIR, tag, annotate) for name in views]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--livery", default="kassow",
                        choices=[*LIVERIES, "all"])
    parser.add_argument("--pose", default="upright", choices=[*POSES, "all"])
    parser.add_argument("--views", default="hero",
                        help="comma-separated: " + ",".join(ALL_VIEWS))
    parser.add_argument("--width", type=int, default=1800, help="output px")
    parser.add_argument("--height", type=int, default=2400, help="output px")
    parser.add_argument("--ss", type=int, default=3, help="supersampling factor")
    parser.add_argument("--annotate", action="store_true",
                        help="number the seven joint axes")
    args = parser.parse_args()

    views = [v.strip() for v in args.views.split(",") if v.strip()]
    liveries = list(LIVERIES) if args.livery == "all" else [args.livery]
    poses = list(POSES) if args.pose == "all" else [args.pose]

    for livery in liveries:
        for pose in poses:
            render(livery, pose, views, args.width, args.height, args.ss,
                   args.annotate)


if __name__ == "__main__":
    main()

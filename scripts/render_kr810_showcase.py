"""Render studio-quality images of the Kassow KR810 (a810) from assets/kr810.xml.

Builds a decorated copy of the MuJoCo model (materials, studio lighting, floor,
skybox) in memory, frames the camera on the arm's silhouette and renders several
angles offscreen.

Usage:
    python scripts/render_kr810_showcase.py --theme both --width 1920 --height 1440
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
MODEL_XML = REPO / "assets" / "kr810.xml"
OUT_DIR = REPO / "renders"

# Kassow livery: pearl-white shells, charcoal base, signature orange collars.
MESH_MATERIAL = {
    "a810_Base": "mat_base",
    "a810_Link2": "mat_shell",
    "a810_Link3": "mat_shell",
    "a810_Link4": "mat_shell",
    "a810_Link5": "mat_shell",
    "a810_Link6": "mat_shell",
    "a810_Link7": "mat_shell",
    "a810_ToolIO": "mat_flange",
}

THEMES = {
    # Dark studio: white robot against a near-black backdrop, reflective floor.
    "studio": {
        "ambient": "0.33 0.34 0.38",
        "sky": ("0.135 0.155 0.195", "0.022 0.026 0.036"),
        "floor": {
            "rgb1": "0.104 0.113 0.133",
            "rgb2": "0.096 0.104 0.124",
            "markrgb": "0.155 0.175 0.215",
            "reflectance": "0.30",
        },
        "materials": [
            # name,        rgba,                  specular, shininess, reflectance
            ("mat_shell", "0.880 0.895 0.915 1", "0.62", "0.62", "0.06"),
            ("mat_base", "0.145 0.158 0.180 1", "0.50", "0.50", "0.12"),
            ("mat_flange", "0.640 0.665 0.700 1", "0.95", "0.90", "0.30"),
            ("mat_accent", "1.000 0.423 0.039 1", "0.70", "0.60", "0.12"),
        ],
        "lights": [
            # pos,            dir,                 diffuse,            specular,          shadow
            ("-0.6 -0.9 4.0", "0.14 0.22 -0.965", "0.74 0.75 0.78", "0.45 0.45 0.46", "true"),
            ("2.4 -1.2 1.4", "-0.80 0.38 -0.46", "0.26 0.29 0.36", "0.10 0.10 0.12", "false"),
            ("1.0 2.6 1.8", "-0.32 -0.80 -0.51", "0.34 0.36 0.44", "0.45 0.46 0.52", "false"),
        ],
    },
    # Light product shot: the version that drops cleanly into a paper or slide.
    "clean": {
        "ambient": "0.52 0.53 0.56",
        "sky": ("0.955 0.962 0.975", "0.760 0.780 0.815"),
        "floor": {
            "rgb1": "0.880 0.890 0.905",
            "rgb2": "0.855 0.866 0.882",
            "markrgb": "0.700 0.715 0.740",
            "reflectance": "0.16",
        },
        "materials": [
            ("mat_shell", "0.935 0.945 0.960 1", "0.55", "0.60", "0.05"),
            ("mat_base", "0.255 0.272 0.300 1", "0.50", "0.55", "0.10"),
            ("mat_flange", "0.600 0.625 0.665 1", "0.90", "0.88", "0.22"),
            ("mat_accent", "1.000 0.423 0.039 1", "0.65", "0.60", "0.10"),
        ],
        "lights": [
            ("-0.6 -0.9 4.0", "0.14 0.22 -0.965", "0.62 0.63 0.66", "0.40 0.40 0.42", "true"),
            ("2.4 -1.2 1.4", "-0.80 0.38 -0.46", "0.28 0.29 0.33", "0.10 0.10 0.12", "false"),
            ("1.0 2.6 1.8", "-0.32 -0.80 -0.51", "0.26 0.27 0.32", "0.30 0.30 0.34", "false"),
        ],
    },
}

# Showcase pose (rad), joint_1..joint_7.
HERO_POSE = np.array([0.55, 0.78, 0.00, 1.32, 0.00, 1.00, 0.00])

# name, azimuth, elevation, framing margin (1.0 = silhouette touches the edges)
VIEWS = [
    ("hero", 132.0, -7.0, 1.14),
    ("front", 180.0, -5.0, 1.12),
    ("side", 92.0, -5.0, 1.12),
    ("top3q", 146.0, -24.0, 1.12),
]


def decorate(xml_path: Path, theme: dict) -> str:
    """Return the model XML with studio materials, lights, floor and skybox."""
    root = ET.parse(xml_path).getroot()
    asset = root.find("asset")
    worldbody = root.find("worldbody")

    # --- global render quality -------------------------------------------------
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="4096", offheight="4096")
    ET.SubElement(visual, "quality", shadowsize="8192", offsamples="8", numslices="56")
    ET.SubElement(visual, "map", znear="0.02", zfar="40", shadowclip="3.0",
                  shadowscale="0.8")
    ET.SubElement(visual, "headlight", ambient=theme["ambient"],
                  diffuse="0.22 0.22 0.24", specular="0.10 0.10 0.10")
    ET.SubElement(root, "statistic", center="0 0 0.6", extent="1.6")

    # --- textures & materials --------------------------------------------------
    sky1, sky2 = theme["sky"]
    ET.SubElement(asset, "texture", type="skybox", builtin="gradient",
                  rgb1=sky1, rgb2=sky2, width="512", height="512")

    floor = theme["floor"]
    ET.SubElement(asset, "texture", name="tex_floor", type="2d", builtin="checker",
                  rgb1=floor["rgb1"], rgb2=floor["rgb2"], mark="edge",
                  markrgb=floor["markrgb"], width="1024", height="1024")
    ET.SubElement(asset, "material", name="mat_floor", texture="tex_floor",
                  texrepeat="3 3", texuniform="true", specular="0.30",
                  shininess="0.45", reflectance=floor["reflectance"])

    for name, rgba, spec, shin, refl in theme["materials"]:
        ET.SubElement(asset, "material", name=name, rgba=rgba, specular=spec,
                      shininess=shin, reflectance=refl)

    # --- floor + lights --------------------------------------------------------
    worldbody.insert(0, ET.Element("geom", name="floor", type="plane", size="6 6 0.05",
                                   pos="0 0 0", material="mat_floor", condim="3"))
    for i, (pos, direction, diffuse, specular, shadow) in enumerate(theme["lights"]):
        worldbody.insert(1 + i,
                         ET.Element("light", name=f"key{i}", pos=pos, dir=direction,
                                    directional="true", diffuse=diffuse,
                                    specular=specular, castshadow=shadow))

    # --- swap flat rgba for materials -----------------------------------------
    for geom in root.iter("geom"):
        if geom.get("name") == "floor":
            continue
        mesh = geom.get("mesh")
        if mesh in MESH_MATERIAL:
            geom.set("material", MESH_MATERIAL[mesh])
        elif geom.get("type") == "cylinder":  # the orange joint collars
            geom.set("material", "mat_accent")
        geom.attrib.pop("rgba", None)

    return ET.tostring(root, encoding="unicode")


def _assets_from(mesh_root: Path) -> dict[str, bytes]:
    """Load the STL files so the model can be built from a string."""
    return {stl.name: stl.read_bytes()
            for stl in (mesh_root / "meshes" / "a810").glob("*.stl")}


def _arm_spheres(model, data) -> tuple[np.ndarray, np.ndarray]:
    """Bounding spheres of the arm geoms (the floor is excluded)."""
    floor = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
    ids = [g for g in range(model.ngeom) if g != floor]
    return data.geom_xpos[ids].copy(), model.geom_rbound[ids].copy()


def _camera_frame(azim_deg: float, elev_deg: float) -> tuple[np.ndarray, ...]:
    """Forward / right / up unit vectors of a MuJoCo free camera."""
    az, el = np.deg2rad(azim_deg), np.deg2rad(elev_deg)
    fwd = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    return fwd, right, np.cross(right, fwd)


def _fit_camera(cam, centres, radii, width: int, height: int, fovy_deg: float,
                margin: float, iterations: int = 4) -> None:
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

        # Re-aim at the silhouette centre, then zoom so it fills `1 / margin`.
        mid_depth = float(depth.mean())
        cam.lookat[:] = np.asarray(cam.lookat) + mid_depth * (cx * tx * right +
                                                              cy * ty * up)
        cam.distance *= half * margin


def render(theme_name: str, width: int, height: int,
           pose: np.ndarray = HERO_POSE) -> list[Path]:
    theme = THEMES[theme_name]
    model = mujoco.MjModel.from_xml_string(decorate(MODEL_XML, theme),
                                           _assets_from(MODEL_XML.parent))
    data = mujoco.MjData(model)
    data.qpos[:7] = pose
    mujoco.mj_forward(model, data)

    centres, radii = _arm_spheres(model, data)
    start_lookat = centres.mean(axis=0)
    start_distance = 4.0 * float(radii.max() + np.ptp(centres, axis=0).max())
    fovy_deg = float(model.vis.global_.fovy)

    scene_opt = mujoco.MjvOption()
    OUT_DIR.mkdir(exist_ok=True)
    written: list[Path] = []

    with mujoco.Renderer(model, height, width) as renderer:
        for name, azim, elev, margin in VIEWS:
            cam = mujoco.MjvCamera()
            cam.type = mujoco.mjtCamera.mjCAMERA_FREE
            cam.azimuth, cam.elevation = azim, elev
            cam.distance = start_distance
            cam.lookat[:] = start_lookat
            _fit_camera(cam, centres, radii, width, height, fovy_deg, margin)

            renderer.update_scene(data, cam, scene_opt)
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = True
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = True

            out = OUT_DIR / f"kr810_{theme_name}_{name}.png"
            Image.fromarray(renderer.render()).save(out)
            written.append(out)
            print(f"wrote {out}")

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=[*THEMES, "both"], default="both")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1440)
    args = parser.parse_args()

    themes = list(THEMES) if args.theme == "both" else [args.theme]
    for name in themes:
        render(name, args.width, args.height)


if __name__ == "__main__":
    main()

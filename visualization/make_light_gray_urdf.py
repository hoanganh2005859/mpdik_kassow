"""Generate a light gray/white visualization variant of the KR810 URDF.

Reads ``assets/kr810.urdf`` (never modified) and writes
``assets/kr810_swift_light_gray.urdf`` next to it, with all body-mesh
materials remapped to light gray / near-white tones so the robot renders
closer to a clean studio-style reference image in Swift. The orange joint
accent rings are left untouched. Mesh ``<mesh filename="./meshes/...">``
references are relative, so the generated file works unchanged as long as
it stays in the same directory as the original ``kr810.urdf``.

Usage (from repo root, any Python with stdlib only)::

    python visualization/make_light_gray_urdf.py
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "assets" / "kr810.urdf"
DEFAULT_OUTPUT = REPO_ROOT / "assets" / "kr810_swift_light_gray.urdf"

# Original tone -> light-visualization tone. Buckets are chosen by the
# average of the original RGB so the mapping degrades gracefully if mesh
# colors change slightly upstream.
_DARK_BODY = "0.82 0.83 0.86 1"
_MID_BODY = "0.90 0.91 0.93 1"
_LIGHT_BODY = "0.95 0.96 0.98 1"

# Materials that are accent/marker colors, not robot body panels, and
# should be preserved as-is.
_PRESERVE_MATERIAL_NAMES = {"orange"}


def _remap_rgba(rgba: str) -> str:
    parts = rgba.strip().split()
    r, g, b = (float(x) for x in parts[:3])
    a = parts[3] if len(parts) > 3 else "1"
    avg = (r + g + b) / 3.0

    if avg < 0.5:
        light = _DARK_BODY
    elif avg < 0.75:
        light = _MID_BODY
    else:
        light = _LIGHT_BODY

    # Preserve the original alpha channel.
    r2, g2, b2 = light.split()[:3]
    return f"{r2} {g2} {b2} {a}"


def make_light_gray_urdf(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Source URDF not found: {source}")

    tree = ET.parse(source)
    root = tree.getroot()

    for material in root.iter("material"):
        name = material.get("name") or ""
        if name in _PRESERVE_MATERIAL_NAMES:
            continue
        color = material.find("color")
        if color is None:
            continue
        rgba = color.get("rgba")
        if not rgba:
            continue
        color.set("rgba", _remap_rgba(rgba))

    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="UTF-8", xml_declaration=True)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out_path = make_light_gray_urdf(args.source, args.output)
    print(f"Wrote light gray visualization URDF: {out_path}")


if __name__ == "__main__":
    main()

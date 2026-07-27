"""Generate a Swift-safe copy of the KR810 URDF with the SAME colors as
``assets/kr810.urdf`` -- no estimated/invented palette.

Reads ``assets/kr810.urdf`` (never modified) and writes
``assets/kr810_swift_visual.urdf`` next to it. Geometry, mesh filenames,
scale, origin, joint, inertial, collision and limit data are copied
through byte-for-byte unchanged via ElementTree. The only normalization
applied is materials: some `<visual>` elements reference a top-level
named material by name only (``<material name="orange"/>``, no inline
`<color>`), which not every URDF consumer resolves. Those are inlined
with the *exact* rgba already declared for that name at the top of
``assets/kr810.urdf``, so Swift renders it deterministically. No color
value is changed, brightened, or invented.

Confirmed source colors (assets/kr810.urdf, verified by parsing, not
guessed):

- base, link1, link2, link3, link4, link5, link6 (inline, already has a
  `<color>` child): ``0.2 0.2 0.2 1``
- end_effector / a810_ToolIO.stl (inline, already has a `<color>` child):
  ``0.8 0.8 0.8 1``
- linkJ2, linkJ4: ``<material name="orange"/>`` with no inline color ->
  resolved here from the top-level declaration:
  ``1.0 0.4235294117647059 0.0392156862745098 1.0``
- Top-level declared materials (left untouched):
  gray ``0.5 0.5 0.5 1.0``, dark_gray ``0.3 0.3 0.3 1.0``,
  light_gray ``0.7 0.7 0.7 1.0``, black ``0.1 0.1 0.1 1.0``,
  orange ``1.0 0.4235294117647059 0.0392156862745098 1.0``

Usage (from repo root)::

    python visualization/make_kassow_visual_urdf.py
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "assets" / "kr810.urdf"
DEFAULT_OUTPUT = REPO_ROOT / "assets" / "kr810_swift_visual.urdf"


def make_visual_urdf(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> Path:
    if not source.exists():
        raise FileNotFoundError(f"Source URDF not found: {source}")

    tree = ET.parse(source)
    root = tree.getroot()

    # Top-level named materials declared directly under <robot>, e.g.
    # <material name="orange"><color rgba="..."/></material>.
    named_rgba: dict[str, str] = {}
    for material in root.findall("material"):
        name = material.get("name")
        color = material.find("color")
        if name and color is not None and color.get("rgba"):
            named_rgba[name] = color.get("rgba")

    inlined = []
    for link in root.iter("link"):
        for visual in link.findall("visual"):
            material = visual.find("material")
            if material is None:
                continue
            if material.find("color") is not None:
                # Already inline (e.g. the 0.2/0.8 body colors) -- leave
                # exactly as-is, do not touch the value.
                continue
            name = material.get("name")
            rgba = named_rgba.get(name)
            if rgba is None:
                continue
            ET.SubElement(material, "color", {"rgba": rgba})
            inlined.append((link.get("name"), name, rgba))

    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="UTF-8", xml_declaration=True)

    for link_name, mat_name, rgba in inlined:
        print(f"  inlined material '{mat_name}' -> rgba=\"{rgba}\" for link '{link_name}'")

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    out_path = make_visual_urdf(args.source, args.output)
    print(f"Wrote Swift-visual URDF (source colors, unchanged): {out_path}")


if __name__ == "__main__":
    main()

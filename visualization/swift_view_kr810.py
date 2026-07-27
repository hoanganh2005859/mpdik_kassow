"""Interactive KR810 viewer in Swift.

Loads ``assets/kr810_swift_visual.urdf`` -- a Swift-only visualization
variant regenerated fresh from ``assets/kr810.urdf`` on every run (the
original file is never modified). It keeps all geometry/origin/joint/
mesh data identical to the source URDF and only assigns a segmented,
readable color scheme per link (see
visualization/make_kassow_visual_urdf.py). Poses the robot in a readable
"ready" configuration and points the camera at a pleasant 3/4 view.
Camera orbit/zoom/pan is native browser mouse control (see
visualization/README_SWIFT_VISUAL.md).

Usage (from repo root)::

    .venv-swift\\Scripts\\python.exe visualization\\swift_view_kr810.py
    .venv-swift\\Scripts\\python.exe visualization\\swift_view_kr810.py --headless
    .venv-swift\\Scripts\\python.exe visualization\\swift_view_kr810.py --hold-seconds 20
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_kassow_visual_urdf import make_visual_urdf  # noqa: E402

# A readable "ready" pose: elbow bent, well clear of the zero/singular
# straight-up configuration, all values within assets/kr810.urdf joint
# limits (joint_2 / joint_4 are the tightest at [-1.2217, 3.1416] rad).
DEMO_Q = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

CAMERA_POSITION = [2.2, -2.2, 1.6]
CAMERA_LOOK_AT = [0.0, 0.0, 0.6]


def build_robot():
    from roboticstoolbox.robot.Robot import Robot

    urdf_path = make_visual_urdf()
    links, name, urdf_string, urdf_filepath = Robot.URDF_read(
        urdf_path.name, tld=str(urdf_path.parent)
    )
    robot = Robot(links, name=name, urdf_string=urdf_string, urdf_filepath=urdf_filepath)
    robot.q = DEMO_Q
    return robot, urdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening a browser tab (CI-style smoke check only).",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=0.0,
        help="Keep the browser tab open for N seconds then exit automatically. "
        "0 (default) holds forever until Ctrl+C.",
    )
    args = parser.parse_args()

    import swift

    robot, urdf_path = build_robot()
    print(f"Using URDF: {urdf_path}")
    print(f"Loaded '{robot.name}' with {robot.n} joints, q = {list(robot.q)}")

    env = swift.Swift()
    env.launch(realtime=True, headless=args.headless)

    env.add(robot)

    if not args.headless:
        env.set_camera_pose(CAMERA_POSITION, CAMERA_LOOK_AT)

    for _ in range(30):
        env.step(0.02)

    print("KR810 view ready.")

    if args.headless:
        env.close()
        return

    if args.hold_seconds > 0:
        print(f"Holding browser tab open for {args.hold_seconds:.0f}s ...")
        time.sleep(args.hold_seconds)
        env.close()
    else:
        print("Browser tab open. Drag to orbit, scroll to zoom, right-drag/shift-drag to pan.")
        print("Press Ctrl+C in this terminal to stop.")
        try:
            env.hold()
        except KeyboardInterrupt:
            pass
        finally:
            env.close()


if __name__ == "__main__":
    main()

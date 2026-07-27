"""Swift environment smoke test using the built-in Franka Emika Panda model.

Confirms that roboticstoolbox-python + swift-sim + numpy are correctly
installed and wired together in ``.venv-swift`` before trying the KR810
viewer. Does NOT touch anything under assets/ or the project's main
.venv.

Usage (from repo root)::

    .venv-swift\\Scripts\\python.exe visualization\\swift_smoke_test.py
    .venv-swift\\Scripts\\python.exe visualization\\swift_smoke_test.py --headless
    .venv-swift\\Scripts\\python.exe visualization\\swift_smoke_test.py --hold-seconds 5
"""

from __future__ import annotations

import argparse
import time


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening a browser tab (fast CI-style check only).",
    )
    parser.add_argument(
        "--hold-seconds",
        type=float,
        default=0.0,
        help="After the animation, keep the browser tab open for N seconds "
        "then exit automatically. 0 (default) means hold forever until "
        "Ctrl+C, and is ignored in --headless mode.",
    )
    args = parser.parse_args()

    print("[1/4] Importing numpy / roboticstoolbox / swift ...")
    import numpy as np
    import roboticstoolbox as rtb
    import swift

    print(f"      numpy {np.__version__}, roboticstoolbox {rtb.__version__}")

    print("[2/4] Launching Swift ...")
    env = swift.Swift()
    env.launch(realtime=True, headless=args.headless)
    print("      Swift launched OK" + (" (headless)" if args.headless else " (browser tab opened)"))

    print("[3/4] Loading Panda model and animating a short motion ...")
    panda = rtb.models.Panda()
    panda.q = panda.qr
    env.add(panda)

    q_start = panda.qr.copy()
    q_end = panda.qz.copy()
    steps = 60
    for i in range(steps):
        s = i / (steps - 1)
        panda.q = (1 - s) * q_start + s * q_end
        env.step(0.02)

    print("[4/4] SMOKE_TEST_OK - Swift + roboticstoolbox environment is working.")

    if args.headless:
        env.close()
        return

    if args.hold_seconds > 0:
        print(f"Holding browser tab open for {args.hold_seconds:.0f}s ...")
        time.sleep(args.hold_seconds)
        env.close()
    else:
        print("Browser tab will stay open. Press Ctrl+C in this terminal to stop.")
        try:
            env.hold()
        except KeyboardInterrupt:
            pass
        finally:
            env.close()


if __name__ == "__main__":
    main()

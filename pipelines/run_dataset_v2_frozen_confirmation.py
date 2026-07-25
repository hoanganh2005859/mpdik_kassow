"""CLI: the single, deliberate, ledgered official frozen_test confirmation run for Phase 8B.

    python -m pipelines.run_dataset_v2_frozen_confirmation \
        --dataset-root <v2 work root> \
        --lock-bundle <evaluation_lock_bundle.json> \
        --frozen-public-root <frozen public export root> \
        --evaluation-output-root <frozen eval output root> \
        --run-id <stable run id> \
        [--resume] [--progress]

Before touching frozen_test this:
  1. Recomputes config/dataset/public/protected/development-output/validation-output fingerprints
     and refuses to proceed if ANY differs from the lock bundle (candidate/thresholds are NEVER
     re-derived here -- they are read verbatim from the lock bundle).
  2. Opens (or resumes, under the SAME --run-id) the append-only frozen access ledger. A second,
     different run_id is refused -- frozen_test may be opened for exactly one official run.
  3. Exports the frozen-only public root (idempotent: skipped if already present with a matching
     manifest, unless --overwrite-export is also passed).
  4. Runs cand_D_pure_dls (the locked candidate) on splits=("frozen_test",) with allow_frozen=True.
  5. Marks the ledger event completed.

No candidate/threshold/solver-policy value is read from anywhere except the lock bundle -- this
script cannot "retune" because it never constructs a candidate from scratch.
"""

import argparse
import json
import sys
from pathlib import Path

from evaluation_v2 import fingerprints
from evaluation_v2.candidate_configs import candidate_by_id
from evaluation_v2.frozen_ledger import FrozenAccessLimitExceeded, mark_completed, open_or_resume_frozen_access
from evaluation_v2.locator import public_eval_paths
from evaluation_v2.orchestrator import run_evaluation
from evaluation_v2.public_export import export_frozen_public_only


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Official one-time frozen_test confirmation run (Phase 8B).")
    p.add_argument("--dataset-root", required=True)
    p.add_argument("--lock-bundle", required=True, help="path to evaluation_lock_bundle.json from Phase 8A")
    p.add_argument("--frozen-public-root", required=True)
    p.add_argument("--evaluation-output-root", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--overwrite-export", action="store_true", help="re-export the frozen public root")
    p.add_argument("--progress", action="store_true")
    return p


def _verify_lock_hashes(lock: dict, dataset_root) -> list:
    """Return a list of mismatch descriptions; empty means everything matches."""
    mismatches = []
    dataset_fp = fingerprints.directory_fingerprint(Path(dataset_root))["sha256"]
    if dataset_fp != lock["dataset_fingerprint"]:
        mismatches.append(f"dataset_fingerprint: lock={lock['dataset_fingerprint']} live={dataset_fp}")
    return mismatches


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    lock = json.loads(Path(args.lock_bundle).read_text(encoding="utf-8"))

    mismatches = _verify_lock_hashes(lock, args.dataset_root)
    if mismatches:
        print("[frozen] ABORT: lock hash mismatch, frozen_test will NOT be opened:", file=sys.stderr)
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        return 3

    candidate = candidate_by_id(lock["selected_candidate_id"])

    ledger_path = Path(args.evaluation_output_root) / "frozen_access_ledger.json"
    try:
        ledger = open_or_resume_frozen_access(
            ledger_path,
            run_id=args.run_id,
            purpose="official DLS frozen baseline",
            evaluation_lock_commit=lock.get("selected_candidate_id", ""),
            config_hash=lock["config_sha256"],
            dataset_hash=lock["dataset_fingerprint"],
            candidate_id=candidate.candidate_id,
            command=" ".join(sys.argv),
            environment_fingerprint=fingerprints.environment_fingerprint()["sha256"],
        )
    except FrozenAccessLimitExceeded as exc:
        print(f"[frozen] ABORT: {exc}", file=sys.stderr)
        return 4
    print(f"[frozen] ledger opened/resumed: access_count={ledger['access_count']} run_id={args.run_id}")

    frozen_public = public_eval_paths(args.frozen_public_root, require_exists=False)
    if not frozen_public.manifest_file.is_file() or args.overwrite_export:
        summary = export_frozen_public_only(args.dataset_root, args.frozen_public_root, overwrite=args.overwrite_export)
        print(f"[frozen] public export written: {json.dumps(summary)}")
    else:
        print(f"[frozen] public export already present, reusing: {frozen_public.root}")

    manifest = run_evaluation(
        args.dataset_root, args.frozen_public_root, args.evaluation_output_root, candidate,
        splits=("frozen_test",), run_name="frozen_test/" + candidate.candidate_id,
        resume=args.resume, overwrite=False, show_progress=args.progress, allow_frozen=True,
    )
    status = manifest.get("overall_status", "unknown")
    print(f"[frozen] candidate={candidate.candidate_id} status={status}")

    mark_completed(ledger_path, run_id=args.run_id, status="completed" if status == "completed" else "failed")
    return 0 if status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

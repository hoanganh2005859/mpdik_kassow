"""CLI: assemble the public Dataset v2.0.0 release + 3 ZIPs + SHA256SUMS.txt (task section 9).

Pure packaging over already-validated, already-public data: the development/validation public
root, the frozen-only public root, the three completed evaluation run directories, and the
existing protected-validation root (development/validation only -- frozen protected evidence is
deliberately never generated). Does not read the dataset root's protected arrays.

    python -m pipelines.build_dataset_v2_release \
        --v2-work-root <...> --public-devval-root <...> --public-frozen-root <...> \
        --protected-devval-root <...> \
        --dev-run-dir <...> --val-run-dir <...> --frozen-run-dir <...> \
        --lock-bundle <evaluation_lock_bundle.json> \
        --release-root <...> --zip-output-dir <...> [--overwrite]
"""

import argparse
import json
from pathlib import Path

from evaluation_v2.combine import _tier_summary
from evaluation_v2.release_builder import (
    assemble_public_release,
    write_checksum_manifest,
    write_known_limitations,
    write_release_notes,
)
from evaluation_v2.release_packaging import extract_and_validate_public_zip, write_sha256sums, zip_directory


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Assemble the public Dataset v2.0.0 release and ZIPs.")
    p.add_argument("--v2-work-root", required=True)
    p.add_argument("--public-devval-root", required=True)
    p.add_argument("--public-frozen-root", required=True)
    p.add_argument("--protected-devval-root", required=True)
    p.add_argument("--dev-run-dir", required=True)
    p.add_argument("--val-run-dir", required=True)
    p.add_argument("--frozen-run-dir", required=True)
    p.add_argument("--lock-bundle", required=True)
    p.add_argument("--release-root", required=True)
    p.add_argument("--zip-output-dir", required=True)
    p.add_argument("--overwrite", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)
    lock = json.loads(Path(args.lock_bundle).read_text(encoding="utf-8"))

    run_dirs = {
        "development": Path(args.dev_run_dir),
        "validation": Path(args.val_run_dir),
        "frozen_test": Path(args.frozen_run_dir),
    }
    final_summary = {
        "selected_candidate_id": lock["selected_candidate_id"],
        "development": _tier_summary(run_dirs["development"]),
        "validation": _tier_summary(run_dirs["validation"]),
        "frozen_test": _tier_summary(run_dirs["frozen_test"]),
        "note": "development/validation/frozen_test are separate sample pools, reported side by "
                "side and never pooled into one aggregate number.",
    }

    release_root = Path(args.release_root)
    counts = assemble_public_release(
        args.v2_work_root, args.public_devval_root, args.public_frozen_root, release_root,
        run_dirs=run_dirs, lock_bundle=lock, final_dls_summary=final_summary, overwrite=args.overwrite,
    )
    write_release_notes(release_root / "release_notes.md", counts=counts, final_summary=final_summary)
    write_known_limitations(release_root / "known_limitations.md")
    write_checksum_manifest(release_root)
    print(f"[release] public release assembled at {release_root}: {json.dumps(counts)}")

    zip_dir = Path(args.zip_output_dir)
    zip_dir.mkdir(parents=True, exist_ok=True)

    public_zip = zip_dir / "KR810_Tier0_Tier4_Dataset_v2.0.0.zip"
    zip_directory(release_root, public_zip)
    print(f"[release] wrote {public_zip}")

    # DLS baseline: non-protected evaluation outputs (manifests + tier CSV/JSON), not raw checkpoints.
    baseline_dir = zip_dir / "_dls_baseline_staging"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    for split, run_dir in run_dirs.items():
        dst = baseline_dir / split
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(run_dir, dst, ignore=shutil.ignore_patterns("checkpoint"))
    (baseline_dir / "evaluation_lock_bundle.json").write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    (baseline_dir / "final_dls_summary.json").write_text(json.dumps(final_summary, indent=2, sort_keys=True), encoding="utf-8")
    baseline_zip = zip_dir / "KR810_Tier0_Tier4_DLS_Baseline_v2.0.0.zip"
    zip_directory(baseline_dir, baseline_zip)
    shutil.rmtree(baseline_dir)
    print(f"[release] wrote {baseline_zip}")

    protected_zip = zip_dir / "KR810_Tier0_Tier4_Protected_Validation_v2.0.0.zip"
    zip_directory(
        Path(args.protected_devval_root), protected_zip,
        marker_text="INTERNAL PROTECTED VALIDATION ARCHIVE -- NOT FOR EVALUATION.\n"
                    "Contains development/validation reconstruction evidence (reference-solution "
                    "hashes) used only to prove public/protected isolation. Never fed to the "
                    "DLS evaluator. frozen_test protected evidence is deliberately not included.\n",
    )
    print(f"[release] wrote {protected_zip}")

    sha_file = zip_dir / "SHA256SUMS.txt"
    write_sha256sums([public_zip, baseline_zip, protected_zip], sha_file)
    print(f"[release] wrote {sha_file}")

    extract_dir = zip_dir / "_public_zip_extract_check"
    report = extract_and_validate_public_zip(public_zip, extract_dir)
    print(f"[release] public ZIP extract validation: {json.dumps(report)}")
    import shutil as _shutil
    _shutil.rmtree(extract_dir, ignore_errors=True)

    ok = report["checksum_pass"] and report["loader_ok"] and report["isolation_pass"]
    return 0 if ok else 5


if __name__ == "__main__":
    raise SystemExit(main())

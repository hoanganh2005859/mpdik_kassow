"""Append-only access ledger gating the single official read of ``frozen_test`` (Phase 8B).

The ledger is a JSON document with an ``access_count`` (number of *distinct* ``run_id`` values
that have ever opened frozen access) and an ``events`` list that is only ever appended to, never
rewritten in place. A resume under the SAME ``run_id`` appends a ``resumed_for_official_run``
event and does not increment ``access_count``. An attempt to open frozen access under a NEW
``run_id`` once any run_id has already been recorded raises :class:`FrozenAccessLimitExceeded` --
frozen_test may be opened for exactly one official run for the life of this ledger file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class FrozenAccessLimitExceeded(RuntimeError):
    """Raised when a NEW run_id attempts frozen access after one has already been recorded."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def read_ledger(ledger_path) -> dict:
    path = Path(ledger_path)
    if not path.is_file():
        return {"access_count": 0, "events": []}
    return json.loads(path.read_text(encoding="utf-8"))


def open_or_resume_frozen_access(
    ledger_path,
    *,
    run_id: str,
    purpose: str,
    evaluation_lock_commit: str,
    config_hash: str,
    dataset_hash: str,
    candidate_id: str,
    command: str,
    environment_fingerprint: str,
) -> dict:
    """Record (or resume) the single permitted official frozen access. Never mutates past events."""
    path = Path(ledger_path)
    ledger = read_ledger(path)
    existing_run_ids = {e["run_id"] for e in ledger["events"]}

    if existing_run_ids and run_id not in existing_run_ids:
        raise FrozenAccessLimitExceeded(
            f"frozen_test has already been opened under run_id(s) {sorted(existing_run_ids)}; "
            f"a new run_id ({run_id!r}) is not permitted (access_count must stay 1)."
        )

    is_new_run = run_id not in existing_run_ids
    event = {
        "run_id": run_id,
        "purpose": purpose,
        "evaluation_lock_commit": evaluation_lock_commit,
        "config_hash": config_hash,
        "dataset_hash": dataset_hash,
        "candidate_id": candidate_id,
        "command": command,
        "machine_environment_fingerprint": environment_fingerprint,
        "timestamp": _now_iso(),
        "status": "opened_for_official_run" if is_new_run else "resumed_for_official_run",
    }
    ledger["events"].append(event)
    ledger["access_count"] = len({e["run_id"] for e in ledger["events"]})
    _atomic_write(path, ledger)
    return ledger


def mark_completed(ledger_path, *, run_id: str, status: str = "completed") -> dict:
    path = Path(ledger_path)
    ledger = read_ledger(path)
    ledger["events"].append({"run_id": run_id, "status": status, "timestamp": _now_iso()})
    _atomic_write(path, ledger)
    return ledger

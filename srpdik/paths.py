"""Repo-relative path resolution for srpdik, mirroring utils/dataset_locator.py's pattern.

Every path here is derived from this file's own location via ``pathlib.Path`` (never a
hardcoded ``D:\\...`` or ``/...`` literal), so it resolves correctly regardless of the caller's
current working directory. This module never scans the filesystem and never defaults to a
Dataset v2 split path (development/validation/frozen_test); those are only ever reached through
an explicit, caller-supplied root (see srpdik/data/split_guard.py).
"""

from pathlib import Path

#: srpdik/paths.py -> srpdik/ -> repo root.
REPO_ROOT = Path(__file__).resolve().parent.parent
SRPDIK_PACKAGE_DIR = Path(__file__).resolve().parent


def repo_root() -> Path:
    """Absolute path to the repository root, derived from this file's location."""
    return REPO_ROOT


def srpdik_package_dir() -> Path:
    """Absolute path to the srpdik/ package directory itself."""
    return SRPDIK_PACKAGE_DIR


def resolve_repo_path(relative_path: str) -> Path:
    """Resolve a repo-relative path (e.g. 'configs/srpdik/dls_locked.json') against REPO_ROOT."""
    return REPO_ROOT / relative_path


def srpdik_config_dir() -> Path:
    """``configs/srpdik/`` under the repo root."""
    return REPO_ROOT / "configs" / "srpdik"


def srpdik_config_path(filename: str) -> Path:
    """Resolve a single config filename under ``configs/srpdik/``."""
    return srpdik_config_dir() / filename


def srpdik_tests_dir() -> Path:
    return REPO_ROOT / "tests" / "srpdik"


def srpdik_notebooks_dir() -> Path:
    return REPO_ROOT / "notebooks" / "srpdik"


def srpdik_results_dir() -> Path:
    return REPO_ROOT / "results" / "srpdik"


def srpdik_docs_dir() -> Path:
    return REPO_ROOT / "docs" / "srpdik"


def srpdik_pipelines_dir() -> Path:
    return REPO_ROOT / "pipelines"

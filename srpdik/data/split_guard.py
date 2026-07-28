"""Fail-closed dataset-split access guard.

Policy (docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md item 11, docs/srpdik/DECISIONS.md):

- ``train`` (the srpdik-internal training stream, distinct seed namespace from dataset v2):
  allowed.
- Dataset v2 ``development``: allowed.
- Dataset v2 ``validation``: allowed only when the caller passes explicit authorization.
- Dataset v2 ``frozen_test``: always denied by this guard. No frozen-evaluation CLI exists in
  Phase 1; a future phase's frozen run must use its own dedicated, ledger-gated path, not this
  guard.

This module never opens or inspects the *contents* of any split -- it only reasons about split
names and path strings. Unknown split names, ambiguous aliases, and paths containing a
frozen-test marker are all rejected (fail-closed: unknown means denied).
"""

from pathlib import Path
from typing import Optional, Union

from srpdik.constants import (
    KNOWN_SPLITS,
    SPLIT_DEVELOPMENT,
    SPLIT_FROZEN_TEST,
    SPLIT_TRAIN,
    SPLIT_VALIDATION,
)
from srpdik.exceptions import SplitAccessDenied

#: Alias -> canonical split name. Only exact, unambiguous aliases are accepted; anything not
#: listed here (including partial/fuzzy matches, e.g. bare "test" or "frozen") is rejected as
#: unknown rather than guessed at.
_SPLIT_ALIASES = {
    "train": SPLIT_TRAIN,
    "training": SPLIT_TRAIN,
    "development": SPLIT_DEVELOPMENT,
    "dev": SPLIT_DEVELOPMENT,
    "validation": SPLIT_VALIDATION,
    "val": SPLIT_VALIDATION,
    "frozen_test": SPLIT_FROZEN_TEST,
}

#: Substrings in a path that mark it as touching the frozen split, independent of the declared
#: split name (defence in depth against a mislabeled or ambiguous caller).
_FROZEN_PATH_MARKERS = ("frozen_test", "frozen-test", "eval_frozen")


def _canonicalize_split(split_name: str) -> str:
    if not isinstance(split_name, str) or not split_name.strip():
        raise SplitAccessDenied("split name must be a non-empty string")
    key = split_name.strip().lower()
    if key not in _SPLIT_ALIASES:
        raise SplitAccessDenied(
            f"unknown or ambiguous split name {split_name!r}; known aliases: "
            f"{sorted(_SPLIT_ALIASES)}"
        )
    canonical = _SPLIT_ALIASES[key]
    if canonical not in KNOWN_SPLITS:
        raise SplitAccessDenied(
            f"split {split_name!r} resolved to an unrecognized canonical split {canonical!r}"
        )
    return canonical


def _assert_path_not_frozen(path: Optional[Union[str, Path]]) -> None:
    if path is None:
        return
    text = str(path).lower()
    for marker in _FROZEN_PATH_MARKERS:
        if marker in text:
            raise SplitAccessDenied(
                f"path {path!r} contains a frozen-test marker ({marker!r}); denied regardless "
                "of the declared split name"
            )


def assert_split_access_allowed(
    split_name: str,
    *,
    path: Optional[Union[str, Path]] = None,
    validation_authorized: bool = False,
) -> str:
    """Fail-closed split access check. Returns the canonical split name on success.

    Raises SplitAccessDenied if: ``split_name`` is unknown/ambiguous; ``path`` (if given)
    contains a frozen-test marker; the canonical split is ``frozen_test`` (always denied in the
    current pipeline); or the canonical split is ``validation`` and ``validation_authorized`` is
    not True.

    Never opens or reads the contents of any split -- it only reasons about the split name and
    an optional path string.
    """
    canonical = _canonicalize_split(split_name)
    _assert_path_not_frozen(path)

    if canonical == SPLIT_FROZEN_TEST:
        raise SplitAccessDenied(
            "frozen_test split access is always denied by this guard in the current pipeline; "
            "a frozen evaluation run requires its own dedicated, ledger-gated path (not "
            "implemented in Phase 1)."
        )
    if canonical == SPLIT_VALIDATION and not validation_authorized:
        raise SplitAccessDenied(
            "validation split access requires explicit authorization "
            "(validation_authorized=True); refusing by default (fail-closed)."
        )
    return canonical


def is_split_access_allowed(
    split_name: str,
    *,
    path: Optional[Union[str, Path]] = None,
    validation_authorized: bool = False,
) -> bool:
    """Non-raising convenience wrapper around assert_split_access_allowed."""
    try:
        assert_split_access_allowed(
            split_name, path=path, validation_authorized=validation_authorized
        )
        return True
    except SplitAccessDenied:
        return False

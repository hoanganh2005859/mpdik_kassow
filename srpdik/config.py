"""Loader/writer + policy checks for srpdik's own method configs (configs/srpdik/*.json).

Every srpdik config must declare schema_version/method_version/description, contain no
absolute filesystem path, and never reference a protected reference field (q_reference,
q_target_reference, ...). This module enforces that fail-closed: a violation raises
SRPDIKConfigError rather than being silently accepted.
"""

import json
from pathlib import Path
from typing import Any, Iterator

from srpdik import constants
from srpdik.exceptions import SRPDIKConfigError
from srpdik.paths import srpdik_config_path

REQUIRED_METADATA_FIELDS = ("schema_version", "method_version", "description")


def _iter_values(obj: Any) -> Iterator[str]:
    if isinstance(obj, dict):
        for value in obj.values():
            yield from _iter_values(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_values(item)
    elif isinstance(obj, str):
        yield obj


def _iter_keys(obj: Any) -> Iterator[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _iter_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_keys(item)


def _looks_like_absolute_path(value: str) -> bool:
    if value.startswith("/"):
        return True
    # Windows drive-letter absolute path, e.g. "D:\\" or "D:/".
    return len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in ("\\", "/")


def assert_config_policy(config: dict, *, context: str) -> None:
    """Fail-closed structural policy check applied to every srpdik config before it is used.

    Rejects: any absolute path string (Windows or POSIX) anywhere in the document's values, and
    any dict *key* that names/embeds a protected reference field. A protected-field token is
    still allowed to appear as a *value* inside an explicitly-named exclusion list (e.g.
    ``"forbidden_fields": ["q_target_reference"]``) -- documenting what must never be wired in is
    required by the spec (see docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md items 3/12); only a
    live field *key* would actually wire protected data into the pipeline.
    """
    for value in _iter_values(config):
        if _looks_like_absolute_path(value):
            raise SRPDIKConfigError(f"{context}: absolute path not allowed: {value!r}")

    for key in _iter_keys(config):
        lowered = key.lower()
        for token in constants.FORBIDDEN_FIELD_SUBSTRINGS:
            if token in lowered:
                raise SRPDIKConfigError(
                    f"{context}: forbidden protected-field key {token!r} found in key {key!r}"
                )


def assert_required_metadata(config: dict, *, context: str) -> None:
    missing = [field for field in REQUIRED_METADATA_FIELDS if field not in config]
    if missing:
        raise SRPDIKConfigError(f"{context}: missing required metadata field(s): {missing}")


def load_srpdik_config(filename: str) -> dict:
    """Load and policy-check one config file from configs/srpdik/ by filename.

    Raises SRPDIKConfigError (fail-closed) if the file is missing, is not valid JSON, is
    missing required metadata, or fails the path/protected-field policy check.
    """
    path = srpdik_config_path(filename)
    if not path.is_file():
        raise SRPDIKConfigError(f"srpdik config not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise SRPDIKConfigError(f"srpdik config {filename} is not valid JSON: {exc}") from exc

    if not isinstance(config, dict):
        raise SRPDIKConfigError(f"srpdik config {filename} must decode to a JSON object")

    assert_required_metadata(config, context=filename)
    assert_config_policy(config, context=filename)
    return config


def write_srpdik_config(path: Path, config: dict) -> None:
    """Write a config with deterministic key order (sorted keys, 2-space indent, trailing newline)."""
    text = json.dumps(config, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")

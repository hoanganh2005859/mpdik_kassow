"""Summary manifest of the srpdik configuration layer, for audit/traceability use.

Read-only: builds a dict describing what config files exist and their hashes/metadata. Does not
create, modify, or delete any file.
"""

from typing import Dict

from srpdik import constants
from srpdik.config import load_srpdik_config
from srpdik.paths import srpdik_config_path
from utils.file_checksum import sha256_file


def build_srpdik_config_manifest() -> Dict[str, dict]:
    """Return ``{filename: {"sha256", "schema_version", "method_version"}}`` for every known
    srpdik method config (excludes the DLS lock file, which has its own dedicated verifier in
    ``srpdik/dls_lock.py``). Raises SRPDIKConfigError (via load_srpdik_config) if any expected
    config is missing or invalid.
    """
    manifest: Dict[str, dict] = {}
    for filename in constants.CONFIG_FILENAMES:
        path = srpdik_config_path(filename)
        config = load_srpdik_config(filename)
        manifest[filename] = {
            "sha256": sha256_file(path),
            "schema_version": config.get("schema_version"),
            "method_version": config.get("method_version"),
        }
    return manifest

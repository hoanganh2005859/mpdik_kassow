"""SR-PPO-DLS specific exceptions.

All srpdik verification/guard code is fail-closed: missing files, hash mismatches, unknown
dataset splits, or ambiguous authorization raise one of these rather than silently proceeding.
"""


class SRPDIKError(Exception):
    """Base class for all srpdik-specific errors."""


class SRPDIKConfigError(SRPDIKError):
    """Raised when an srpdik config file is missing, malformed, or fails a policy check
    (absolute path, protected-field reference, missing required metadata)."""


class DLSLockVerificationError(SRPDIKError):
    """Raised when the locked pure-DLS snapshot fails candidate/source/config hash verification."""


class SplitAccessDenied(SRPDIKError):
    """Raised when a caller requests access to a dataset split that policy forbids, or supplies
    an unrecognized/ambiguous split name (fail-closed: unknown means denied)."""

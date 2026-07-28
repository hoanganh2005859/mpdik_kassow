"""Locked, project-wide constants for the SR-PPO-DLS method.

Values here reflect PDF-derived design decisions already locked in
``docs/srpdik/DECISIONS.md`` and ``docs/srpdik/SRPDIK_REFERENCE_REQUIREMENTS.md``. This module
implements no solver/env/training behavior itself.
"""

METHOD_NAME = "srpdik"

#: The one official locked DLS candidate this method is built on top of (never retuned).
OFFICIAL_DLS_CANDIDATE_ID = "cand_D_pure_dls"

LOCK_FORMAT_VERSION = "1.0.0"

#: PDF section 6.3 (36-D observation) / 6.5 (7-D residual action).
OBSERVATION_DIM = 36
ACTION_DIM = 7

SPLIT_TRAIN = "train"
SPLIT_DEVELOPMENT = "development"
SPLIT_VALIDATION = "validation"
SPLIT_FROZEN_TEST = "frozen_test"

KNOWN_SPLITS = frozenset({SPLIT_TRAIN, SPLIT_DEVELOPMENT, SPLIT_VALIDATION, SPLIT_FROZEN_TEST})

#: Method-level config filenames under configs/srpdik/ (excludes the DLS lock file, which has
#: its own dedicated loader/verifier in srpdik/dls_lock.py).
CONFIG_FILENAMES = (
    "srpdik_method.json",
    "srpdik_observation.json",
    "srpdik_action.json",
    "srpdik_safety.json",
    "srpdik_reward.json",
    "srpdik_training.json",
    "srpdik_curriculum.json",
    "srpdik_evaluation.json",
    "srpdik_data.json",
)

DLS_LOCK_FILENAME = "dls_locked.json"

#: The Phase 0 reference PDF, copied verbatim into docs/srpdik/references/ (see DECISIONS.md #3).
PDF_REFERENCE_RELATIVE_PATH = (
    "docs/srpdik/references/SR_PPO_DLS_KR810_Theory_and_Dataset_Application.pdf"
)
PDF_REFERENCE_SHA256 = "b9a9fe0c65719ccbcfb7cf92bbea4b72b016d6a1c43f91892614bdfad0c96395"

#: Field names/substrings that must never appear as keys in srpdik config or observation code
#: (PDF p.7 "Cac field bi cam"; mirrors evaluation_v2.protected_guard.PROTECTED_FIELD_NAMES).
FORBIDDEN_FIELD_SUBSTRINGS = (
    "q_reference",
    "q_target_reference",
    "q_source_reference",
    "reconstruction_error",
    "waypoint_reachable",
)

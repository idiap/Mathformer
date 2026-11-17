# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep external benchmark adapters isolated from core framework code.
#
# Intent:
#   Represent benchmark loading, evaluation, and documentation conventions clearly for repeatable experiments.
#
# Function:
#   Defines adapters and notes for benchmark families used in evaluation workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

from .proofnet import (
    DEFAULT_DATA_DIR,
    DATASET_REPO_ID,
    OPTIONAL_FILES,
    REQUIRED_FIELDS,
    SPLIT_TO_FILE,
    ProofNetExample,
    ProofNetError,
    build_autoformalization_prompt,
    dataset_stats,
    download_proofnet,
    export_generation_inputs,
    load_split,
)

__all__ = [
    "DEFAULT_DATA_DIR",
    "DATASET_REPO_ID",
    "OPTIONAL_FILES",
    "REQUIRED_FIELDS",
    "SPLIT_TO_FILE",
    "ProofNetExample",
    "ProofNetError",
    "build_autoformalization_prompt",
    "dataset_stats",
    "download_proofnet",
    "export_generation_inputs",
    "load_split",
]

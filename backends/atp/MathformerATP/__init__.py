# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Bridge informal theorem statements and first-order automated theorem proving in a traceable way.
#
# Intent:
#   Represent ATP candidates, premise-selection evidence, Vampire execution, and proof artifacts as explicit data.
#
# Function:
#   Defines the proof-search machinery used by examples, tests, and theorem-discovery workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""ATP integrations for Mathformer."""

from .generation import (
    GeneratedLemma,
    PremiseGenerationReport,
    generate_candidate_lemmas,
)
from .premises import (
    PremiseCandidate,
    PremiseSelectionReport,
    build_premise_registry,
    select_premises,
)
from .vampire import (
    ATPProblem,
    ATPResult,
    InformalProof,
    TPTPFormula,
    VampireRunner,
    aggressive_autoformalize,
    discover_proof,
    group_inverse_product_problem,
    group_triple_inverse_product_problem,
    informalize_proof,
    transitive_irreflexive_asymmetric_problem,
    unary_implication_chain_problem,
)

__all__ = [
    "ATPProblem",
    "ATPResult",
    "GeneratedLemma",
    "InformalProof",
    "PremiseCandidate",
    "PremiseGenerationReport",
    "PremiseSelectionReport",
    "TPTPFormula",
    "VampireRunner",
    "aggressive_autoformalize",
    "build_premise_registry",
    "discover_proof",
    "generate_candidate_lemmas",
    "group_inverse_product_problem",
    "group_triple_inverse_product_problem",
    "informalize_proof",
    "select_premises",
    "transitive_irreflexive_asymmetric_problem",
    "unary_implication_chain_problem",
]

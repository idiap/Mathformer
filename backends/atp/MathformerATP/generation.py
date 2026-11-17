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

"""Premise generation templates for Mathformer ATP search."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .premises import PremiseCandidate


@dataclass
class GeneratedLemma:
    """A generated premise candidate plus its proof/promotion state."""

    id: str
    candidate: PremiseCandidate
    generation_reason: str
    dependency_ids: list[str]
    attempt_proof: bool = True
    proof_status: str = "unattempted"
    promoted: bool = False
    problem_path: str | None = None
    result_path: str | None = None
    proof_path: str | None = None
    rejection_reason: str | None = None
    elapsed_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``GeneratedLemma.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``GeneratedLemma.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        payload = asdict(self)
        payload["candidate"] = self.candidate.to_dict()
        return payload


@dataclass
class PremiseGenerationReport:
    """Document the responsibility of ``PremiseGenerationReport``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Group related state and behavior so callers can use this part of the MathformerATP workflow through a clear object boundary.

    Function:
        Defines the proof-search machinery used by examples, tests, and theorem-discovery workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    problem_id: str
    generated_count: int
    attempted_count: int
    proved_count: int
    promoted_ids: list[str]
    generated_lemmas: list[GeneratedLemma] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``PremiseGenerationReport.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``PremiseGenerationReport.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "problem_id": self.problem_id,
            "generated_count": self.generated_count,
            "attempted_count": self.attempted_count,
            "proved_count": self.proved_count,
            "promoted_ids": self.promoted_ids,
            "generated_lemmas": [lemma.to_dict() for lemma in self.generated_lemmas],
            "notes": self.notes,
        }


def generate_candidate_lemmas(
    problem: Any, selected_premises: list[PremiseCandidate]
) -> list[GeneratedLemma]:
    """Document the responsibility of ``generate_candidate_lemmas``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``generate_candidate_lemmas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    strategy = str(
        getattr(problem, "metadata", {}).get("autoformalization_strategy", "")
    ).lower()
    if "group triple inverse product theorem" in strategy:
        return _group_triple_inverse_product_lemmas(selected_premises)
    if "group inverse product theorem" in strategy:
        return _group_inverse_product_lemmas(selected_premises)
    return []


def build_generation_report(
    problem_id: str, generated_lemmas: list[GeneratedLemma]
) -> PremiseGenerationReport:
    """Document the responsibility of ``build_generation_report``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    attempted = [lemma for lemma in generated_lemmas if lemma.attempt_proof]
    proved = [lemma for lemma in generated_lemmas if lemma.promoted]
    notes = [
        "Generated lemmas are promoted only after a separate Vampire proof succeeds.",
        "Rejected generated lemmas remain visible in the report but are not inserted into theorem attempts.",
    ]
    return PremiseGenerationReport(
        problem_id=problem_id,
        generated_count=len(generated_lemmas),
        attempted_count=len(attempted),
        proved_count=len(proved),
        promoted_ids=[lemma.id for lemma in proved],
        generated_lemmas=generated_lemmas,
        notes=notes,
    )


def promoted_candidates(
    generated_lemmas: list[GeneratedLemma],
) -> list[PremiseCandidate]:
    """Document the responsibility of ``promoted_candidates``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``promoted_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [lemma.candidate for lemma in generated_lemmas if lemma.promoted]


def _group_inverse_product_lemmas(
    selected_premises: list[PremiseCandidate],
) -> list[GeneratedLemma]:
    """Document the responsibility of ``_group_inverse_product_lemmas``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_group_inverse_product_lemmas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    dependency_ids = [candidate.id for candidate in selected_premises]
    common_tags = ["algebra", "group", "equality"]
    return [
        GeneratedLemma(
            id="product_candidate_right_inverse",
            candidate=PremiseCandidate(
                id="generated_product_candidate_right_inverse",
                name="generated_product_candidate_right_inverse",
                formula="! [X,Y] : ( mul(mul(X,Y),mul(inv(Y),inv(X))) = e )",
                premise_type="generated_hypothesis",
                provenance="generated from reverse-order inverse proof plan",
                domain_tags=common_tags,
                theorem_shapes=["equational", "universal"],
                dependency_ids=dependency_ids,
            ),
            generation_reason=(
                "The goal identifies mul(inv(Y),inv(X)) as the candidate inverse of mul(X,Y); "
                "prove it is a right inverse."
            ),
            dependency_ids=dependency_ids,
        ),
        GeneratedLemma(
            id="product_candidate_left_inverse",
            candidate=PremiseCandidate(
                id="generated_product_candidate_left_inverse",
                name="generated_product_candidate_left_inverse",
                formula="! [X,Y] : ( mul(mul(inv(Y),inv(X)),mul(X,Y)) = e )",
                premise_type="generated_hypothesis",
                provenance="generated from reverse-order inverse proof plan",
                domain_tags=common_tags,
                theorem_shapes=["equational", "universal"],
                dependency_ids=dependency_ids,
            ),
            generation_reason=(
                "The goal identifies mul(inv(Y),inv(X)) as the candidate inverse of mul(X,Y); "
                "prove it is a left inverse."
            ),
            dependency_ids=dependency_ids,
        ),
        GeneratedLemma(
            id="two_sided_inverse_unique",
            candidate=PremiseCandidate(
                id="generated_two_sided_inverse_unique",
                name="generated_two_sided_inverse_unique",
                formula="! [A,B] : ( ( mul(A,B) = e & mul(B,A) = e ) => inv(A) = B )",
                premise_type="generated_hypothesis",
                provenance="generated bridge from two-sided inverse proof to inverse equality",
                domain_tags=common_tags,
                theorem_shapes=["equational", "implicational", "universal"],
                dependency_ids=dependency_ids,
            ),
            generation_reason=(
                "If B is proved to be both a right and left inverse of A, then B must be inv(A)."
            ),
            dependency_ids=dependency_ids,
        ),
        GeneratedLemma(
            id="unsafe_group_commutativity_shortcut",
            candidate=PremiseCandidate(
                id="generated_unsafe_group_commutativity_shortcut",
                name="generated_unsafe_group_commutativity_shortcut",
                formula="! [X,Y] : ( mul(X,Y) = mul(Y,X) )",
                premise_type="rejected_generated_lemma",
                provenance="unsafe generated shortcut rejected before proof search",
                domain_tags=common_tags,
                theorem_shapes=["equational", "universal"],
                dependency_ids=dependency_ids,
                rejected_reason="would silently strengthen group to abelian group",
            ),
            generation_reason="Rejected adversarial shortcut: commutativity would make the goal easier but is not source-backed.",
            dependency_ids=dependency_ids,
            attempt_proof=False,
            proof_status="rejected",
            rejection_reason="not attempted because it is an unsafe strengthening of the source context",
        ),
    ]


def _group_triple_inverse_product_lemmas(
    selected_premises: list[PremiseCandidate],
) -> list[GeneratedLemma]:
    """Document the responsibility of ``_group_triple_inverse_product_lemmas``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_group_triple_inverse_product_lemmas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    dependency_ids = [candidate.id for candidate in selected_premises]
    common_tags = ["algebra", "group", "equality"]
    return [
        GeneratedLemma(
            id="binary_product_inverse_reverse_order",
            candidate=PremiseCandidate(
                id="generated_binary_product_inverse_reverse_order",
                name="generated_binary_product_inverse_reverse_order",
                formula="! [X,Y] : ( inv(mul(X,Y)) = mul(inv(Y),inv(X)) )",
                premise_type="generated_hypothesis",
                provenance="generated as a reusable helper for triple-product inverse reversal",
                domain_tags=common_tags,
                theorem_shapes=["equational", "universal"],
                dependency_ids=dependency_ids,
            ),
            generation_reason=(
                "The triple-product goal can be decomposed by first proving the binary inverse-of-product theorem."
            ),
            dependency_ids=dependency_ids,
        ),
        GeneratedLemma(
            id="unsafe_group_commutativity_shortcut",
            candidate=PremiseCandidate(
                id="generated_unsafe_group_commutativity_shortcut",
                name="generated_unsafe_group_commutativity_shortcut",
                formula="! [X,Y] : ( mul(X,Y) = mul(Y,X) )",
                premise_type="rejected_generated_lemma",
                provenance="unsafe generated shortcut rejected before proof search",
                domain_tags=common_tags,
                theorem_shapes=["equational", "universal"],
                dependency_ids=dependency_ids,
                rejected_reason="would silently strengthen group to abelian group",
            ),
            generation_reason="Rejected adversarial shortcut: commutativity would make the goal easier but is not source-backed.",
            dependency_ids=dependency_ids,
            attempt_proof=False,
            proof_status="rejected",
            rejection_reason="not attempted because it is an unsafe strengthening of the source context",
        ),
    ]

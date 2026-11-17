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

"""Premise selection data model and scoring for Mathformer ATP search."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

TRUSTED_PREMISE_TYPES = {
    "source_assumption",
    "library_fact",
    "definition_expansion",
    "proved_generated_lemma",
}

UNTRUSTED_PREMISE_TYPES = {
    "generated_hypothesis",
    "search_hint_only",
    "rejected_generated_lemma",
}

TPTP_RESERVED_WORDS = {
    "fof",
    "cnf",
    "tff",
    "thf",
    "axiom",
    "conjecture",
    "lemma",
    "definition",
    "hypothesis",
}


@dataclass
class PremiseCandidate:
    """A possible premise with explicit provenance and trust state."""

    id: str
    name: str
    formula: str
    premise_type: str
    provenance: str
    formula_role: str = "axiom"
    language: str = "fof"
    domain_tags: list[str] = field(default_factory=list)
    theorem_shapes: list[str] = field(default_factory=list)
    source_span: str | None = None
    dependency_ids: list[str] = field(default_factory=list)
    negative_domain_tags: list[str] = field(default_factory=list)
    selected: bool = False
    score: float = 0.0
    score_reasons: list[str] = field(default_factory=list)
    rejected_reason: str | None = None

    @property
    def trusted(self) -> bool:
        """Document the responsibility of ``PremiseCandidate.trusted``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``PremiseCandidate.trusted`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return self.premise_type in TRUSTED_PREMISE_TYPES

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``PremiseCandidate.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``PremiseCandidate.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        payload = asdict(self)
        payload["trusted"] = self.trusted
        payload["symbols"] = sorted(extract_formula_symbols(self.formula))
        return payload


@dataclass
class PremiseSelectionReport:
    """A serializable report for one theorem's premise selection pass."""

    problem_id: str
    budget: str
    target_formula: str
    target_symbols: list[str]
    target_shapes: list[str]
    target_domain_tags: list[str]
    candidate_count: int
    selected_count: int
    selected_ids: list[str]
    candidates: list[PremiseCandidate]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Document the responsibility of ``PremiseSelectionReport.to_dict``.

        Motivation:
            Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

        Intent:
            Provide the local operation named ``PremiseSelectionReport.to_dict`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return {
            "problem_id": self.problem_id,
            "budget": self.budget,
            "target_formula": self.target_formula,
            "target_symbols": self.target_symbols,
            "target_shapes": self.target_shapes,
            "target_domain_tags": self.target_domain_tags,
            "candidate_count": self.candidate_count,
            "selected_count": self.selected_count,
            "selected_ids": self.selected_ids,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "notes": self.notes,
        }


def extract_formula_symbols(formula: str) -> set[str]:
    """Extract lower-case TPTP function, predicate, and constant symbols."""

    symbols: set[str] = set()
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_]*\b", formula):
        if token in TPTP_RESERVED_WORDS:
            continue
        if token[0].isupper():
            continue
        symbols.add(token)
    return symbols


def infer_formula_shapes(formula: str) -> list[str]:
    """Document the responsibility of ``infer_formula_shapes``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``infer_formula_shapes`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    shapes: list[str] = []
    if "=" in formula:
        shapes.append("equational")
    if "=>" in formula or "<=>" in formula:
        shapes.append("implicational")
    if "~" in formula:
        shapes.append("negated")
    if "!" in formula:
        shapes.append("universal")
    if "?" in formula:
        shapes.append("existential")
    return shapes or ["atomic"]


def infer_problem_domain_tags(
    problem_metadata: dict[str, Any], target_formula: str
) -> list[str]:
    """Document the responsibility of ``infer_problem_domain_tags``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``infer_problem_domain_tags`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    strategy = str(problem_metadata.get("autoformalization_strategy", "")).lower()
    tags: set[str] = set()
    if "group" in strategy or {"mul", "inv", "e"} & extract_formula_symbols(
        target_formula
    ):
        tags.update({"algebra", "group", "equality"})
    if "subset" in strategy or "member" in target_formula or "subset" in target_formula:
        tags.update({"set", "membership", "first_order"})
    if "relation" in strategy or "asymmetric" in strategy or "transitive" in strategy:
        tags.update({"relation", "first_order"})
    if "=" in target_formula:
        tags.add("equality")
    return sorted(tags)


def build_premise_registry(problem: Any) -> list[PremiseCandidate]:
    """Build the local premise universe for an ATP problem.

    The problem object is intentionally duck-typed so this module stays
    independent from the Vampire runner classes.
    """

    candidates: list[PremiseCandidate] = []
    metadata = dict(getattr(problem, "metadata", {}) or {})
    target = next(
        (formula for formula in problem.formulas if formula.role == "conjecture"), None
    )
    target_formula = target.formula if target else ""
    domain_tags = infer_problem_domain_tags(metadata, target_formula)

    for formula in problem.formulas:
        if formula.role == "conjecture":
            continue
        candidates.append(
            PremiseCandidate(
                id=formula.name,
                name=formula.name,
                formula=formula.formula,
                formula_role=formula.role,
                language=formula.language,
                premise_type="source_assumption",
                provenance="autoformalized theorem context",
                domain_tags=domain_tags,
                theorem_shapes=infer_formula_shapes(formula.formula),
                source_span=problem.informal_statement or None,
            )
        )

    strategy = str(metadata.get("autoformalization_strategy", "")).lower()
    if "group" in strategy and "inverse" in strategy:
        candidates.extend(_group_registry_distractors())
    elif "relation" in strategy or "asymmetric" in strategy:
        candidates.extend(_relation_registry_distractors())
    elif "subset" in strategy:
        candidates.extend(_subset_registry_distractors())

    return candidates


def _group_registry_distractors() -> list[PremiseCandidate]:
    """Useful-looking but untrusted facts used to test rejection discipline."""

    return [
        PremiseCandidate(
            id="group_commutativity_shortcut",
            name="group_commutativity_shortcut",
            formula="! [X,Y] : ( mul(X,Y) = mul(Y,X) )",
            premise_type="generated_hypothesis",
            provenance="unsafe generated shortcut; not valid for arbitrary groups",
            domain_tags=["algebra", "group", "equality"],
            theorem_shapes=["equational", "universal"],
            rejected_reason="not source-backed and not valid for all groups",
        ),
        PremiseCandidate(
            id="relation_transitivity_distractor",
            name="relation_transitivity_distractor",
            formula="! [X,Y,Z] : ( ( r(X,Y) & r(Y,Z) ) => r(X,Z) )",
            premise_type="search_hint_only",
            provenance="cross-domain registry distractor",
            domain_tags=["relation", "first_order"],
            negative_domain_tags=["group"],
            theorem_shapes=["implicational", "universal"],
            rejected_reason="domain mismatch",
        ),
    ]


def _relation_registry_distractors() -> list[PremiseCandidate]:
    """Document the responsibility of ``_relation_registry_distractors``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_relation_registry_distractors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        PremiseCandidate(
            id="group_associativity_distractor",
            name="group_associativity_distractor",
            formula="! [X,Y,Z] : ( mul(mul(X,Y),Z) = mul(X,mul(Y,Z)) )",
            premise_type="search_hint_only",
            provenance="cross-domain registry distractor",
            domain_tags=["algebra", "group", "equality"],
            negative_domain_tags=["relation"],
            theorem_shapes=["equational", "universal"],
            rejected_reason="domain mismatch",
        )
    ]


def _subset_registry_distractors() -> list[PremiseCandidate]:
    """Document the responsibility of ``_subset_registry_distractors``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_subset_registry_distractors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [
        PremiseCandidate(
            id="set_extensionality_hint",
            name="set_extensionality_hint",
            formula="! [A,B] : ( ( ! [X] : ( member(X,A) <=> member(X,B) ) ) => A = B )",
            premise_type="search_hint_only",
            provenance="not required for subset transitivity",
            domain_tags=["set", "membership", "equality"],
            theorem_shapes=["equational", "implicational", "universal"],
            rejected_reason="not needed by target theorem shape",
        )
    ]


def select_premises(
    problem: Any, candidates: list[PremiseCandidate], *, budget: str = "medium"
) -> PremiseSelectionReport:
    """Document the responsibility of ``select_premises``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``select_premises`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    conjecture = next(
        (formula for formula in problem.formulas if formula.role == "conjecture"), None
    )
    if conjecture is None:
        raise ValueError(f"Problem {problem.problem_id!r} has no conjecture formula.")

    target_symbols = extract_formula_symbols(conjecture.formula)
    target_shapes = set(infer_formula_shapes(conjecture.formula))
    target_domain_tags = set(
        infer_problem_domain_tags(problem.metadata, conjecture.formula)
    )
    max_selected = _budget_limit(budget, candidates)

    scored: list[PremiseCandidate] = []
    for candidate in candidates:
        score, reasons = _score_candidate(
            candidate,
            target_symbols=target_symbols,
            target_shapes=target_shapes,
            target_domain_tags=target_domain_tags,
        )
        candidate.score = score
        candidate.score_reasons = reasons
        candidate.selected = False
        scored.append(candidate)

    trusted_positive = [
        candidate
        for candidate in sorted(scored, key=lambda item: (-item.score, item.id))
        if candidate.trusted and candidate.score > 0
    ]
    selected = trusted_positive[:max_selected]
    for candidate in selected:
        candidate.selected = True
        candidate.rejected_reason = None
    selected_ids = {candidate.id for candidate in selected}
    for candidate in scored:
        if candidate.id not in selected_ids and candidate.rejected_reason is None:
            if not candidate.trusted:
                candidate.rejected_reason = (
                    "untrusted premise cannot be selected without proof"
                )
            elif candidate.score <= 0:
                candidate.rejected_reason = "score did not meet selection threshold"
            else:
                candidate.rejected_reason = f"excluded by {budget!r} premise budget"

    notes = [
        "Only trusted source/library/definition premises are selectable at this stage.",
        "Generated premises must be proved in a separate obligation before promotion.",
    ]
    return PremiseSelectionReport(
        problem_id=problem.problem_id,
        budget=budget,
        target_formula=conjecture.formula,
        target_symbols=sorted(target_symbols),
        target_shapes=sorted(target_shapes),
        target_domain_tags=sorted(target_domain_tags),
        candidate_count=len(scored),
        selected_count=len(selected),
        selected_ids=[candidate.id for candidate in selected],
        candidates=scored,
        notes=notes,
    )


def selected_candidates(report: PremiseSelectionReport) -> list[PremiseCandidate]:
    """Document the responsibility of ``selected_candidates``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``selected_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [candidate for candidate in report.candidates if candidate.selected]


def _budget_limit(budget: str, candidates: list[PremiseCandidate]) -> int:
    """Document the responsibility of ``_budget_limit``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_budget_limit`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if budget == "tiny":
        return 2
    if budget == "small":
        return 4
    if budget == "medium":
        return 8
    if budget == "full":
        return len(candidates)
    raise ValueError(f"Unknown premise budget {budget!r}.")


def _score_candidate(
    candidate: PremiseCandidate,
    *,
    target_symbols: set[str],
    target_shapes: set[str],
    target_domain_tags: set[str],
) -> tuple[float, list[str]]:
    """Document the responsibility of ``_score_candidate``.

    Motivation:
        Bridge informal theorem statements and first-order automated theorem proving in a traceable way.

    Intent:
        Provide the local operation named ``_score_candidate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    score = 0.0
    reasons: list[str] = []

    if candidate.trusted:
        score += 4.0
        reasons.append("+4 trusted provenance")
    else:
        score -= 8.0
        reasons.append("-8 untrusted/search-only provenance")

    candidate_symbols = extract_formula_symbols(candidate.formula)
    overlap = sorted(candidate_symbols & target_symbols)
    if overlap:
        symbol_score = min(4.0, float(len(overlap)))
        score += symbol_score
        reasons.append(f"+{symbol_score:g} symbol overlap: {', '.join(overlap)}")

    domain_overlap = sorted(set(candidate.domain_tags) & target_domain_tags)
    if domain_overlap:
        score += 2.0
        reasons.append(f"+2 domain overlap: {', '.join(domain_overlap)}")

    negative_overlap = sorted(set(candidate.negative_domain_tags) & target_domain_tags)
    if negative_overlap:
        score -= 5.0
        reasons.append(f"-5 negative domain overlap: {', '.join(negative_overlap)}")

    shape_overlap = sorted(set(candidate.theorem_shapes) & target_shapes)
    if shape_overlap:
        score += 1.0
        reasons.append(f"+1 shape overlap: {', '.join(shape_overlap)}")

    if not reasons:
        reasons.append("no positive evidence")
    return score, reasons

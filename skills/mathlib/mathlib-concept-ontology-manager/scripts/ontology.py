#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Shared ontology-profile loader for Mathformer mathlib concept tools."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PROFILE = (
    REPO_ROOT
    / "skills"
    / "mathlib"
    / "mathlib-concept-ontology-manager"
    / "references"
    / "core.yaml"
)


def normalize_token(value: str) -> str:
    """Document the responsibility of ``normalize_token``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_token`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = value.strip().lower().replace("-", "_")
    text = re.sub(r"\s+", "_", text)
    text = text.strip("_'")
    if text.endswith("'s"):
        text = text[:-2]
    elif text.endswith("s'"):
        text = text[:-1]
    return text


def normalize_surface(value: str) -> str:
    """Document the responsibility of ``normalize_surface``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_surface`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return re.sub(r"\s+", " ", value.strip().lower().replace("_", " "))


def load_profile(path: Path | str | None = None) -> Dict[str, Any]:
    """Document the responsibility of ``load_profile``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    profile_path = DEFAULT_PROFILE if path is None else Path(path)
    raw = profile_path.read_text(encoding="utf-8")
    start_positions = [pos for pos in (raw.find("{"), raw.find("[")) if pos >= 0]
    if start_positions:
        raw = raw[min(start_positions) :]
    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{profile_path} must use the JSON subset of YAML; parse failed: {exc}"
        ) from exc
    if not isinstance(profile, dict):
        raise ValueError(f"{profile_path} must contain a mapping at the top level")
    profile["_profile_path"] = str(profile_path)
    return profile


def list_string_map(value: Any, *, field: str) -> Dict[str, List[str]]:
    """Document the responsibility of ``list_string_map``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``list_string_map`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    out: Dict[str, List[str]] = {}
    for key, items in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field} keys must be strings")
        if not isinstance(items, list) or not all(
            isinstance(item, str) for item in items
        ):
            raise ValueError(f"{field}.{key} must be a list of strings")
        out[key] = list(items)
    return out


def list_strings(value: Any, *, field: str) -> List[str]:
    """Document the responsibility of ``list_strings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``list_strings`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be a list of strings")
    return list(value)


def concept_profiles(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``concept_profiles``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concept_profiles`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    concepts = profile.get("concepts", [])
    if not isinstance(concepts, list):
        raise ValueError("concepts must be a list")
    out: List[Dict[str, Any]] = []
    for idx, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            raise ValueError(f"concepts[{idx}] must be an object")
        concept_id = concept.get("concept_id")
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise ValueError(f"concepts[{idx}].concept_id must be a nonempty string")
        out.append(concept)
    return out


def synonym_map(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Document the responsibility of ``synonym_map``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``synonym_map`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return list_string_map(profile.get("synonyms"), field="synonyms")


def preferred_decls(profile: Dict[str, Any]) -> Dict[str, List[str]]:
    """Document the responsibility of ``preferred_decls``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``preferred_decls`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return list_string_map(profile.get("preferred_decls"), field="preferred_decls")


def phrase_hints(profile: Dict[str, Any]) -> List[str]:
    """Document the responsibility of ``phrase_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phrase_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return list_strings(profile.get("phrase_hints"), field="phrase_hints")


def keyword_hints(profile: Dict[str, Any]) -> List[str]:
    """Document the responsibility of ``keyword_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``keyword_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return list_strings(profile.get("keyword_hints"), field="keyword_hints")


def all_surface_terms(profile: Dict[str, Any]) -> List[str]:
    """Document the responsibility of ``all_surface_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``all_surface_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    terms = set(phrase_hints(profile))
    for concept in concept_profiles(profile):
        for surface in concept.get("surface_terms", []):
            if isinstance(surface, str):
                terms.add(surface)
    return sorted(terms, key=lambda item: (-len(item), item))


def matching_concepts(
    profile: Dict[str, Any], surface_or_concept: str
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``matching_concepts``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``matching_concepts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = normalize_surface(surface_or_concept)
    normalized_token = normalize_token(surface_or_concept)
    matches: List[Dict[str, Any]] = []
    for concept in concept_profiles(profile):
        concept_id = str(concept.get("concept_id", ""))
        surfaces = [
            str(item)
            for item in concept.get("surface_terms", [])
            if isinstance(item, str)
        ]
        keys = {normalize_surface(item) for item in surfaces}
        keys.add(normalize_surface(concept_id.replace(".", " ")))
        keys.add(normalize_token(concept_id.split(".")[-1]))
        if normalized in keys or normalized_token in keys:
            matches.append(concept)
    return matches


def ontology_terms_for_concept(profile: Dict[str, Any], concept: str) -> List[str]:
    """Document the responsibility of ``ontology_terms_for_concept``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ontology_terms_for_concept`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    terms = set()
    for matched in matching_concepts(profile, concept):
        for key in (
            "surface_terms",
            "domain_tags",
            "lean_objects",
            "preferred_declarations",
            "preferred_modules",
        ):
            for item in matched.get(key, []):
                if isinstance(item, str):
                    terms.add(item.lower())
                    terms.add(normalize_token(item))
        concept_id = str(matched.get("concept_id", ""))
        if concept_id:
            terms.update(normalize_token(part) for part in concept_id.split("."))
    return sorted(term for term in terms if term)


def validate_profile(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``validate_profile``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for concept in concept_profiles(profile):
        concept_id = str(concept["concept_id"])
        if concept_id in seen:
            findings.append(
                {
                    "severity": "high",
                    "code": "duplicate_concept_id",
                    "message": f"Duplicate concept id `{concept_id}`.",
                }
            )
        seen.add(concept_id)
        for required in ("surface_terms", "domain_tags", "lean_objects", "status"):
            if required not in concept:
                findings.append(
                    {
                        "severity": "medium",
                        "code": "missing_concept_field",
                        "message": f"{concept_id} is missing `{required}`.",
                    }
                )
        surfaces = concept.get("surface_terms", [])
        if not isinstance(surfaces, list) or not surfaces:
            findings.append(
                {
                    "severity": "high",
                    "code": "empty_surface_terms",
                    "message": f"{concept_id} has no surface terms.",
                }
            )
    synonym_map(profile)
    preferred_decls(profile)
    phrase_hints(profile)
    keyword_hints(profile)
    return findings


def clue_hits(text: str, clues: Sequence[str]) -> List[str]:
    """Document the responsibility of ``clue_hits``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``clue_hits`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = normalize_surface(text)
    hits = []
    for clue in clues:
        clue_norm = normalize_surface(clue)
        if clue_norm and clue_norm in normalized:
            hits.append(clue)
    return hits


def text_windows(text: str, term: str, *, radius: int = 96) -> Iterable[Dict[str, Any]]:
    """Document the responsibility of ``text_windows``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``text_windows`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = text.lower()
    term_norm = normalize_surface(term)
    pattern = re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(term_norm) + r"(?![A-Za-z0-9_])"
    )
    for match in pattern.finditer(normalize_surface(normalized)):
        start = max(0, match.start() - radius)
        end = min(len(normalized), match.end() + radius)
        yield {
            "start": match.start(),
            "end": match.end(),
            "context": normalized[start:end],
        }

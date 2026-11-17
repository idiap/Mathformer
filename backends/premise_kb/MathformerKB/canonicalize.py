# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make reusable mathematical facts searchable before they are trusted as proof premises.
#
# Intent:
#   Combine canonical hashes, Bloom-filter membership checks, and vector-space similarity for premise retrieval.
#
# Function:
#   Defines storage, ingestion, indexing, and search behavior for the local premise knowledge base.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Canonicalization and hashing for premise-KB surfaces."""

from __future__ import annotations

import hashlib
import re

from .schema import KBEntry

RESERVED_TPTP = {
    "fof",
    "cnf",
    "tff",
    "thf",
    "axiom",
    "conjecture",
    "lemma",
    "definition",
    "include",
}


def canonicalize_informal(text: str) -> str:
    """Document the responsibility of ``canonicalize_informal``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``canonicalize_informal`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = text.strip().lower()
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"\b(theorem|lemma|corollary|proposition)\s*[:.-]\s*", "", text)
    text = re.sub(r"[^a-z0-9=+\-*/^(),.\\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def canonicalize_latex(text: str) -> str:
    """Document the responsibility of ``canonicalize_latex``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``canonicalize_latex`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = text.strip().lower()
    replacements = {
        r"\cdot": "*",
        r"\times": "*",
        r"\left": "",
        r"\right": "",
        r"\operatorname": "",
        r"\mathrm": "",
        r"\ ": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\{([a-z0-9])\}", r"\1", text)
    text = re.sub(r"\s+", "", text)
    return text


def canonicalize_formal(text: str, *, system: str = "tptp") -> str:
    """Document the responsibility of ``canonicalize_formal``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``canonicalize_formal`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = text.strip()
    text = re.sub(r"%.*", "", text)
    text = re.sub(r"\s+", " ", text)
    if system.lower() == "tptp":
        text = _canonicalize_tptp_variables(text)
    return text.strip().lower()


def canonical_hash(text: str, *, surface: str) -> str:
    """Document the responsibility of ``canonical_hash``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``canonical_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if surface in {"informal", "name", "title", "alias"}:
        canonical = canonicalize_informal(text)
    elif surface == "latex":
        canonical = canonicalize_latex(text)
    elif surface.startswith("formal"):
        canonical = canonicalize_formal(text)
    else:
        canonical = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(f"{surface}\0{canonical}".encode("utf-8")).hexdigest()


def populate_canonical_fields(entry: KBEntry) -> KBEntry:
    """Document the responsibility of ``populate_canonical_fields``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``populate_canonical_fields`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hashes = dict(entry.canonical_hashes)
    hashes.setdefault(
        "informal", canonical_hash(entry.informal_statement, surface="informal")
    )
    if entry.latex_statement:
        hashes.setdefault(
            "latex", canonical_hash(entry.latex_statement, surface="latex")
        )
    name_surface = infer_name_surface(entry)
    if name_surface:
        hashes.setdefault("name", canonical_hash(name_surface, surface="name"))
    for surface in entry.formal_statements:
        key = f"formal_{surface.system.lower()}"
        hashes.setdefault(key, canonical_hash(surface.statement, surface=key))
    entry.canonical_hashes = hashes
    if not entry.symbols:
        entry.symbols = sorted(extract_symbols(entry))
    if not entry.theorem_shape:
        entry.theorem_shape = sorted(infer_theorem_shape(entry))
    return entry


def extract_symbols(entry: KBEntry) -> set[str]:
    """Document the responsibility of ``extract_symbols``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``extract_symbols`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    symbols: set[str] = set()
    texts = [entry.informal_statement]
    if entry.latex_statement:
        texts.append(entry.latex_statement)
    texts.extend(surface.statement for surface in entry.formal_statements)
    for text in texts:
        for token in re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]*\b", text):
            if token in RESERVED_TPTP or token[0].isupper():
                continue
            if len(token) == 1 and token not in {"e", "r", "s", "t"}:
                continue
            symbols.add(token.lower())
    return symbols


def infer_theorem_shape(entry: KBEntry | str) -> set[str]:
    """Document the responsibility of ``infer_theorem_shape``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``infer_theorem_shape`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(entry, str):
        text = entry
    else:
        text_parts = [entry.informal_statement]
        text_parts.extend(surface.statement for surface in entry.formal_statements)
        text = " ".join(text_parts)
    lowered = text.lower()
    shape: set[str] = set()
    if "=" in text or "equal" in lowered or "identity" in lowered:
        shape.add("equational")
    if "=>" in text or "<=>" in text or "if " in lowered or "implies" in lowered:
        shape.add("implicational")
    if "!" in text or "for all" in lowered or "every" in lowered:
        shape.add("universal")
    if "?" in text or "exists" in lowered:
        shape.add("existential")
    if "not " in lowered or "~" in text or "never" in lowered:
        shape.add("negated")
    return shape or {"atomic"}


def semantic_card(entry: KBEntry) -> str:
    """Document the responsibility of ``semantic_card``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``semantic_card`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = [
        entry.informal_statement,
        entry.latex_statement or "",
        " ".join(entry.domain_tags),
        " ".join(entry.symbols),
        " ".join(entry.theorem_shape),
    ]
    parts.extend(surface.statement for surface in entry.formal_statements)
    return " ".join(part for part in parts if part)


def infer_name_surface(entry: KBEntry) -> str | None:
    """Extract a title/name alias for generated name-level seed entries."""
    if not entry.notes or "name_level_seed=true" not in entry.notes:
        return None
    if entry.latex_statement:
        name = re.sub(r"\s+\([^()]+\)\s*$", "", entry.latex_statement).strip()
        if name:
            return name
    match = re.match(
        r"(.+?)\s+is\s+a\s+famous\s+", entry.informal_statement, flags=re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def stable_id_from_statement(prefix: str, statement: str) -> str:
    """Document the responsibility of ``stable_id_from_statement``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``stable_id_from_statement`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    digest = canonical_hash(statement, surface="informal")[:12]
    slug = re.sub(r"[^a-z0-9]+", "_", canonicalize_informal(statement))[:56].strip("_")
    return f"{prefix}.{slug or 'entry'}_{digest}"


def _canonicalize_tptp_variables(text: str) -> str:
    """Document the responsibility of ``_canonicalize_tptp_variables``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_canonicalize_tptp_variables`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    mapping: dict[str, str] = {}
    counter = 0

    def repl(match: re.Match[str]) -> str:
        """Document the responsibility of ``_canonicalize_tptp_variables.repl``.

        Motivation:
            Make reusable mathematical facts searchable before they are trusted as proof premises.

        Intent:
            Provide the local operation named ``_canonicalize_tptp_variables.repl`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        nonlocal counter
        name = match.group(0)
        if name not in mapping:
            mapping[name] = f"V{counter}"
            counter += 1
        return mapping[name]

    return re.sub(r"\b[A-Z][A-Za-z0-9_]*\b", repl, text)

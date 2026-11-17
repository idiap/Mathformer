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

"""Ingestion helpers for premise KB seed lists and local artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from .canonicalize import (
    infer_theorem_shape,
    populate_canonical_fields,
    stable_id_from_statement,
)
from .schema import FormalSurface, KBEntry, ProvenanceRecord


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def generated_seed_entries() -> list[KBEntry]:
    """Document the responsibility of ``generated_seed_entries``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``generated_seed_entries`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    records = [
        {
            "id": "group.inverse_product_reverse_order",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, the inverse of a product is the product of the inverses in reverse order.",
            "latex": "(xy)^{-1} = y^{-1}x^{-1}",
            "formal": "! [X,Y] : ( inv(mul(X,Y)) = mul(inv(Y),inv(X)) )",
            "symbols": ["e", "inv", "mul"],
        },
        {
            "id": "group.inverse_triple_product_reverse_order",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, the inverse of a product of three elements is the product of the inverses in reverse order.",
            "latex": "(xyz)^{-1} = z^{-1}y^{-1}x^{-1}",
            "formal": "! [X,Y,Z] : ( inv(mul(mul(X,Y),Z)) = mul(inv(Z),mul(inv(Y),inv(X))) )",
            "symbols": ["e", "inv", "mul"],
        },
        {
            "id": "group.left_identity",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, the identity element multiplied on the left leaves every element unchanged.",
            "latex": "ex = x",
            "formal": "! [X] : ( mul(e,X) = X )",
            "symbols": ["e", "mul"],
        },
        {
            "id": "group.right_identity",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, every element multiplied by the identity element on the right is unchanged.",
            "latex": "xe = x",
            "formal": "! [X] : ( mul(X,e) = X )",
            "symbols": ["e", "mul"],
        },
        {
            "id": "group.left_inverse",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, the inverse of an element multiplied on the left gives the identity.",
            "latex": "x^{-1}x = e",
            "formal": "! [X] : ( mul(inv(X),X) = e )",
            "symbols": ["e", "inv", "mul"],
        },
        {
            "id": "group.right_inverse",
            "domain_tags": ["algebra", "group", "equality"],
            "informal": "In a group, an element multiplied by its inverse on the right gives the identity.",
            "latex": "xx^{-1} = e",
            "formal": "! [X] : ( mul(X,inv(X)) = e )",
            "symbols": ["e", "inv", "mul"],
        },
        {
            "id": "relation.transitive_irreflexive_asymmetric",
            "domain_tags": ["relation", "first_order"],
            "informal": "Every transitive and irreflexive binary relation is asymmetric.",
            "latex": "transitive(r) and irreflexive(r) implies asymmetric(r)",
            "formal": "! [X,Y] : ( r(X,Y) => ~ r(Y,X) )",
            "symbols": ["r"],
        },
        {
            "id": "set.subset_transitive",
            "domain_tags": ["set", "membership", "first_order"],
            "informal": "If one set is a subset of a second and the second is a subset of a third, then the first is a subset of the third.",
            "latex": "R \\subseteq S \\land S \\subseteq T \\Rightarrow R \\subseteq T",
            "formal": "subset(r,s) & subset(s,t) => subset(r,t)",
            "symbols": ["member", "subset"],
        },
    ]
    provenance = ProvenanceRecord(
        kind="generated",
        source="MathformerKB generated common theorem seed list",
        retrieved_at=now(),
        confidence="medium",
    )
    entries = []
    for record in records:
        entry = KBEntry(
            id=record["id"],
            status="generated_candidate",
            domain_tags=record["domain_tags"],
            informal_statement=record["informal"],
            latex_statement=record["latex"],
            formal_statements=[
                FormalSurface(
                    system="tptp", statement=record["formal"], status="candidate"
                )
            ],
            symbols=record["symbols"],
            theorem_shape=sorted(infer_theorem_shape(record["formal"])),
            provenance=[provenance],
        )
        entries.append(populate_canonical_fields(entry))
    return entries


def entries_from_vampire_artifacts(
    root: Path, *, limit: int | None = None
) -> list[KBEntry]:
    """Document the responsibility of ``entries_from_vampire_artifacts``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``entries_from_vampire_artifacts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    reports = sorted(root.rglob("discovery_report.json"))
    entries: list[KBEntry] = []
    for report_path in reports[:limit]:
        entries.extend(entries_from_vampire_report(report_path))
    return entries


def entries_from_vampire_report(report_path: Path) -> list[KBEntry]:
    """Document the responsibility of ``entries_from_vampire_report``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``entries_from_vampire_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    winner = payload.get("winner") or {}
    formulas = winner.get("formulas") or []
    conjectures = [
        formula for formula in formulas if formula.get("role") == "conjecture"
    ]
    if not conjectures:
        return []
    statement = (
        payload.get("informal_statement") or winner.get("informal_statement") or ""
    )
    status = "proved_formal" if payload.get("ok") else "formal_candidate"
    formal_status = "proved" if payload.get("ok") else "candidate"
    proof_path = payload.get("winning_formal_proof_path")
    problem_path = payload.get("attempts", [{}])[0].get("problem_path")
    domain_tags = _domain_tags_from_report(payload)
    provenance = ProvenanceRecord(
        kind="local_artifact",
        source=str(report_path),
        retrieved_at=now(),
        confidence="high" if payload.get("ok") else "medium",
    )
    entries: list[KBEntry] = []
    for formula in conjectures:
        formal_statement = str(formula["formula"])
        entry = KBEntry(
            id=_entry_id_from_report(payload, formal_statement),
            status=status,
            domain_tags=domain_tags,
            informal_statement=statement or f"TPTP conjecture from {report_path}",
            formal_statements=[
                FormalSurface(
                    system="tptp",
                    statement=formal_statement,
                    status=formal_status,
                    proof_artifact=proof_path,
                    source_artifact=problem_path,
                )
            ],
            theorem_shape=sorted(infer_theorem_shape(formal_statement)),
            provenance=[provenance],
        )
        entries.append(populate_canonical_fields(entry))
    return entries


def entries_from_jsonl_corpus(
    path: Path, *, provenance_kind: str = "corpus"
) -> list[KBEntry]:
    """Document the responsibility of ``entries_from_jsonl_corpus``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``entries_from_jsonl_corpus`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    entries: list[KBEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        entry_id = payload.get("id") or stable_id_from_statement(
            "corpus", payload["informal_statement"]
        )
        formal_payloads = payload.get("formal_statements", [])
        formal_surfaces = [
            FormalSurface(
                system=item["system"],
                statement=item["statement"],
                status=item.get("status", "candidate"),
                proof_artifact=item.get("proof_artifact"),
                source_artifact=item.get("source_artifact"),
            )
            for item in formal_payloads
        ]
        provenance = ProvenanceRecord(
            kind=provenance_kind,
            source=str(path),
            retrieved_at=now(),
            confidence=payload.get("confidence", "medium"),
        )
        entry = KBEntry(
            id=entry_id,
            status=payload.get("status", "source_backed_candidate"),
            domain_tags=list(payload.get("domain_tags", [])),
            informal_statement=payload["informal_statement"],
            latex_statement=payload.get("latex_statement"),
            formal_statements=formal_surfaces,
            symbols=list(payload.get("symbols", [])),
            theorem_shape=list(payload.get("theorem_shape", [])),
            provenance=[provenance],
            notes=payload.get("notes"),
        )
        entries.append(populate_canonical_fields(entry))
    return entries


def _domain_tags_from_report(payload: dict[str, object]) -> list[str]:
    """Document the responsibility of ``_domain_tags_from_report``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_domain_tags_from_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = json.dumps(payload).lower()
    tags: set[str] = set()
    if "group" in text or "mul(" in text or "inv(" in text:
        tags.update({"algebra", "group", "equality"})
    if "subset" in text or "member" in text:
        tags.update({"set", "membership", "first_order"})
    if "relation" in text or "irreflexive" in text or "asymmetric" in text:
        tags.update({"relation", "first_order"})
    return sorted(tags or {"first_order"})


def _entry_id_from_report(payload: dict[str, object], formal_statement: str) -> str:
    """Document the responsibility of ``_entry_id_from_report``.

    Motivation:
        Make reusable mathematical facts searchable before they are trusted as proof premises.

    Intent:
        Provide the local operation named ``_entry_id_from_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    winner = payload.get("winner") or {}
    if isinstance(winner, dict) and winner.get("problem_id"):
        return f"vampire.{winner['problem_id']}"
    return stable_id_from_statement("vampire", formal_statement)

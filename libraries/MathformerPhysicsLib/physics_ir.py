# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Versioned backend-neutral representation of a physics derivation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence


IR_SCHEMA_VERSION = 1


def stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True)
class Quantity:
    quantity_id: str
    role: str
    dimension: str
    unit: str
    domain: str = "real"


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    statement: str
    provenance: str = "source"


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    kind: str
    claim: str
    source_anchors: tuple[str, ...] = ()
    generated_support: bool = False
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectionBridge:
    bridge_id: str
    source_surface: str
    target_surface: str
    policy: str


@dataclass(frozen=True)
class PhysicsDerivationIR:
    case_id: str
    source_digest: str
    statement_nl: str
    statement_latex: str
    target_claim: str
    quantities: tuple[Quantity, ...]
    assumptions: tuple[Assumption, ...]
    obligations: tuple[Obligation, ...]
    coordinate_frame: Mapping[str, Any] = field(default_factory=dict)
    regimes: tuple[str, ...] = ()
    source_laws: tuple[str, ...] = ()
    projection_bridges: tuple[ProjectionBridge, ...] = ()
    schema_version: int = IR_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def ir_digest(self) -> str:
        return stable_digest(self.to_dict())


def _slug(value: str, fallback: str) -> str:
    normalized = "".join(character.lower() if character.isalnum() else "_" for character in value)
    normalized = "_".join(part for part in normalized.split("_") if part)
    return normalized[:80] or fallback


def from_case_spec(
    case_id: str,
    spec: Mapping[str, Any],
    *,
    steps: Sequence[Mapping[str, Any]] = (),
    projection_bridges: Sequence[Mapping[str, Any]] = (),
) -> PhysicsDerivationIR:
    """Convert a source/case record into the common semantic contract."""

    statement_nl = str(spec.get("statement_nl") or "")
    statement_latex = str(spec.get("statement_latex") or "")
    source_anchors = tuple(str(item) for item in spec.get("source_anchors", []) if str(item))
    source_digest = stable_digest(
        {
            "case_id": case_id,
            "statement_nl": statement_nl,
            "statement_latex": statement_latex,
            "source_anchors": source_anchors,
        }
    )
    quantities = tuple(
        Quantity(
            quantity_id=str(symbol),
            role=str(values[0]) if isinstance(values, (list, tuple)) and len(values) > 0 else str(symbol),
            dimension=str(values[1]) if isinstance(values, (list, tuple)) and len(values) > 1 else "unknown",
            unit=str(values[2]) if isinstance(values, (list, tuple)) and len(values) > 2 else "unknown",
        )
        for symbol, values in sorted((spec.get("quantities") or {}).items())
    )
    assumptions = tuple(
        Assumption(
            assumption_id=f"assumption_{index:03d}_{_slug(str(statement), 'context')}",
            statement=str(statement),
        )
        for index, statement in enumerate(spec.get("assumptions") or (), start=1)
    )
    obligations = tuple(
        Obligation(
            obligation_id=str(step.get("id") or f"obligation_{index:03d}"),
            kind=str(step.get("kind") or "derivation_step"),
            claim=str(step.get("expression") or step.get("claim") or ""),
            source_anchors=tuple(str(item) for item in step.get("source_anchors", source_anchors)),
            generated_support=bool(step.get("generated") or step.get("generated_support")),
            depends_on=(str(steps[index - 2].get("id")),) if index > 1 and steps[index - 2].get("id") else (),
        )
        for index, step in enumerate(steps, start=1)
    )
    bridges = tuple(
        ProjectionBridge(
            bridge_id=str(item.get("id") or item.get("bridge_id") or f"projection_{index:03d}"),
            source_surface=str(item.get("source_surface") or item.get("source") or "source_claim"),
            target_surface=str(item.get("target_surface") or item.get("target") or "backend_claim"),
            policy=str(item.get("policy") or "explicit_projection"),
        )
        for index, item in enumerate(projection_bridges, start=1)
    )
    return PhysicsDerivationIR(
        case_id=case_id,
        source_digest=source_digest,
        statement_nl=statement_nl,
        statement_latex=statement_latex,
        target_claim=str(spec.get("target") or statement_latex or statement_nl),
        quantities=quantities,
        assumptions=assumptions,
        obligations=obligations,
        coordinate_frame=dict(spec.get("frame") or {}),
        regimes=tuple(str(item) for item in spec.get("regimes") or ()),
        source_laws=tuple(str(item) for item in spec.get("laws") or ()),
        projection_bridges=bridges,
    )


def validate_ir(ir: PhysicsDerivationIR) -> list[str]:
    errors: list[str] = []
    if ir.schema_version != IR_SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {ir.schema_version}")
    if not ir.case_id:
        errors.append("case_id is required")
    if not ir.source_digest:
        errors.append("source_digest is required")
    quantity_ids = [item.quantity_id for item in ir.quantities]
    obligation_ids = [item.obligation_id for item in ir.obligations]
    if len(quantity_ids) != len(set(quantity_ids)):
        errors.append("quantity ids must be unique")
    if len(obligation_ids) != len(set(obligation_ids)):
        errors.append("obligation ids must be unique")
    for quantity in ir.quantities:
        if quantity.dimension == "unknown" or quantity.unit == "unknown":
            errors.append(f"quantity {quantity.quantity_id} lacks dimension or unit semantics")
    known_obligations = set(obligation_ids)
    for obligation in ir.obligations:
        missing = sorted(set(obligation.depends_on) - known_obligations)
        if missing:
            errors.append(f"obligation {obligation.obligation_id} has unknown dependencies: {missing}")
    return errors


def backend_packet(
    ir: PhysicsDerivationIR,
    *,
    backend: str,
    artifact_path: str,
    encoded_assumption_ids: Iterable[str] | None = None,
    encoded_obligation_ids: Iterable[str] | None = None,
    intentional_projections: Iterable[str] = (),
    artifact_digest: str | None = None,
) -> dict[str, Any]:
    """Bind one backend artifact to the authoritative IR."""

    assumption_ids = (
        sorted(set(encoded_assumption_ids))
        if encoded_assumption_ids is not None
        else sorted(item.assumption_id for item in ir.assumptions)
    )
    obligation_ids = (
        sorted(set(encoded_obligation_ids))
        if encoded_obligation_ids is not None
        else sorted(item.obligation_id for item in ir.obligations)
    )
    return {
        "schema_version": 1,
        "style": "physics_backend_semantic_packet",
        "backend": backend,
        "case_id": ir.case_id,
        "source_digest": ir.source_digest,
        "ir_digest": ir.ir_digest,
        "artifact_path": artifact_path,
        "artifact_digest": artifact_digest,
        "quantity_roles": {item.quantity_id: item.role for item in ir.quantities},
        "assumption_ids": assumption_ids,
        "obligation_ids": obligation_ids,
        "projection_policy": sorted(set(intentional_projections)),
        "target_claim": ir.target_claim,
    }


def compare_backend_packets(packets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compare semantics while keeping backend coverage separate from parity."""

    findings: list[dict[str, Any]] = []
    if not packets:
        return {"schema_version": 1, "coverage_ok": False, "semantic_parity": False, "findings": [{"code": "no_packets"}]}
    baseline = packets[0]
    fields = ("case_id", "source_digest", "ir_digest", "quantity_roles", "assumption_ids", "obligation_ids", "target_claim")
    for packet in packets[1:]:
        for field_name in fields:
            if packet.get(field_name) != baseline.get(field_name):
                findings.append(
                    {
                        "severity": "high",
                        "code": f"cross_backend_{field_name}_mismatch",
                        "field": field_name,
                        "baseline_backend": baseline.get("backend"),
                        "backend": packet.get("backend"),
                        "baseline": baseline.get(field_name),
                        "observed": packet.get(field_name),
                    }
                )
    return {
        "schema_version": 1,
        "coverage_ok": len({str(item.get("backend")) for item in packets}) == len(packets),
        "semantic_parity": not findings,
        "backend_count": len(packets),
        "backends": sorted(str(item.get("backend")) for item in packets),
        "findings": findings,
    }

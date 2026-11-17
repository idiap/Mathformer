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

"""Review an expanded informal physics derivation packet for readiness."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Sequence

STYLE = "physics_informal_derivation_readiness_report"


def load_packet(path: Path | None, text: str | None) -> dict[str, Any]:
    """Document the responsibility of ``load_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if text is not None:
        return json.loads(text)
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def finding(
    severity: str,
    code: str,
    message: str,
    *,
    step_id: str | None = None,
    refinement_target: str,
    remediation: str,
    locality: str,
) -> dict[str, str]:
    """Document the responsibility of ``finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    item = {
        "severity": severity,
        "code": code,
        "message": message,
        "refinement_target": refinement_target,
        "remediation": remediation,
        "locality": locality,
    }
    if step_id is not None:
        item["step_id"] = step_id
    return item


def review_packet(packet: dict[str, Any], case_id: str) -> dict[str, Any]:
    """Document the responsibility of ``review_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``review_packet`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    steps = packet.get("steps")
    if not isinstance(steps, list):
        steps = []
    expected_grounding = packet.get("expected_grounding_summary", {})
    handoff = packet.get("handoff", [])
    findings = []
    if not steps:
        findings.append(
            finding(
                "high",
                "no_steps",
                "No source-anchored derivation steps found.",
                refinement_target="physics.informal.expand",
                remediation="Rebuild the informal expansion packet from the original source text before backend drafting.",
                locality="packet-level regeneration; do not draft formal code from an empty packet",
            )
        )
    if expected_grounding.get("status") not in {"expected", "not_required"}:
        findings.append(
            finding(
                "high",
                "missing_expected_grounding_summary",
                "Expanded informal packet does not state the expected formal grounding before backend drafting.",
                refinement_target="physics.informal.expand",
                remediation="Annotate expected Mathlib surfaces, definitions, background lemmas, unit bridges, and algebraic cores.",
                locality="add packet metadata and per-step grounding annotations only",
            )
        )
    grounding_roles = (
        set(expected_grounding.get("roles", []))
        if isinstance(expected_grounding.get("roles"), list)
        else set()
    )
    if grounding_roles and "dependency.resolve" not in handoff:
        findings.append(
            finding(
                "high",
                "dependency_resolution_handoff_missing",
                "Expected grounding roles are present but dependency.resolve is not in the handoff.",
                refinement_target="dependency.resolve",
                remediation="Route expected definitions and background results through the dependency resolver before theorem drafting.",
                locality="append the dependency handoff; preserve existing source steps",
            )
        )
    for step in steps:
        step_id = step.get("step_id", "unknown")
        is_context = step.get("formalization_role") == "context"
        if not step.get("source_anchor"):
            findings.append(
                finding(
                    "high",
                    "missing_source_anchor",
                    "Step has no source anchor.",
                    step_id=step_id,
                    refinement_target="physics.informal.expand",
                    remediation="Attach a Source line/span anchor or mark the statement as generated support with a transition anchor.",
                    locality="edit only this step's anchor metadata",
                )
            )
        if step.get("support_status") == "generated_support_needed":
            findings.append(
                finding(
                    "high",
                    "generated_support_unreviewed",
                    "Generated bridge step has not been reviewed or discharged.",
                    step_id=step_id,
                    refinement_target="physics.informal.expand",
                    remediation="Expand this bridge into a source-aligned local derivation or create a support lemma for it.",
                    locality="add/prove this bridge only; do not rewrite adjacent source-anchored steps",
                )
            )
        hints = step.get("law_or_rule_hints") or []
        if not is_context and (
            not hints
            or hints == ["unresolved law or algebraic rule"]
            or hints == ["unresolved transition rule"]
        ):
            findings.append(
                finding(
                    "high",
                    "missing_law_or_rule_provenance",
                    "Candidate derivation step lacks a usable law or rule provenance hint.",
                    step_id=step_id,
                    refinement_target="physics.laws.ground",
                    remediation="Identify the physics law, calculus rule, algebraic transformation, or source-backed definition that justifies this step.",
                    locality="add provenance for this step without changing the source statement",
                )
            )
        if not is_context and step.get("dimension_unit_status") in {
            None,
            "",
            "needs_check",
        }:
            findings.append(
                finding(
                    "medium",
                    "dimension_unit_needs_check",
                    "Candidate derivation step needs unit/dimension review before formal theorem acceptance.",
                    step_id=step_id,
                    refinement_target="physics.units.check",
                    remediation="Run or attach a unit/dimension homogeneity check for this step.",
                    locality="record a unit result for this step; do not alter unrelated steps",
                )
            )
        if not is_context and not step.get("expected_formal_grounding"):
            findings.append(
                finding(
                    "high",
                    "missing_step_expected_grounding",
                    "Candidate derivation step has no expected formal grounding annotation.",
                    step_id=step_id,
                    refinement_target="physics.informal.expand",
                    remediation="Add per-step expected grounding roles and target formal object kinds.",
                    locality="annotate this step only",
                )
            )
        roles = step.get("expected_grounding_roles") or []
        if any(
            role in roles
            for role in [
                "calculus_support",
                "source_law_support",
                "unit_dimension_bridge",
                "algebraic_core",
            ]
        ) and not step.get("law_or_rule_hints"):
            findings.append(
                finding(
                    "high",
                    "grounding_role_without_rule_hint",
                    "A formal grounding role requires a law/rule hint, but none was provided.",
                    step_id=step_id,
                    refinement_target="physics.laws.ground",
                    remediation="Add the law/rule hint matching the expected grounding role.",
                    locality="add hints to this step only",
                )
            )
    severity_order = {"high": 3, "medium": 2, "low": 1}
    max_severity = max(
        (severity_order.get(item["severity"], 0) for item in findings), default=0
    )
    verdict = "pass" if max_severity == 0 else "fail" if max_severity >= 3 else "block"
    return {
        "style": STYLE,
        "case_id": case_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "step_count": len(steps),
        "findings": findings,
        "finding_summary": dict(Counter(item["code"] for item in findings)),
        "reviewed_grounding": {
            "expected_grounding_status": expected_grounding.get("status", "missing"),
            "expected_grounding_roles": sorted(grounding_roles),
            "dependency_resolution_handoff": "dependency.resolve" in handoff,
        },
        "handoff": (
            []
            if verdict == "pass"
            else [
                "physics.informal.expand",
                "preformalization.expansion_web_support",
                "dependency.resolve",
            ]
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-file", type=Path)
    parser.add_argument("--packet-json")
    parser.add_argument("--case-id", default="physics_informal_case")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    if args.self_test:
        packet = {
            "steps": [
                {
                    "step_id": "G1",
                    "source_anchor": "S1->S2",
                    "support_status": "generated_support_needed",
                    "law_or_rule_hints": ["unresolved transition rule"],
                    "dimension_unit_status": "needs_check",
                }
            ]
        }
        report = review_packet(packet, "self_test")
        assert report["style"] == STYLE
        assert report["verdict"] == "fail"
        assert report["findings"][0]["remediation"]
        assert report["finding_summary"]["missing_expected_grounding_summary"] == 1
        good_packet = {
            "expected_grounding_summary": {
                "status": "expected",
                "roles": ["algebraic_core"],
            },
            "handoff": ["dependency.resolve"],
            "steps": [
                {
                    "step_id": "S1",
                    "source_anchor": "Source:1",
                    "support_status": "literal_source",
                    "law_or_rule_hints": ["calculus transformation"],
                    "dimension_unit_status": "checked",
                    "formalization_role": "candidate_derivation_step",
                    "expected_grounding_roles": ["algebraic_core"],
                    "expected_formal_grounding": [{"role": "algebraic_core"}],
                }
            ],
        }
        good_report = review_packet(good_packet, "self_test_good")
        assert good_report["verdict"] == "pass", good_report
        print(json.dumps({"ok": True, "style": STYLE}, indent=2))
        return 0
    packet = load_packet(args.packet_file, args.packet_json)
    report = review_packet(packet, args.case_id)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

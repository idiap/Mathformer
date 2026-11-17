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

"""Validate web-sourced mathlib grounding packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

SKILL_NAME = "mathlib-web-evidence-validator"
HOOK_ID = "mathlib.web_evidence"

API_CLAIM_TYPES = {
    "api_convention",
    "declaration",
    "import",
    "module",
    "namespace",
    "notation",
    "theorem_shape",
}

OFFICIAL_DOC_HOSTS = {"leanprover-community.github.io"}
OFFICIAL_SOURCE_HOSTS = {"github.com", "raw.githubusercontent.com"}
RETRIEVAL_AID_HOSTS = {"loogle.lean-lang.org", "leansearch.net"}
OFFICIAL_SOURCE_KINDS = {"official_docs", "official_source"}


def make_finding(
    severity: str,
    code: str,
    message: str,
    *,
    claim_index: Optional[int] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``make_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    finding: Dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if claim_index is not None:
        finding["claim_index"] = claim_index
    if url is not None:
        finding["url"] = url
    return finding


def classify_url(url: str) -> str:
    """Document the responsibility of ``classify_url``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_url`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path
    if host in OFFICIAL_DOC_HOSTS and "/mathlib4_docs" in path:
        return "official_docs"
    if host == "github.com" and path.startswith("/leanprover-community/mathlib4"):
        return "official_source"
    if host == "raw.githubusercontent.com" and path.startswith(
        "/leanprover-community/mathlib4"
    ):
        return "official_source"
    if host in RETRIEVAL_AID_HOSTS:
        return "retrieval_aid"
    return "unknown"


def is_local_verified(value: Any) -> bool:
    """Document the responsibility of ``is_local_verified``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_local_verified`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not isinstance(value, dict):
        return False
    if value.get("check_ok") is True:
        return True
    if value.get("compile_ok") is True:
        return True
    if value.get("verified") is True:
        return True
    if str(value.get("status", "")).lower() in {"ok", "passed", "verified"}:
        return True
    return False


def source_map(packet: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Document the responsibility of ``source_map``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_map`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result: Dict[str, Dict[str, Any]] = {}
    for source in packet.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = source.get("id")
        if isinstance(source_id, str) and source_id:
            result[source_id] = source
    return result


def resolve_claim_source(
    claim: Dict[str, Any],
    sources: Dict[str, Dict[str, Any]],
) -> Tuple[str, str]:
    """Document the responsibility of ``resolve_claim_source``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``resolve_claim_source`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    source_url = claim.get("source_url")
    declared_kind = claim.get("source_kind")
    source_id = claim.get("source_id")
    if isinstance(source_id, str) and source_id in sources:
        source = sources[source_id]
        source_url = source.get("url", source_url)
        declared_kind = source.get("source_kind", declared_kind)
    if not isinstance(source_url, str):
        source_url = ""
    if not isinstance(declared_kind, str) or not declared_kind:
        declared_kind = classify_url(source_url) if source_url else "unknown"
    return source_url, declared_kind


def optional_url(value: Any) -> str:
    """Document the responsibility of ``optional_url``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``optional_url`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return value if isinstance(value, str) else ""


def validate_packet(
    packet: Dict[str, Any], *, allow_unverified: bool = False
) -> Dict[str, Any]:
    """Document the responsibility of ``validate_packet``.

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
    claims = packet.get("claims")
    if not isinstance(claims, list) or not claims:
        findings.append(
            make_finding(
                "high",
                "missing_claims",
                "Evidence packet must contain a non-empty claims list.",
            )
        )
        claims = []

    sources = source_map(packet)
    claim_statuses: List[Dict[str, Any]] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            findings.append(
                make_finding(
                    "high",
                    "malformed_claim",
                    "Claim is not an object.",
                    claim_index=index,
                )
            )
            continue
        claim_type = str(claim.get("claim_type") or "unknown")
        source_url, declared_kind = resolve_claim_source(claim, sources)
        actual_kind = classify_url(source_url) if source_url else "unknown"
        source_kind = actual_kind if actual_kind != "unknown" else declared_kind
        official_corroboration_url = optional_url(
            claim.get("official_corroboration_url")
        )
        official_corroboration_kind = (
            classify_url(official_corroboration_url)
            if official_corroboration_url
            else ""
        )
        has_official_source = (
            source_kind in OFFICIAL_SOURCE_KINDS
            or official_corroboration_kind in OFFICIAL_SOURCE_KINDS
        )
        is_api_claim = claim_type in API_CLAIM_TYPES
        local_verified = is_local_verified(claim.get("local_verification"))
        status = "grounded" if local_verified else "needs_local_verification"

        if not source_url:
            findings.append(
                make_finding(
                    "high",
                    "missing_source_url",
                    "Claim is missing source_url or resolvable source_id.",
                    claim_index=index,
                )
            )
            status = "blocked"
        elif is_api_claim and not has_official_source:
            findings.append(
                make_finding(
                    "high",
                    "api_claim_without_official_source",
                    "Mathlib API claims require official docs or official source evidence.",
                    claim_index=index,
                    url=source_url,
                )
            )
            status = "blocked"
        if source_kind == "retrieval_aid":
            if not official_corroboration_url:
                findings.append(
                    make_finding(
                        "medium",
                        "retrieval_aid_without_corroboration",
                        "Retrieval aids may discover candidates but need official corroboration.",
                        claim_index=index,
                        url=source_url,
                    )
                )
                status = "blocked" if is_api_claim else "needs_official_corroboration"
            elif official_corroboration_kind not in OFFICIAL_SOURCE_KINDS:
                findings.append(
                    make_finding(
                        "high",
                        "official_corroboration_url_not_official",
                        "The corroboration URL must point to official mathlib docs or source.",
                        claim_index=index,
                        url=official_corroboration_url,
                    )
                )
                status = "blocked"

        if is_api_claim and not local_verified:
            severity = "medium" if allow_unverified else "high"
            findings.append(
                make_finding(
                    severity,
                    "missing_local_verification",
                    "API claim has not been locally verified with Lean/import-context checks.",
                    claim_index=index,
                    url=source_url or None,
                )
            )
            if not allow_unverified:
                status = "blocked"
        if is_api_claim and not claim.get("evidence_summary"):
            findings.append(
                make_finding(
                    "medium",
                    "missing_evidence_summary",
                    "API claims should include a short source-backed evidence summary.",
                    claim_index=index,
                    url=source_url or None,
                )
            )
        if (
            is_api_claim
            and claim_type == "declaration"
            and not claim.get("declaration")
        ):
            findings.append(
                make_finding(
                    "medium",
                    "missing_declaration_name",
                    "Declaration claims should name the declaration to #check.",
                    claim_index=index,
                )
            )
        if (
            is_api_claim
            and claim_type in {"import", "module"}
            and not claim.get("module")
        ):
            findings.append(
                make_finding(
                    "medium",
                    "missing_module_name",
                    "Import/module claims should name the Mathlib module.",
                    claim_index=index,
                )
            )
        if not claim.get("query"):
            findings.append(
                make_finding(
                    "low",
                    "missing_query_provenance",
                    "Claim should record the search query or retrieval path.",
                    claim_index=index,
                )
            )

        claim_statuses.append(
            {
                "claim_index": index,
                "claim_type": claim_type,
                "status": status,
                "source_kind": source_kind,
                "source_url": source_url,
                "official_source_available": has_official_source,
                "official_corroboration_url": official_corroboration_url,
                "official_corroboration_kind": official_corroboration_kind,
                "local_verified": local_verified,
            }
        )

    blocking = [item for item in findings if item["severity"] == "high"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking,
        "summary": {
            "claim_count": len(claims),
            "grounded_claim_count": sum(
                1 for item in claim_statuses if item["status"] == "grounded"
            ),
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
        },
        "claim_statuses": claim_statuses,
        "findings": findings,
    }


def self_test() -> Dict[str, Any]:
    """Document the responsibility of ``self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    good_packet = {
        "claims": [
            {
                "claim_type": "declaration",
                "claim": "Function.Injective is a mathlib declaration.",
                "source_url": "https://leanprover-community.github.io/mathlib4_docs/Mathlib/Logic/Function/Basic.html",
                "query": 'site:leanprover-community.github.io/mathlib4_docs "Function.Injective"',
                "evidence_summary": "Official mathlib docs/source corroborates the declaration.",
                "declaration": "Function.Injective",
                "module": "Mathlib.Logic.Function.Basic",
                "local_verification": {"method": "#check", "check_ok": True},
            }
        ]
    }
    retrieval_with_corroboration_packet = {
        "claims": [
            {
                "claim_type": "declaration",
                "claim": "CompactSpace is a mathlib declaration discovered through a retrieval aid.",
                "source_url": "https://loogle.lean-lang.org/?q=CompactSpace",
                "official_corroboration_url": (
                    "https://leanprover-community.github.io/mathlib4_docs/"
                    "Mathlib/Topology/Compactness/Compact.html"
                ),
                "query": "CompactSpace",
                "evidence_summary": "Official mathlib docs corroborate the retrieval-aid candidate.",
                "declaration": "CompactSpace",
                "module": "Mathlib.Topology.Compactness.Compact",
                "local_verification": {"method": "#check", "check_ok": True},
            }
        ]
    }
    bad_packet = {
        "claims": [
            {
                "claim_type": "declaration",
                "claim": "SomeBlogDecl is in mathlib.",
                "source_url": "https://example.com/mathlib-notes",
                "query": "SomeBlogDecl mathlib",
                "evidence_summary": "Unsupported external page claims the declaration exists.",
                "declaration": "SomeBlogDecl",
            }
        ]
    }
    retrieval_only_packet = {
        "claims": [
            {
                "claim_type": "declaration",
                "claim": "CompactSpace is a mathlib declaration discovered through Loogle only.",
                "source_url": "https://loogle.lean-lang.org/?q=CompactSpace",
                "query": "CompactSpace",
                "evidence_summary": "Retrieval aid produced a candidate.",
                "declaration": "CompactSpace",
                "local_verification": {"method": "#check", "check_ok": True},
            }
        ]
    }
    good = validate_packet(good_packet)
    retrieval_with_corroboration = validate_packet(retrieval_with_corroboration_packet)
    bad = validate_packet(bad_packet)
    retrieval_only = validate_packet(retrieval_only_packet)
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": (
            good["ok"]
            and retrieval_with_corroboration["ok"]
            and not bad["ok"]
            and not retrieval_only["ok"]
        ),
        "good": good,
        "retrieval_with_corroboration": retrieval_with_corroboration,
        "bad": bad,
        "retrieval_only": retrieval_only,
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
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
    parser.add_argument("--packet", type=Path, help="JSON evidence packet to validate.")
    parser.add_argument("--text", help="Inline JSON evidence packet.")
    parser.add_argument("--allow-unverified", action="store_true")
    parser.add_argument("--expect-blocking", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def load_packet(args: argparse.Namespace) -> Dict[str, Any]:
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
    if args.packet:
        parsed = json.loads(args.packet.read_text(encoding="utf-8"))
    elif args.text:
        parsed = json.loads(args.text)
    else:
        raise SystemExit("--packet, --text, or --self-test is required")
    if not isinstance(parsed, dict):
        raise SystemExit("packet must be a JSON object")
    return parsed


def render_text(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        f"ok: {report['ok']}",
        f"claims: {report.get('summary', {}).get('claim_count', 0)}",
        f"grounded: {report.get('summary', {}).get('grounded_claim_count', 0)}",
        f"findings: {report.get('summary', {}).get('finding_count', 0)}",
    ]
    for finding in report.get("findings", []):
        lines.append(f"! {finding['severity']} {finding['code']}: {finding['message']}")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
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
        report = self_test()
    else:
        report = validate_packet(
            load_packet(args), allow_unverified=args.allow_unverified
        )
    if args.expect_blocking and report.get("ok"):
        report = dict(report)
        report["ok"] = False
        report.setdefault("findings", []).append(
            make_finding(
                "high",
                "expected_blocking_but_passed",
                "Expected blocking findings, but validation passed.",
            )
        )
    elif args.expect_blocking and not report.get("ok"):
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(render_text(report))
        return 0
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report.get("ok") else 3


if __name__ == "__main__":
    sys.exit(main())

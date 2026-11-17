#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Give Mathformer papers a deterministic first-pass audit for unsupported
#   claims introduced while documenting new platform functionality.
#
# Intent:
#   Detect common observability overclaims, missing packet paths, and missing
#   figure/table source references before a human paper review.
#
# Function:
#   Scans LaTeX or Markdown text and an optional evidence packet, then emits a
#   JSON audit report with severity-ranked findings.
#
# Maintenance Notes:
#   This is a conservative lint-style check. It complements, but does not
#   replace, the paper-claim-evidence-auditor skill.

"""Audit paper claims against new-functionality evidence packets."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]

OVERCLAIM_PATTERNS = [
    (
        "dashboard_correctness_overclaim",
        re.compile(
            r"\b(?:dashboard|dashboards|HTML dashboard)\b.{0,80}\b(?:prove|proves|certify|certifies|guarantee|guarantees)\b",
            re.IGNORECASE,
        ),
        "Dashboards support inspection claims, not correctness certification.",
    ),
    (
        "rfde_correctness_overclaim",
        re.compile(
            r"\b(?:RFDE|reference-free monitor|monitor plot|monitor plots)\b.{0,80}\b(?:prove|proves|certify|certifies|guarantee|guarantees)\b",
            re.IGNORECASE,
        ),
        "RFDE and monitor plots support trajectory diagnosis, not theorem correctness.",
    ),
    (
        "unqualified_correct_by_construction",
        re.compile(r"\bcorrect by construction\b", re.IGNORECASE),
        "Generated formalizations should not be described as correct by construction.",
    ),
]

CLAIM_KEYWORDS = {
    "observability": ("observability", "inspectable", "inspection"),
    "dashboard/interface": ("dashboard", "HTML", "browser-readable"),
    "workflow-control": ("controlled action", "workflow hub", "registered action"),
    "reasoning-log schema": ("reasoning log", "skill-application", "JSONL"),
    "reference-free monitor": (
        "reference-free monitor",
        "weakest dimension",
        "risk delta",
    ),
}


def read_text(path: Path) -> str:
    """Read UTF-8 text with a clear error if the path is missing."""

    return path.read_text(encoding="utf-8")


def load_packet(path: Path | None) -> dict[str, Any] | None:
    """Load an optional JSON evidence packet."""

    if path is None:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def paper_line_for_offset(text: str, offset: int) -> int:
    """Convert a character offset to a one-based line number."""

    return text.count("\n", 0, offset) + 1


def find_overclaims(text: str) -> list[dict[str, Any]]:
    """Find phrases that turn observability evidence into correctness claims."""

    findings: list[dict[str, Any]] = []
    for finding_id, pattern, message in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(text):
            excerpt = " ".join(match.group(0).split())
            findings.append(
                {
                    "id": finding_id,
                    "severity": "high",
                    "line": paper_line_for_offset(text, match.start()),
                    "message": message,
                    "excerpt": excerpt,
                }
            )
    return findings


def packet_features(packet: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Normalize single-feature and multi-feature packets."""

    if not packet:
        return []
    if "features" in packet:
        return list(packet["features"])
    return [packet]


def audit_packet_paths(packet: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Report missing implementation or artifact paths in the evidence packet."""

    if not packet:
        return []
    missing = packet.get("missing_paths", [])
    if not missing:
        return []
    return [
        {
            "id": "missing_packet_path",
            "severity": "medium",
            "line": None,
            "message": "Evidence packet references paths that are absent in this checkout.",
            "paths": missing,
        }
    ]


def audit_feature_mentions(
    text: str, packet: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Check that paper text mentioning a feature also cites concrete artifacts."""

    findings: list[dict[str, Any]] = []
    for claim_type, keywords in CLAIM_KEYWORDS.items():
        if any(keyword.lower() in text.lower() for keyword in keywords):
            has_repo_path = bool(re.search(r"\\repo\{[^}]+\}", text)) or "`" in text
            if not has_repo_path:
                findings.append(
                    {
                        "id": "claim_without_artifact_path",
                        "severity": "medium",
                        "line": None,
                        "message": f"Paper mentions {claim_type} concepts without visible artifact path syntax.",
                    }
                )
    if packet and "packet_type" not in packet:
        findings.append(
            {
                "id": "unknown_packet_schema",
                "severity": "low",
                "line": None,
                "message": "Evidence packet has no packet_type field.",
            }
        )
    return findings


def classify_claim_surface(text: str) -> dict[str, int]:
    """Count occurrences of paper-update claim categories."""

    lowered = text.lower()
    return {
        claim_type: sum(lowered.count(keyword.lower()) for keyword in keywords)
        for claim_type, keywords in CLAIM_KEYWORDS.items()
    }


def audit_figure_sources(text: str) -> list[dict[str, Any]]:
    """Check includegraphics targets that look repo-local."""

    findings: list[dict[str, Any]] = []
    for match in re.finditer(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", text):
        target = match.group(1)
        candidates = [
            REPO_ROOT / target,
            REPO_ROOT / "paper" / target,
            REPO_ROOT / "paper" / "figures" / target,
        ]
        if not any(candidate.exists() for candidate in candidates):
            findings.append(
                {
                    "id": "missing_figure_source",
                    "severity": "medium",
                    "line": paper_line_for_offset(text, match.start()),
                    "message": "Figure include path could not be resolved locally.",
                    "path": target,
                }
            )
    return findings


def main() -> int:
    """Run the paper-claim audit and write an optional JSON report."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", required=True, help="Paper or doc file to audit.")
    parser.add_argument("--evidence-packet", help="Optional evidence packet JSON.")
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument("--json", action="store_true", help="Print the report as JSON.")
    args = parser.parse_args()

    paper_path = Path(args.paper)
    if not paper_path.is_absolute():
        paper_path = REPO_ROOT / paper_path
    packet_path = Path(args.evidence_packet) if args.evidence_packet else None
    if packet_path is not None and not packet_path.is_absolute():
        packet_path = REPO_ROOT / packet_path

    text = read_text(paper_path)
    packet = load_packet(packet_path)
    findings = []
    findings.extend(find_overclaims(text))
    findings.extend(audit_packet_paths(packet))
    findings.extend(audit_feature_mentions(text, packet))
    findings.extend(audit_figure_sources(text))

    severity_rank = {"high": 0, "medium": 1, "low": 2}
    findings.sort(
        key=lambda item: (
            severity_rank.get(item["severity"], 9),
            item.get("line") or 10**9,
            item["id"],
        )
    )

    report = {
        "ok": not any(item["severity"] == "high" for item in findings),
        "paper": str(paper_path),
        "evidence_packet": str(packet_path) if packet_path else None,
        "claim_surface_counts": classify_claim_surface(text),
        "feature_count": len(packet_features(packet)),
        "finding_count": len(findings),
        "findings": findings,
    }

    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = REPO_ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif findings:
        for finding in findings:
            line = f":{finding['line']}" if finding.get("line") else ""
            print(
                f"{finding['severity'].upper()} {finding['id']}{line}: {finding['message']}"
            )
    else:
        print("No claim-audit findings.")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

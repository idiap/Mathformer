#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

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

"""Heuristic Lean4/mathlib compatibility auditor.

This script scans a Lean file for common patterns that reduce interoperability
with mathlib-native objects and APIs. It can optionally run a concrete Lean
check via `lake env lean`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry as append_shared_reasoning_log_entry,
)

DECL_RE = re.compile(
    r"^\s*(?:@[A-Za-z0-9_'.` ]+\s*)*"
    r"(def|theorem|lemma|axiom|structure|class|instance|abbrev|inductive|coinductive)\b"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")


@dataclass
class Finding:
    """Document the responsibility of ``Finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/mathlib-compatibility-auditor/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    severity: str
    code: str
    category: str
    message: str
    line: Optional[int] = None
    suggestion: Optional[str] = None


_REASONING_LOG_COUNTERS: Dict[str, int] = {}
TOP_LEVEL_DECL_RE = re.compile(
    r"^(?:@[A-Za-z0-9_'.` ]+\s*)*"
    r"(def|theorem|lemma|axiom|structure|class|instance|abbrev|inductive|coinductive)\b"
)
TOP_LEVEL_DECL_NAME_RE = re.compile(
    r"^(?:@[A-Za-z0-9_'.` ]+\s*)*"
    r"(def|theorem|lemma|axiom|structure|class|instance|abbrev|inductive|coinductive)\s+"
    r"([A-Za-z0-9_'.`]+)"
)
COMPATIBILITY_WEIGHTS = {"high": 20, "medium": 10, "low": 4, "info": 0}
CRITICAL_REVIEW_WEIGHTS = {"high": 25, "medium": 14, "low": 5, "info": 0}
DIMENSION_NAMES = [
    "compiler_health",
    "documentation_hygiene",
    "mathlib_alignment",
    "interface_design",
    "artifact_substance",
    "placeholder_hygiene",
]
MATHLIB_ABSTRACTION_AUDITOR_SKILL = (
    "mathlib-abstraction-auditor/check_mathlib_compat.py"
)
LEAN_COMPILE_CHECKER_SKILL = "lean-compile-checker/check_mathlib_compat.py"
MATHLIB_ABSTRACTION_AUDIT_HOOK = "audit.compatibility"
LEAN_COMPILE_CHECK_HOOK = "check.compile"


def _jsonable(value: Any) -> Any:
    """Document the responsibility of ``_jsonable``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_jsonable`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return repr(value)


def _file_hash(text: str, *, length: int = 12) -> str:
    """Document the responsibility of ``_file_hash``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_file_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _seed_reasoning_event_counter(path: Path) -> int:
    """Document the responsibility of ``_seed_reasoning_event_counter``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_seed_reasoning_event_counter`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not path.exists():
        return 0
    last_index = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        event_index = parsed.get("event_index")
        if isinstance(event_index, int):
            last_index = max(last_index, event_index)
    return last_index


def append_reasoning_log_entry(
    output_file: str | Path,
    *,
    step: str,
    payload: Dict[str, Any],
) -> Path:
    """Document the responsibility of ``append_reasoning_log_entry``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_reasoning_log_entry`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return append_shared_reasoning_log_entry(output_file, step=step, payload=payload)


def make_reasoning_logger(
    output_file: Path | None,
) -> Callable[[str, Dict[str, Any]], None]:
    """Document the responsibility of ``make_reasoning_logger``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """

    def trace_event(step: str, payload: Dict[str, Any]) -> None:
        """Document the responsibility of ``make_reasoning_logger.trace_event``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Build the local data structure or artifact used by the next workflow stage.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if output_file is None:
            return
        append_reasoning_log_entry(output_file, step=step, payload=payload)

    return trace_event


def _strip_single_line_comment(line: str) -> str:
    """Document the responsibility of ``_strip_single_line_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_strip_single_line_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "--" in line:
        return line.split("--", 1)[0]
    return line


def _has_doc_comment(lines: List[str], decl_idx: int) -> bool:
    """Document the responsibility of ``_has_doc_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_has_doc_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    idx = decl_idx - 1
    while idx >= 0 and lines[idx].strip() == "":
        idx -= 1
    if idx < 0:
        return False

    if "-/" not in lines[idx]:
        return False

    while idx >= 0:
        stripped = lines[idx].strip()
        if "/--" in stripped:
            return True
        if stripped == "":
            return False
        if stripped.startswith("/-") and not stripped.startswith("/--"):
            return False
        idx -= 1
    return False


def _score_band(score: int) -> str:
    """Document the responsibility of ``_score_band``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_score_band`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if score >= 95:
        return "excellent"
    if score >= 85:
        return "good"
    if score >= 70:
        return "moderate"
    return "weak"


def _collect_top_level_declarations(lines: List[str]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``_collect_top_level_declarations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_collect_top_level_declarations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    declarations: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for i, raw in enumerate(lines, start=1):
        if raw.startswith(" ") or raw.startswith("\t"):
            if current is not None:
                current["lines"].append(raw)
            continue

        code_part = _strip_single_line_comment(raw)
        match = TOP_LEVEL_DECL_RE.match(code_part)
        if match is not None:
            if current is not None:
                declarations.append(current)
            name_match = TOP_LEVEL_DECL_NAME_RE.match(code_part)
            current = {
                "kind": match.group(1),
                "name": name_match.group(2) if name_match is not None else None,
                "line": i,
                "lines": [raw],
            }
            continue

        if current is not None:
            current["lines"].append(raw)

    if current is not None:
        declarations.append(current)
    return declarations


def _normalize_declaration_block(block_lines: List[str]) -> str:
    """Document the responsibility of ``_normalize_declaration_block``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_normalize_declaration_block`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cleaned: List[str] = []
    for raw in block_lines:
        code_part = _strip_single_line_comment(raw).strip()
        if not code_part:
            continue
        cleaned.append(code_part)
    return " ".join(cleaned)


def _is_thin_wrapper_declaration(kind: str, block_lines: List[str]) -> bool:
    """Document the responsibility of ``_is_thin_wrapper_declaration``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_is_thin_wrapper_declaration`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if kind not in {"theorem", "lemma", "def", "abbrev"}:
        return False

    block = _normalize_declaration_block(block_lines)
    if ":=" not in block:
        return False

    body = block.split(":=", 1)[1].strip()
    if not body:
        return False

    thin_by_patterns = [
        r"^by exact [A-Za-z0-9_'.]+(?: .*)?$",
        r"^by simpa(?: \[[^\]]*\])? using [A-Za-z0-9_'.]+(?: .*)?$",
        r"^by rwa(?: \[[^\]]*\])? using [A-Za-z0-9_'.]+(?: .*)?$",
        r"^by infer_instance$",
        r"^by rfl$",
    ]
    for pattern in thin_by_patterns:
        if re.match(pattern, body):
            return True

    if body.startswith(("by ", "fun ", "match ", "let ", "calc ", "if ", "show ")):
        return False

    if re.match(r"^[A-Za-z0-9_'.]+(?:\s+[A-Za-z0-9_'.()\[\]{}<>:=,+\-/*]+)*$", body):
        return True

    return False


def _compute_dimension_scores(findings: List[Finding]) -> Dict[str, int]:
    """Document the responsibility of ``_compute_dimension_scores``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_compute_dimension_scores`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    dimension_scores = {name: 100 for name in DIMENSION_NAMES}
    for finding in findings:
        if finding.category not in dimension_scores:
            continue
        deduction = CRITICAL_REVIEW_WEIGHTS.get(finding.severity, 0)
        dimension_scores[finding.category] = max(
            0, dimension_scores[finding.category] - deduction
        )
    return dimension_scores


def _run_lake_check(lean_file: Path, lake_workdir: Path) -> Dict[str, Any]:
    """Document the responsibility of ``_run_lake_check``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    proc = subprocess.run(
        ["lake", "env", "lean", str(lean_file)],
        cwd=str(lake_workdir),
        capture_output=True,
        text=True,
    )
    combined = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
    errors = []
    for line in combined.splitlines():
        if ": error:" in line:
            errors.append(line.strip())
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "error_count": len(errors),
        "errors": errors[:25],
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def audit_file(
    lean_file: Path,
    *,
    run_lake_check: bool,
    lake_workdir: Path,
    trace_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``audit_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``audit_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = lean_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings: List[Finding] = []
    skill_name = MATHLIB_ABSTRACTION_AUDITOR_SKILL

    def log_event(
        step: str,
        payload: Dict[str, Any],
        *,
        skill: str = skill_name,
    ) -> None:
        """Document the responsibility of ``audit_file.log_event``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``audit_file.log_event`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if trace_event is None:
            return
        hook_id = (
            LEAN_COMPILE_CHECK_HOOK
            if skill == LEAN_COMPILE_CHECKER_SKILL
            else MATHLIB_ABSTRACTION_AUDIT_HOOK
        )
        trace_event(step, {"skill": skill, "hook_id": hook_id, **payload})

    def record_finding(
        finding: Finding,
        *,
        source: str,
        skill: str = skill_name,
    ) -> None:
        """Document the responsibility of ``audit_file.record_finding``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Search available candidates and return the matches needed by the caller.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        findings.append(finding)
        log_event(
            "compatibility_audit_finding_detected",
            {
                "source": source,
                "finding": asdict(finding),
            },
            skill=skill,
        )

    log_event(
        "compatibility_audit_file_loaded",
        {
            "lean_file": str(lean_file),
            "line_count": len(lines),
            "file_hash": _file_hash(text),
            "run_lake_check": run_lake_check,
            "lake_workdir": str(lake_workdir),
        },
    )

    imports: List[str] = []
    declaration_count = 0
    undocumented_declarations = 0

    for i, raw in enumerate(lines, start=1):
        m_imp = IMPORT_RE.match(raw)
        if m_imp:
            imports.append(m_imp.group(1))

        code_part = _strip_single_line_comment(raw)
        if DECL_RE.search(code_part):
            declaration_count += 1
            if not _has_doc_comment(lines, i - 1):
                undocumented_declarations += 1
                record_finding(
                    Finding(
                        severity="low",
                        code="missing_doc_comment",
                        category="documentation_hygiene",
                        line=i,
                        message="Declaration appears without an immediate `/-- ... -/` doc comment.",
                        suggestion="Add a concise natural-language doc comment directly above this declaration.",
                    ),
                    source="doc_comment_check",
                )

        if re.search(r"\bsorry\b", code_part):
            record_finding(
                Finding(
                    severity="medium",
                    code="sorry_placeholder",
                    category="placeholder_hygiene",
                    line=i,
                    message="Found `sorry` placeholder.",
                    suggestion="Replace `sorry` with a proof or explicitly mark this as interface-only scaffolding.",
                ),
                source="placeholder_scan",
            )
        if re.search(r"\baxiom\b", code_part):
            record_finding(
                Finding(
                    severity="medium",
                    code="axiom_placeholder",
                    category="placeholder_hygiene",
                    line=i,
                    message="Found `axiom` declaration.",
                    suggestion="Prefer theorem/proof or isolate axioms inside explicit assumption packages.",
                ),
                source="placeholder_scan",
            )

    log_event(
        "compatibility_audit_structure_scanned",
        {
            "import_count": len(imports),
            "declaration_count": declaration_count,
            "undocumented_declarations": undocumented_declarations,
        },
    )

    if imports and "Mathlib" in imports:
        record_finding(
            Finding(
                severity="low",
                code="broad_import_mathlib",
                category="mathlib_alignment",
                message="Uses broad `import Mathlib`.",
                suggestion="Trim imports to required modules once interface stabilizes.",
            ),
            source="import_scan",
        )

    has_native_gaussian = "ProbabilityTheory.IsGaussian" in text
    has_custom_gaussian_pred = bool(
        re.search(r"\b(IsGaussianMeasure|IsGaussianMeasureH)\b", text)
    )
    if has_custom_gaussian_pred and not has_native_gaussian:
        record_finding(
            Finding(
                severity="high",
                code="custom_gaussian_predicate",
                category="mathlib_alignment",
                message=(
                    "Custom Gaussian predicate detected without `ProbabilityTheory.IsGaussian`."
                ),
                suggestion=(
                    "Use `ProbabilityTheory.IsGaussian` directly when possible and isolate only the missing cylindrical-extension notion."
                ),
            ),
            source="gaussian_interface_check",
        )

    has_probability_pair = (
        "MeasureTheory.IsProbabilityMeasure" in text
        and "MeasureTheory.ProbabilityMeasure" not in text
    )
    if has_probability_pair:
        record_finding(
            Finding(
                severity="medium",
                code="non_native_probability_encoding",
                category="mathlib_alignment",
                message=(
                    "Uses `IsProbabilityMeasure` without `ProbabilityMeasure` witness type."
                ),
                suggestion=(
                    "Prefer `MeasureTheory.ProbabilityMeasure` as witness type when normalization is part of the interface."
                ),
            ),
            source="probability_interface_check",
        )

    has_basis_indep = "IsHilbertSchmidtBasisIndependent" in text
    basis_indep_uses = len(re.findall(r"\bIsHilbertSchmidtBasisIndependent\b", text))
    if has_basis_indep and basis_indep_uses <= 1:
        record_finding(
            Finding(
                severity="low",
                code="floating_basis_independence",
                category="interface_design",
                message="Basis-independence interface appears unused/weakly connected.",
                suggestion="Connect basis-independence to an operational lemma or remove until used.",
            ),
            source="basis_independence_check",
        )

    abstract_boundary_fields = len(re.findall(r"\bHas[A-Z][A-Za-z0-9_]*\s*:", text))
    if abstract_boundary_fields > 2:
        record_finding(
            Finding(
                severity="medium",
                code="multiple_abstract_boundaries",
                category="interface_design",
                message=(
                    f"Detected {abstract_boundary_fields} `Has...` boundary-style fields; interface may be over-abstracted."
                ),
                suggestion=(
                    "Keep one primary abstract boundary for the genuinely missing notion and concretize the rest with mathlib-native objects."
                ),
            ),
            source="abstraction_boundary_check",
        )

    top_level_declarations = _collect_top_level_declarations(lines)
    substance_declarations = [
        decl
        for decl in top_level_declarations
        if decl["kind"] in {"theorem", "lemma", "def", "abbrev"}
    ]
    thin_wrapper_declarations = [
        decl
        for decl in substance_declarations
        if _is_thin_wrapper_declaration(decl["kind"], decl["lines"])
    ]
    thin_wrapper_ratio = (
        len(thin_wrapper_declarations) / len(substance_declarations)
        if substance_declarations
        else 0.0
    )
    thin_wrapper_names = [
        decl["name"] or f"<anonymous@{decl['line']}>"
        for decl in thin_wrapper_declarations[:5]
    ]
    if len(substance_declarations) >= 3 and thin_wrapper_ratio >= 0.8:
        record_finding(
            Finding(
                severity="medium",
                code="thin_wrapper_heavy_interface",
                category="artifact_substance",
                message=(
                    "Most top-level declarations are thin wrappers around existing results; "
                    "the module may overstate end-to-end formalization depth."
                ),
                suggestion=(
                    "Add source-faithful specializations, nontrivial bridge lemmas, or concrete theorem statements "
                    "instead of only alias-style wrappers."
                ),
            ),
            source="artifact_substance_check",
        )
    elif len(substance_declarations) >= 2 and thin_wrapper_ratio >= 0.5:
        record_finding(
            Finding(
                severity="low",
                code="wrapper_heavy_interface",
                category="artifact_substance",
                message=(
                    "A large share of top-level declarations are thin wrappers around existing results."
                ),
                suggestion=(
                    "Consider adding source-specific specializations or bridge lemmas so the artifact carries more domain substance."
                ),
            ),
            source="artifact_substance_check",
        )

    lake_check = None
    if run_lake_check:
        log_event(
            "compatibility_audit_lake_check_start",
            {
                "lean_file": str(lean_file),
                "lake_workdir": str(lake_workdir),
            },
            skill=LEAN_COMPILE_CHECKER_SKILL,
        )
        lake_check = _run_lake_check(lean_file=lean_file, lake_workdir=lake_workdir)
        log_event(
            "compatibility_audit_lake_check_complete",
            {
                "ok": lake_check["ok"],
                "returncode": lake_check["returncode"],
                "error_count": lake_check["error_count"],
                "errors": lake_check["errors"],
            },
            skill=LEAN_COMPILE_CHECKER_SKILL,
        )
        if not lake_check["ok"]:
            record_finding(
                Finding(
                    severity="high",
                    code="lean_check_failed",
                    category="compiler_health",
                    message=(
                        f"`lake env lean` failed with {lake_check['error_count']} error(s)."
                    ),
                    suggestion="Resolve Lean errors and rerun the compatibility audit.",
                ),
                source="lake_check",
                skill=LEAN_COMPILE_CHECKER_SKILL,
            )

    score = max(
        0, 100 - sum(COMPATIBILITY_WEIGHTS.get(f.severity, 0) for f in findings)
    )
    band = _score_band(score)
    critical_review_score = max(
        0,
        100 - sum(CRITICAL_REVIEW_WEIGHTS.get(f.severity, 0) for f in findings),
    )
    critical_review_band = _score_band(critical_review_score)

    counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    dimension_scores = _compute_dimension_scores(findings)
    dimension_bands = {
        name: _score_band(value) for name, value in dimension_scores.items()
    }

    result = {
        "lean_file": str(lean_file),
        "compatibility_score": score,
        "compatibility_band": band,
        "critical_review_score": critical_review_score,
        "critical_review_band": critical_review_band,
        "summary": {
            "line_count": len(lines),
            "import_count": len(imports),
            "declaration_count": declaration_count,
            "undocumented_declarations": undocumented_declarations,
            "severity_counts": counts,
            "finding_count": len(findings),
            "top_level_declaration_count": len(top_level_declarations),
            "substance_declaration_count": len(substance_declarations),
            "thin_wrapper_declaration_count": len(thin_wrapper_declarations),
            "thin_wrapper_ratio": round(thin_wrapper_ratio, 3),
            "thin_wrapper_examples": thin_wrapper_names,
        },
        "expanded_scores": {
            "critical_review_score": critical_review_score,
            "critical_review_band": critical_review_band,
            "dimension_scores": dimension_scores,
            "dimension_bands": dimension_bands,
        },
        "mathlib_native_presence": {
            "ProbabilityTheory.IsGaussian": "ProbabilityTheory.IsGaussian" in text,
            "MeasureTheory.ProbabilityMeasure": "MeasureTheory.ProbabilityMeasure"
            in text,
            "HilbertBasis": "HilbertBasis" in text,
            "MeasureTheory.IsProbabilityMeasure": "MeasureTheory.IsProbabilityMeasure"
            in text,
        },
        "findings": [asdict(f) for f in findings],
        "lake_check": lake_check,
    }
    log_event(
        "compatibility_audit_complete",
        {
            "compatibility_score": score,
            "compatibility_band": band,
            "critical_review_score": critical_review_score,
            "critical_review_band": critical_review_band,
            "severity_counts": counts,
            "finding_count": len(findings),
            "thin_wrapper_ratio": round(thin_wrapper_ratio, 3),
            "thin_wrapper_declaration_count": len(thin_wrapper_declarations),
        },
    )
    return result


def _print_text_report(report: Dict[str, Any]) -> None:
    """Document the responsibility of ``_print_text_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_print_text_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    print(
        f"[mathlib-compat] score={report['compatibility_score']} "
        f"band={report['compatibility_band']} "
        f"critical_review={report.get('critical_review_score', report['compatibility_score'])} "
        f"critical_band={report.get('critical_review_band', report['compatibility_band'])}"
    )
    summary = report["summary"]
    print(
        "  declarations={decl} undocumented={undoc} imports={imp} findings={finding_count}".format(
            decl=summary["declaration_count"],
            undoc=summary["undocumented_declarations"],
            imp=summary["import_count"],
            finding_count=summary.get("finding_count", len(report.get("findings", []))),
        )
    )
    if "thin_wrapper_declaration_count" in summary:
        print(
            "  top_level={top} substance={substance} thin_wrappers={thin} ratio={ratio}".format(
                top=summary.get("top_level_declaration_count", 0),
                substance=summary.get("substance_declaration_count", 0),
                thin=summary.get("thin_wrapper_declaration_count", 0),
                ratio=summary.get("thin_wrapper_ratio", 0),
            )
        )
    sev = summary["severity_counts"]
    print(
        f"  findings: high={sev.get('high', 0)} medium={sev.get('medium', 0)} "
        f"low={sev.get('low', 0)} info={sev.get('info', 0)}"
    )
    expanded_scores = report.get("expanded_scores")
    if expanded_scores is not None:
        dims = expanded_scores.get("dimension_scores", {})
        if dims:
            print(
                "  dimensions: "
                + ", ".join(f"{name}={value}" for name, value in dims.items())
            )

    if not report["findings"]:
        print("  no findings")
    else:
        for f in report["findings"]:
            loc = f" [line {f['line']}]" if f.get("line") is not None else ""
            print(f"- {f['severity'].upper()} {f['code']}{loc}: {f['message']}")
            if f.get("suggestion"):
                print(f"    suggestion: {f['suggestion']}")

    lake = report.get("lake_check")
    if lake is not None:
        print(
            f"  lake_check: ok={lake['ok']} returncode={lake['returncode']} "
            f"errors={lake['error_count']}"
        )
        if lake["errors"]:
            for line in lake["errors"][:10]:
                print(f"    {line}")


def main() -> int:
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
    parser = argparse.ArgumentParser(
        description="Audit Lean file for mathlib compatibility."
    )
    parser.add_argument("--lean-file", required=True, help="Path to Lean file.")
    parser.add_argument(
        "--run-lake-check",
        action="store_true",
        help="Run `lake env lean` for the target file.",
    )
    parser.add_argument(
        "--lake-workdir",
        default=".",
        help="Working directory used for `lake env lean` (default: current directory).",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    parser.add_argument("--output", help="Optional path to write JSON report.")
    parser.add_argument(
        "--reasoning-log-file",
        help="Optional JSONL file where structured reasoning events are appended.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when high-severity findings exist.",
    )
    args = parser.parse_args()
    write_reasoning_event = make_reasoning_logger(
        None
        if args.reasoning_log_file is None
        else Path(args.reasoning_log_file).expanduser().resolve()
    )

    def trace_event(step: str, payload: Dict[str, Any]) -> None:
        """Document the responsibility of ``main.trace_event``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``main.trace_event`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        write_reasoning_event(
            step,
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "hook_id": MATHLIB_ABSTRACTION_AUDIT_HOOK,
                **payload,
            },
        )

    lean_file = Path(args.lean_file).expanduser().resolve()
    if not lean_file.exists():
        trace_event(
            "compatibility_audit_input_error",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "error": "lean_file_missing",
                "lean_file": str(lean_file),
            },
        )
        print(f"error: file does not exist: {lean_file}", file=sys.stderr)
        return 2
    if lean_file.suffix != ".lean":
        trace_event(
            "compatibility_audit_input_error",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "error": "invalid_extension",
                "lean_file": str(lean_file),
            },
        )
        print(f"error: expected a .lean file, got: {lean_file}", file=sys.stderr)
        return 2

    lake_workdir = Path(args.lake_workdir).expanduser().resolve()
    if args.run_lake_check and not lake_workdir.exists():
        trace_event(
            "compatibility_audit_input_error",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "error": "lake_workdir_missing",
                "lake_workdir": str(lake_workdir),
            },
        )
        print(f"error: lake workdir does not exist: {lake_workdir}", file=sys.stderr)
        return 2

    trace_event(
        "compatibility_audit_cli_start",
        {
            "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
            "lean_file": str(lean_file),
            "run_lake_check": args.run_lake_check,
            "lake_workdir": str(lake_workdir),
            "json_output": args.json,
            "output_path": args.output,
            "strict": args.strict,
        },
    )

    report = audit_file(
        lean_file=lean_file,
        run_lake_check=args.run_lake_check,
        lake_workdir=lake_workdir,
        trace_event=trace_event,
    )

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        trace_event(
            "compatibility_audit_report_written",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "output_path": str(output_path),
            },
        )

    if args.json:
        trace_event(
            "compatibility_audit_output_emitted",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "output_format": "json",
            },
        )
        print(json.dumps(report, indent=2))
    else:
        trace_event(
            "compatibility_audit_output_emitted",
            {
                "skill": MATHLIB_ABSTRACTION_AUDITOR_SKILL,
                "output_format": "text",
            },
        )
        _print_text_report(report)

    if args.strict:
        high_count = report["summary"]["severity_counts"].get("high", 0)
        if high_count > 0:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

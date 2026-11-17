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

"""Build a cross-file concept index for Lean autoformalization artifacts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, DefaultDict, Dict, List, Optional, Sequence, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover
    append_reasoning_log_entry = None  # type: ignore[assignment]


SKILL_NAME = "lean-cross-file-concept-consistency-indexer"
HOOK_ID = "consistency.cross_file_concepts"
EXTRACTOR_SCRIPT = (
    REPO_ROOT
    / "skills"
    / "lean"
    / "lean-informalization-extractor"
    / "scripts"
    / "extract_lean_informalization.py"
)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_']*")
CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|[0-9]+")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "source",
    "generated",
    "note",
    "theorem",
    "lemma",
    "definition",
    "prop",
    "proof",
    "lean",
    "mathformer",
    "autoformalized",
}


def rel(path: Path) -> str:
    """Document the responsibility of ``rel``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``rel`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def utc_now() -> str:
    """Document the responsibility of ``utc_now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``utc_now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def append_event(
    reasoning_log: Optional[Path], step: str, payload: Dict[str, Any]
) -> None:
    """Document the responsibility of ``append_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def run_json_command(cmd: Sequence[str], *, timeout_sec: int = 120) -> Dict[str, Any]:
    """Document the responsibility of ``run_json_command``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    proc = subprocess.run(
        list(cmd),
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout_sec,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "parse_error": True,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    payload["_command"] = list(cmd)
    payload["_returncode"] = proc.returncode
    payload["_duration_ms"] = duration_ms
    if proc.stderr:
        payload["_stderr_tail"] = proc.stderr[-2000:]
    return payload


def extractor_for_paths(paths: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``extractor_for_paths``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extractor_for_paths`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [sys.executable, str(EXTRACTOR_SCRIPT), "--json"]
    for path in paths:
        cmd.extend(["--lean-file", rel(path)])
    return run_json_command(cmd, timeout_sec=120)


def extractor_for_text(text: str, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``extractor_for_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extractor_for_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return run_json_command(
        [
            sys.executable,
            str(EXTRACTOR_SCRIPT),
            "--text",
            text,
            "--name",
            name,
            "--json",
        ],
        timeout_sec=60,
    )


def simple_name(name: str) -> str:
    """Document the responsibility of ``simple_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``simple_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return name.rsplit(".", 1)[-1]


def name_tokens(name: str) -> List[str]:
    """Document the responsibility of ``name_tokens``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``name_tokens`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw = re.sub(r"[_'.]+", " ", simple_name(name))
    tokens: List[str] = []
    for part in raw.split():
        tokens.extend(CAMEL_RE.findall(part) or [part])
    return [
        token.lower() for token in tokens if token and token.lower() not in STOPWORDS
    ]


def text_tokens(text: str) -> Set[str]:
    """Document the responsibility of ``text_tokens``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``text_tokens`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        token.lower()
        for token in WORD_RE.findall(text)
        if len(token) > 3 and token.lower() not in STOPWORDS
    }


def source_text(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``source_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fields = declaration.get("source_alignment", {}) or {}
    return " ".join(
        str(piece)
        for piece in (
            declaration.get("informal_statement", ""),
            fields.get("original_nl", ""),
            fields.get("original_latex", ""),
            fields.get("generated_notes", ""),
            fields.get("generated_equivalents", ""),
        )
        if piece
    )


def signature_fingerprint(signature: str) -> str:
    """Document the responsibility of ``signature_fingerprint``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``signature_fingerprint`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = re.sub(r"\s+", " ", signature).strip()
    normalized = re.sub(r"\b[A-Za-z_][A-Za-z0-9_']*\s*:", "_:", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def concept_key(declaration: Dict[str, Any]) -> str:
    """Document the responsibility of ``concept_key``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concept_key`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tokens = name_tokens(str(declaration.get("name", "")))
    if tokens:
        return ".".join(tokens)
    words = sorted(text_tokens(source_text(declaration)))
    return ".".join(words[:3]) if words else "unknown"


def declaration_ref(file_name: str, declaration: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``declaration_ref``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``declaration_ref`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    signature = str(declaration.get("signature", ""))
    tokens = sorted(
        set(name_tokens(str(declaration.get("name", ""))))
        | text_tokens(source_text(declaration))
    )[:20]
    return {
        "file": file_name,
        "kind": declaration.get("kind"),
        "name": declaration.get("name"),
        "simple_name": simple_name(str(declaration.get("name", ""))),
        "line": declaration.get("line"),
        "signature_fingerprint": signature_fingerprint(signature),
        "signature_preview": signature[:220],
        "concept_tokens": tokens,
    }


def add_finding(
    findings: List[Dict[str, Any]],
    *,
    severity: str,
    code: str,
    message: str,
    evidence: Dict[str, Any],
) -> None:
    """Document the responsibility of ``add_finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings.append(
        {"severity": severity, "code": code, "message": message, "evidence": evidence}
    )


def build_index(
    report: Dict[str, Any], *, strict_cross_file_duplicates: bool = False
) -> Dict[str, Any]:
    """Document the responsibility of ``build_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    refs: List[Dict[str, Any]] = []
    imports_by_file: Dict[str, List[str]] = {}
    for file_packet in report.get("files", []) or []:
        file_name = str(file_packet.get("file", "<unknown>"))
        imports_by_file[file_name] = list(file_packet.get("imports", []) or [])
        seen_full_in_file: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        seen_simple_in_file: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        for declaration in file_packet.get("declarations", []) or []:
            ref = declaration_ref(file_name, declaration)
            ref["concept_key"] = concept_key(declaration)
            refs.append(ref)
            seen_full_in_file[str(ref["name"])].append(ref)
            seen_simple_in_file[str(ref["simple_name"])].append(ref)
        for name, duplicates in seen_full_in_file.items():
            if len(duplicates) > 1:
                add_finding(
                    findings,
                    severity="high",
                    code="duplicate_full_declaration_name_same_file",
                    message="The same fully qualified declaration name appears more than once in one Lean file.",
                    evidence={
                        "file": file_name,
                        "name": name,
                        "declarations": duplicates,
                    },
                )
        for name, duplicates in seen_simple_in_file.items():
            fingerprints = {str(item["signature_fingerprint"]) for item in duplicates}
            full_names = {str(item["name"]) for item in duplicates}
            if len(duplicates) > 1 and len(full_names) > 1 and len(fingerprints) > 1:
                add_finding(
                    findings,
                    severity="low",
                    code="same_file_simple_name_family",
                    message="Several namespace-qualified declarations share the same simple name in one file; review whether this is intentional.",
                    evidence={
                        "file": file_name,
                        "simple_name": name,
                        "declarations": duplicates,
                    },
                )

    by_name: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_concept: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ref in refs:
        by_name[str(ref["simple_name"])].append(ref)
        by_concept[str(ref["concept_key"])].append(ref)

    for name, duplicates in sorted(by_name.items()):
        files = {str(item["file"]) for item in duplicates}
        fingerprints = {str(item["signature_fingerprint"]) for item in duplicates}
        if len(files) > 1 and len(fingerprints) > 1:
            add_finding(
                findings,
                severity="high" if strict_cross_file_duplicates else "medium",
                code="cross_file_name_divergent_signature",
                message="The same simple declaration name appears across files with divergent signatures.",
                evidence={"simple_name": name, "declarations": duplicates},
            )

    concept_index: Dict[str, Any] = {}
    for key, declarations in sorted(by_concept.items()):
        if len(declarations) < 2:
            continue
        fingerprints = sorted(
            {str(item["signature_fingerprint"]) for item in declarations}
        )
        files = sorted({str(item["file"]) for item in declarations})
        concept_index[key] = {
            "declaration_count": len(declarations),
            "file_count": len(files),
            "files": files,
            "signature_family_count": len(fingerprints),
            "signature_fingerprints": fingerprints,
            "declarations": declarations,
        }
        if len(files) > 1 and len(declarations) >= 3:
            add_finding(
                findings,
                severity="low",
                code="mathformerlib_promotion_candidate",
                message="A concept family repeats across files and may be a MathformerLib promotion candidate.",
                evidence={
                    "concept_key": key,
                    "files": files,
                    "declaration_count": len(declarations),
                },
            )

    high = sum(1 for item in findings if item.get("severity") == "high")
    medium = sum(1 for item in findings if item.get("severity") == "medium")
    low = sum(1 for item in findings if item.get("severity") == "low")
    score = max(0, 100 - min(90, 40 * high) - min(35, 6 * medium) - min(15, low))
    kind_counts = Counter(str(item.get("kind")) for item in refs)
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": high == 0,
        "summary": {
            "file_count": len(imports_by_file),
            "declaration_count": len(refs),
            "concept_family_count": len(concept_index),
            "repeated_name_count": sum(
                1 for values in by_name.values() if len(values) > 1
            ),
            "finding_count": len(findings),
            "blocking_finding_count": high,
            "cross_file_consistency_score": score,
            "kind_counts": dict(sorted(kind_counts.items())),
        },
        "imports_by_file": imports_by_file,
        "concept_index": concept_index,
        "findings": findings,
    }


def run_self_test() -> Dict[str, Any]:
    """Document the responsibility of ``run_self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    good_text = """
/-- Generated note (NL): First concept. -/
def FirstConcept : Prop := True

/-- Generated note (NL): Second concept. -/
def SecondConcept : Prop := True
"""
    bad_text = """
/-- Generated note (NL): Duplicate concept one. -/
def DuplicateConcept : Prop := True

/-- Generated note (NL): Duplicate concept two. -/
def DuplicateConcept : Prop := False
"""
    good = build_index(extractor_for_text(good_text, "good_cross_file_fixture"))
    bad = build_index(extractor_for_text(bad_text, "bad_cross_file_fixture"))
    bad_codes = {item.get("code") for item in bad.get("findings", [])}
    ok = (
        bool(good.get("ok"))
        and not bool(bad.get("ok"))
        and "duplicate_full_declaration_name_same_file" in bad_codes
    )
    return {
        "generated_at_utc": utc_now(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": ok,
        "summary": {
            "good_fixture_ok": good.get("ok"),
            "bad_fixture_ok": bad.get("ok"),
            "bad_codes": sorted(str(code) for code in bad_codes),
        },
        "fixtures": {"good": good, "bad": bad},
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
    parser.add_argument(
        "--lean-file", action="append", default=[], help="Lean file to index."
    )
    parser.add_argument("--text", help="Inline Lean text fixture to index.")
    parser.add_argument(
        "--name", default="inline.lean", help="Name for inline text input."
    )
    parser.add_argument(
        "--extractor-report",
        type=Path,
        help="Existing informalization extractor JSON report.",
    )
    parser.add_argument(
        "--strict-cross-file-duplicates",
        action="store_true",
        help="Promote cross-file divergent same-name signatures to blockers.",
    )
    parser.add_argument(
        "--include-extractor-report",
        action="store_true",
        help="Embed the extractor report in output.",
    )
    parser.add_argument(
        "--reasoning-log-file", type=Path, help="Optional JSONL reasoning log path."
    )
    parser.add_argument("--output-file", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--expect-ok",
        action="store_true",
        help="Return nonzero when the report is not ok.",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run built-in fixtures."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    return parser.parse_args(argv)


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
        report = run_self_test()
    else:
        append_event(args.reasoning_log_file, "lean_cross_file_concept_index_start", {})
        if args.extractor_report:
            extractor_report = json.loads(
                args.extractor_report.read_text(encoding="utf-8")
            )
        elif args.text is not None:
            extractor_report = extractor_for_text(args.text, args.name)
        else:
            paths = [Path(path) for path in args.lean_file]
            extractor_report = extractor_for_paths(paths)
        report = build_index(
            extractor_report,
            strict_cross_file_duplicates=args.strict_cross_file_duplicates,
        )
        if args.include_extractor_report:
            report["extractor_report"] = extractor_report
        append_event(
            args.reasoning_log_file,
            "lean_cross_file_concept_index_complete",
            report.get("summary", {}),
        )

    if args.output_file:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"ok={report.get('ok')} cross_file_score={report.get('summary', {}).get('cross_file_consistency_score')} "
            f"findings={report.get('summary', {}).get('finding_count', 0)}"
        )
    return 1 if args.expect_ok and not report.get("ok") else 0


if __name__ == "__main__":
    raise SystemExit(main())

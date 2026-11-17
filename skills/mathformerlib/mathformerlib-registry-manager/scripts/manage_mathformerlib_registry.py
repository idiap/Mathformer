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

"""Build and validate the Mathformerlib formalization registry."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "mathformerlib-registry-manager"
HOOK_ID = "mathformerlib.registry"
DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")
PLACEHOLDER_RE = re.compile(
    r"(?<![A-Za-z0-9_])(sorry|admit|axiom|exact\?)(?![A-Za-z0-9_])|"
    r"\b(mock|mocked|stub|fake|simulated|placeholder|TODO|FIXME)\b",
    re.IGNORECASE,
)
SCAFFOLD_RE = re.compile(
    r"(?i)\b(interface scaffold|scaffold|intentionally abstract|abstract boundary)\b"
)


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


def module_from_path(path: Path) -> str:
    """Document the responsibility of ``module_from_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_from_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rel_path = path.resolve().relative_to(REPO_ROOT.resolve()).with_suffix("")
    return ".".join(rel_path.parts)


def file_sha256(path: Path) -> str:
    """Document the responsibility of ``file_sha256``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``file_sha256`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_imports(text: str) -> List[str]:
    """Document the responsibility of ``parse_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    imports: List[str] = []
    for raw in text.splitlines():
        match = IMPORT_RE.match(raw)
        if match is None:
            continue
        imports.extend(part for part in match.group(1).split() if part)
    return imports


def parse_declarations(text: str, module: str, path: Path) -> List[Dict[str, Any]]:
    """Document the responsibility of ``parse_declarations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    declarations: List[Dict[str, Any]] = []
    namespace_stack: List[str] = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        stripped = re.sub(r"--.*$", "", raw).strip()
        namespace_match = re.match(r"^namespace\s+([A-Za-z0-9_.']+)\s*$", stripped)
        if namespace_match is not None:
            namespace_stack.append(namespace_match.group(1))
            continue
        end_match = re.match(r"^end(?:\s+([A-Za-z0-9_.']+))?\s*$", stripped)
        if end_match is not None and namespace_stack:
            end_name = end_match.group(1)
            if end_name is None or namespace_stack[-1] == end_name:
                namespace_stack.pop()
            continue
        match = DECL_RE.match(raw)
        if match is None:
            continue
        kind, name = match.groups()
        qualified = ".".join([*namespace_stack, name]) if namespace_stack else name
        declarations.append(
            {
                "kind": kind,
                "name": name,
                "qualified_name": qualified,
                "module": module,
                "path": rel(path),
                "line": line_no,
                "source_ref": f"{rel(path)}:{line_no}",
                "signature": raw.strip(),
            }
        )
    return declarations


def marker_rows(text: str, pattern: re.Pattern[str], code: str) -> List[Dict[str, Any]]:
    """Document the responsibility of ``marker_rows``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``marker_rows`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows: List[Dict[str, Any]] = []
    for line_no, raw in enumerate(text.splitlines(), 1):
        for match in pattern.finditer(raw):
            rows.append(
                {
                    "code": code,
                    "line": line_no,
                    "evidence": raw.strip(),
                    "match": match.group(0),
                }
            )
    return rows


def classify_module(
    path: Path, placeholders: List[Dict[str, Any]], scaffolds: List[Dict[str, Any]]
) -> str:
    """Document the responsibility of ``classify_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_module`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if placeholders or scaffolds:
        return "draft"
    if (
        rel(path).startswith("libraries/MathformerLib/")
        or rel(path) == "libraries/MathformerLib.lean"
    ):
        return "accepted"
    return "candidate"


def iter_lean_files(roots: Sequence[Path]) -> Iterable[Path]:
    """Document the responsibility of ``iter_lean_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_lean_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen: set[Path] = set()
    for root in roots:
        path = (REPO_ROOT / root).resolve()
        if path.is_file() and path.suffix == ".lean":
            if path not in seen:
                seen.add(path)
                yield path
        elif path.is_dir():
            for item in sorted(path.rglob("*.lean")):
                item = item.resolve()
                if item not in seen:
                    seen.add(item)
                    yield item


def scan_module(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``scan_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``scan_module`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = path.read_text(encoding="utf-8")
    module = module_from_path(path)
    placeholders = marker_rows(text, PLACEHOLDER_RE, "placeholder_marker")
    scaffolds = marker_rows(text, SCAFFOLD_RE, "scaffold_marker")
    declarations = parse_declarations(text, module, path)
    return {
        "module": module,
        "path": rel(path),
        "sha256": file_sha256(path),
        "imports": parse_imports(text),
        "declaration_count": len(declarations),
        "theorem_like_count": sum(
            1 for item in declarations if item["kind"] in {"theorem", "lemma"}
        ),
        "status": classify_module(path, placeholders, scaffolds),
        "markers": {
            "placeholders": placeholders,
            "scaffolds": scaffolds,
        },
        "declarations": declarations,
    }


def duplicate_findings(modules: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``duplicate_findings``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for module in modules:
        for decl in module.get("declarations", []):
            by_name.setdefault(decl["qualified_name"], []).append(decl)
    findings: List[Dict[str, Any]] = []
    for name, rows in sorted(by_name.items()):
        if len(rows) <= 1:
            continue
        findings.append(
            {
                "severity": "medium",
                "code": "duplicate_qualified_declaration",
                "message": f"Declaration `{name}` appears in multiple registry entries.",
                "occurrences": rows,
            }
        )
    return findings


def build_registry(roots: Sequence[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``build_registry``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    modules = [scan_module(path) for path in iter_lean_files(roots)]
    declarations = [decl for module in modules for decl in module["declarations"]]
    findings = duplicate_findings(modules)
    accepted_with_markers = [
        module
        for module in modules
        if module["status"] == "accepted"
        and (module["markers"]["placeholders"] or module["markers"]["scaffolds"])
    ]
    for module in accepted_with_markers:
        findings.append(
            {
                "severity": "high",
                "code": "accepted_module_has_markers",
                "message": f"Accepted module `{module['module']}` contains placeholder or scaffold markers.",
                "path": module["path"],
            }
        )
    status_counts: Dict[str, int] = {}
    for module in modules:
        status_counts[module["status"]] = status_counts.get(module["status"], 0) + 1
    blocking = [item for item in findings if item["severity"] == "high"]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "library": "MathformerLib",
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": not blocking,
        "roots": [str(root) for root in roots],
        "summary": {
            "module_count": len(modules),
            "declaration_count": len(declarations),
            "theorem_like_count": sum(
                module["theorem_like_count"] for module in modules
            ),
            "status_counts": status_counts,
            "finding_count": len(findings),
            "blocking_finding_count": len(blocking),
        },
        "modules": modules,
        "findings": findings,
    }


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
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def render_text(registry: Dict[str, Any]) -> str:
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
    summary = registry["summary"]
    lines = [
        f"ok: {registry['ok']}",
        f"modules: {summary['module_count']}",
        f"declarations: {summary['declaration_count']}",
        f"theorem_like: {summary['theorem_like_count']}",
        f"statuses: {summary['status_counts']}",
        f"findings: {summary['finding_count']}",
    ]
    for module in registry["modules"]:
        lines.append(
            f"- {module['status']} {module['module']} "
            f"decls={module['declaration_count']} path={module['path']}"
        )
    for finding in registry["findings"][:20]:
        lines.append(f"! {finding['severity']} {finding['code']}: {finding['message']}")
    return "\n".join(lines)


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
        "--include-root",
        action="append",
        type=Path,
        default=[],
        help="Lean file or directory to include. Defaults to MathformerLib.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("artifacts/mathformerlib/registry.json"),
    )
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--json", action="store_true")
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
    roots = args.include_root or [
        Path("MathformerLib"),
        Path("libraries/MathformerLib.lean"),
    ]
    append_event(
        args.reasoning_log_file,
        "mathformerlib_registry_build_start",
        {"roots": [str(root) for root in roots]},
    )
    registry = build_registry(roots)
    output_file = (REPO_ROOT / args.output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    append_event(
        args.reasoning_log_file,
        "mathformerlib_registry_build_complete",
        {"output_file": rel(output_file), "ok": registry["ok"], **registry["summary"]},
    )
    if args.json:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
    else:
        print(render_text(registry))
    return 0 if registry["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

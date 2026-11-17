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

"""Navigate the local mathlib source tree by module hierarchy and declaration neighborhood."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")


@dataclass
class ModuleRecord:
    """Document the responsibility of ``ModuleRecord``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/mathlib-hierarchy-navigator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    module: str
    rel_file: str
    source_path: str
    depth: int
    parent: Optional[str]


@dataclass
class DeclarationRecord:
    """Document the responsibility of ``DeclarationRecord``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/mathlib-hierarchy-navigator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    name: str
    kind: str
    module: str
    line: int
    source_ref: str
    signature: str


def normalize_module(value: str) -> str:
    """Document the responsibility of ``normalize_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_module`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = value.strip().replace("/", ".")
    if text.endswith(".lean"):
        text = text[:-5]
    text = text.strip(".")
    if not text:
        return "Mathlib"
    if not text.startswith("Mathlib"):
        text = "Mathlib." + text
    return text


def module_from_path(mathlib_root: Path, path: Path) -> str:
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
    rel = path.relative_to(mathlib_root).with_suffix("")
    return "Mathlib." + ".".join(rel.parts)


def module_to_path(mathlib_root: Path, module: str) -> Path:
    """Document the responsibility of ``module_to_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_to_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = normalize_module(module)
    parts = normalized.split(".")
    if parts and parts[0] == "Mathlib":
        parts = parts[1:]
    return mathlib_root.joinpath(*parts).with_suffix(".lean")


def is_child_path(path: Path, parent: Path) -> bool:
    """Document the responsibility of ``is_child_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_child_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def parent_module(module: str) -> Optional[str]:
    """Document the responsibility of ``parent_module``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``parent_module`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = module.split(".")
    if len(parts) <= 1:
        return None
    return ".".join(parts[:-1])


def module_ancestors(module: str) -> List[str]:
    """Document the responsibility of ``module_ancestors``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_ancestors`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = module.split(".")
    return [".".join(parts[:idx]) for idx in range(1, len(parts) + 1)]


def source_ref(rel_file: str, line: int) -> str:
    """Document the responsibility of ``source_ref``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_ref`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"{rel_file}:{line}"


def iter_module_records(mathlib_root: Path) -> List[ModuleRecord]:
    """Document the responsibility of ``iter_module_records``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_module_records`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    records: List[ModuleRecord] = []
    for path in sorted(mathlib_root.rglob("*.lean")):
        module = module_from_path(mathlib_root, path)
        rel_file = str(path.relative_to(mathlib_root))
        records.append(
            ModuleRecord(
                module=module,
                rel_file=rel_file,
                source_path=str(path.resolve()),
                depth=len(module.split(".")),
                parent=parent_module(module),
            )
        )
    return records


def build_children(records: Sequence[ModuleRecord]) -> Dict[str, Set[str]]:
    """Document the responsibility of ``build_children``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    children: Dict[str, Set[str]] = defaultdict(set)
    for record in records:
        parts = record.module.split(".")
        for idx in range(1, len(parts)):
            parent = ".".join(parts[:idx])
            child = ".".join(parts[: idx + 1])
            children[parent].add(child)
    return children


def leaf_count(prefix: str, modules: Set[str]) -> int:
    """Document the responsibility of ``leaf_count``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``leaf_count`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    needle = prefix + "."
    return sum(1 for module in modules if module == prefix or module.startswith(needle))


def child_rows(
    prefix: str,
    *,
    children: Dict[str, Set[str]],
    modules: Set[str],
    records_by_module: Dict[str, ModuleRecord],
    max_children: int,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``child_rows``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``child_rows`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows: List[Dict[str, Any]] = []
    for child in sorted(children.get(prefix, set()))[:max_children]:
        record = records_by_module.get(child)
        rows.append(
            {
                "module": child,
                "kind": (
                    "module_prefix"
                    if child in modules and child in children
                    else ("module" if child in modules else "prefix")
                ),
                "leaf_count": leaf_count(child, modules),
                "source_ref": None if record is None else record.rel_file,
            }
        )
    return rows


def parse_imports(path: Path) -> List[str]:
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
    if not path.exists():
        return imports
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = IMPORT_RE.match(raw)
        if match is not None:
            imports.extend(match.group(1).split())
        elif DECL_RE.match(raw):
            break
    return imports


def parse_declarations(
    mathlib_root: Path,
    path: Path,
    *,
    query: Optional[str] = None,
    max_decls: int = 40,
) -> List[DeclarationRecord]:
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
    if not path.exists():
        return []
    module = module_from_path(mathlib_root, path)
    rel_file = str(path.relative_to(mathlib_root))
    query_l = None if query is None else query.lower()
    declarations: List[DeclarationRecord] = []
    for line_no, raw in enumerate(
        path.read_text(encoding="utf-8", errors="ignore").splitlines(),
        start=1,
    ):
        match = DECL_RE.match(raw)
        if match is None:
            continue
        kind, name = match.groups()
        signature = raw.strip()
        haystack = f"{name} {kind} {signature}".lower()
        if query_l and query_l not in haystack:
            continue
        declarations.append(
            DeclarationRecord(
                name=name,
                kind=kind,
                module=module,
                line=line_no,
                source_ref=source_ref(rel_file, line_no),
                signature=signature,
            )
        )
        if len(declarations) >= max_decls:
            break
    return declarations


def module_matches(module: str, terms: Sequence[str]) -> bool:
    """Document the responsibility of ``module_matches``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_matches`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    module_l = module.lower()
    return all(term in module_l for term in terms)


def declaration_search(
    mathlib_root: Path,
    records: Sequence[ModuleRecord],
    *,
    query: str,
    max_modules: int,
    max_decls: int,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``declaration_search``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows: List[Dict[str, Any]] = []
    remaining = max_decls
    for record in records[:max_modules]:
        if remaining <= 0:
            break
        path = mathlib_root / record.rel_file
        found = parse_declarations(
            mathlib_root,
            path,
            query=query,
            max_decls=remaining,
        )
        for decl in found:
            rows.append(asdict(decl))
        remaining = max_decls - len(rows)
    return rows


def append_reasoning_event(
    path: Optional[Path],
    *,
    step: str,
    payload: Dict[str, Any],
) -> None:
    """Document the responsibility of ``append_reasoning_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_reasoning_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return
    append_reasoning_log_entry(path, step=step, payload=payload)


def build_navigation(args: argparse.Namespace) -> Dict[str, Any]:
    """Document the responsibility of ``build_navigation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    mathlib_root = args.mathlib_root
    if not mathlib_root.exists():
        raise FileNotFoundError(f"Mathlib root not found: {mathlib_root}")

    focus = normalize_module(args.module or args.module_prefix)
    records = iter_module_records(mathlib_root)
    modules = {record.module for record in records}
    records_by_module = {record.module: record for record in records}
    children = build_children(records)
    focus_path = module_to_path(mathlib_root, focus)
    focus_record = records_by_module.get(focus)

    parent = parent_module(focus)
    sibling_rows: List[Dict[str, Any]] = []
    if parent is not None:
        sibling_rows = [
            row
            for row in child_rows(
                parent,
                children=children,
                modules=modules,
                records_by_module=records_by_module,
                max_children=args.max_children + 1,
            )
            if row["module"] != focus
        ][: args.max_children]

    payload: Dict[str, Any] = {
        "mathlib_root": str(mathlib_root.resolve()),
        "focus": {
            "module": focus,
            "kind": (
                "module_prefix"
                if focus in modules and focus in children
                else ("module" if focus in modules else "prefix")
            ),
            "source_path": None if focus_record is None else focus_record.source_path,
            "source_ref": None if focus_record is None else focus_record.rel_file,
        },
        "ancestors": module_ancestors(focus),
        "children": child_rows(
            focus,
            children=children,
            modules=modules,
            records_by_module=records_by_module,
            max_children=args.max_children,
        ),
        "siblings": sibling_rows,
        "module": None,
        "query_results": None,
    }

    if (
        focus_path.exists()
        and focus_path.is_file()
        and is_child_path(focus_path, mathlib_root)
    ):
        payload["module"] = {
            "module": focus,
            "imports": parse_imports(focus_path),
            "declarations": [
                asdict(row)
                for row in parse_declarations(
                    mathlib_root,
                    focus_path,
                    query=args.declaration,
                    max_decls=args.max_decls,
                )
            ],
        }

    if args.query:
        terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_']+", args.query)]
        matching_modules = [
            asdict(record) for record in records if module_matches(record.module, terms)
        ][: args.max_modules]
        search_space = [
            record for record in records if module_matches(record.module, terms)
        ]
        if not search_space:
            search_space = records
        payload["query_results"] = {
            "query": args.query,
            "matching_modules": matching_modules,
            "matching_declarations": declaration_search(
                mathlib_root,
                search_space,
                query=args.query,
                max_modules=args.max_search_modules,
                max_decls=args.max_decls,
            ),
        }

    return payload


def render_text(payload: Dict[str, Any]) -> str:
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
    focus = payload["focus"]
    lines = [
        f"Focus: {focus['module']} ({focus['kind']})",
        "Ancestors: " + " -> ".join(payload["ancestors"]),
    ]
    if payload["children"]:
        lines.append("Children:")
        for row in payload["children"]:
            lines.append(
                f"- {row['module']} [{row['kind']}; leaves={row['leaf_count']}]"
            )
    if payload["siblings"]:
        lines.append("Siblings:")
        for row in payload["siblings"]:
            lines.append(f"- {row['module']} [{row['kind']}]")
    if payload.get("module"):
        module = payload["module"]
        lines.append("Imports:")
        for imp in module["imports"]:
            lines.append(f"- import {imp}")
        lines.append("Declarations:")
        for decl in module["declarations"]:
            lines.append(f"- {decl['kind']} {decl['name']} ({decl['source_ref']})")
    query_results = payload.get("query_results")
    if query_results:
        lines.append(f"Query: {query_results['query']}")
        lines.append("Matching modules:")
        for row in query_results["matching_modules"]:
            lines.append(f"- {row['module']} ({row['rel_file']})")
        lines.append("Matching declarations:")
        for row in query_results["matching_declarations"]:
            lines.append(
                f"- {row['kind']} {row['name']} in {row['module']} ({row['source_ref']})"
            )
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
        "--mathlib-root",
        type=Path,
        default=Path(".lake/packages/mathlib/Mathlib"),
        help="Path to the local Mathlib source root.",
    )
    parser.add_argument(
        "--module-prefix",
        default="Mathlib",
        help="Module prefix to navigate, such as Mathlib.Topology.",
    )
    parser.add_argument(
        "--module",
        help="Concrete module to inspect, such as Mathlib.Topology.Basic.",
    )
    parser.add_argument(
        "--declaration",
        help="Optional declaration-name substring filter inside the focused module.",
    )
    parser.add_argument(
        "--query",
        help="Optional module/declaration query to organize under the hierarchy.",
    )
    parser.add_argument("--max-children", type=int, default=24)
    parser.add_argument("--max-modules", type=int, default=40)
    parser.add_argument("--max-search-modules", type=int, default=300)
    parser.add_argument("--max-decls", type=int, default=60)
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
    append_reasoning_event(
        args.reasoning_log_file,
        step="mathlib_hierarchy_navigation_start",
        payload={
            "skill": "mathlib-hierarchy-navigator",
            "hook_id": "mathlib.hierarchy.navigate",
            "module_prefix": args.module_prefix,
            "module": args.module,
            "query": args.query,
        },
    )
    payload = build_navigation(args)
    append_reasoning_event(
        args.reasoning_log_file,
        step="mathlib_module_tree_scanned",
        payload={
            "skill": "mathlib-module-tree-cartographer",
            "hook_id": "mathlib.hierarchy.module_tree",
            "focus": payload["focus"],
            "child_count": len(payload["children"]),
            "sibling_count": len(payload["siblings"]),
        },
    )
    if payload.get("module") is not None:
        append_reasoning_event(
            args.reasoning_log_file,
            step="mathlib_declaration_neighborhood_ready",
            payload={
                "skill": "mathlib-declaration-neighborhood-navigator",
                "hook_id": "mathlib.hierarchy.declaration_neighborhood",
                "module": payload["module"]["module"],
                "declaration_count": len(payload["module"]["declarations"]),
            },
        )
    append_reasoning_event(
        args.reasoning_log_file,
        step="mathlib_hierarchy_navigation_complete",
        payload={
            "skill": "mathlib-hierarchy-navigator",
            "hook_id": "mathlib.hierarchy.navigate",
            "focus": payload["focus"],
        },
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

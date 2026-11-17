#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Shared helpers for the controlled Mathlib indexing layer."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MATHLIB_ROOT = REPO_ROOT / ".lake" / "packages" / "mathlib" / "Mathlib"
DEFAULT_INDEX = REPO_ROOT / "artifacts" / "mathlib_index" / "index.json"
DEFAULT_RERANKER_CACHE = (
    REPO_ROOT / "artifacts" / "mathlib_index" / "reranker_cache.json"
)

DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")
DOC_RE = re.compile(r"^\s*/--\s?(.*)")

AREA_SEGMENTS = {
    "Topology",
    "Analysis",
    "Order",
    "MeasureTheory",
    "LinearAlgebra",
    "Geometry",
    "Data",
    "Algebra",
    "SetTheory",
    "CategoryTheory",
    "Combinatorics",
    "Probability",
    "Logic",
    "NumberTheory",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def run_version(command: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"unavailable:{exc.__class__.__name__}"
    text = (result.stdout or result.stderr).strip().splitlines()
    return text[0] if text else f"returncode:{result.returncode}"


def version_stamp(mathlib_root: Path) -> dict[str, Any]:
    mathlib_repo = mathlib_root.parent
    revision = (
        run_version(["git", "rev-parse", "HEAD"], cwd=mathlib_repo)
        if (mathlib_repo / ".git").exists()
        else "unknown"
    )
    return {
        "lean_version": run_version(["lean", "--version"]),
        "mathlib_git_revision": revision,
        "mathlib_root": rel(mathlib_root),
        "build_timestamp_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }


def module_from_path(mathlib_root: Path, path: Path) -> str:
    return "Mathlib." + ".".join(path.relative_to(mathlib_root).with_suffix("").parts)


def source_ref(mathlib_root: Path, path: Path, line: int) -> str:
    return f"{path.relative_to(mathlib_root).as_posix()}:{line}"


def area_tags(module: str) -> list[str]:
    tags = []
    for part in module.split("."):
        if part in AREA_SEGMENTS:
            tags.append(
                part.replace("MeasureTheory", "measure_theory")
                .replace("LinearAlgebra", "linear_algebra")
                .lower()
            )
    return sorted(set(tags))


def parse_imports(lines: list[str]) -> list[str]:
    imports: list[str] = []
    for raw in lines:
        match = IMPORT_RE.match(raw)
        if match:
            imports.extend(match.group(1).split())
        elif DECL_RE.match(raw):
            break
    return imports


def doc_comment_before(lines: list[str], index: int) -> str:
    collected: list[str] = []
    cursor = index - 1
    while cursor >= 0:
        raw = lines[cursor].strip()
        if not raw:
            cursor -= 1
            continue
        if raw.endswith("-/"):
            text = raw[:-2].strip()
            if text:
                collected.append(text)
            cursor -= 1
            while cursor >= 0:
                item = lines[cursor].strip()
                start = DOC_RE.match(item)
                if start:
                    collected.append(start.group(1).strip())
                    break
                collected.append(item)
                cursor -= 1
            break
        start = DOC_RE.match(raw)
        if start:
            collected.append(start.group(1).strip())
            break
        break
    return " ".join(reversed([item for item in collected if item])).strip()


def split_decl_tokens(name: str) -> list[str]:
    spaced = re.sub(
        r"([a-z0-9])([A-Z])", r"\1 \2", name.replace(".", " ").replace("_", " ")
    )
    return [token.lower() for token in re.findall(r"[A-Za-z0-9]+", spaced) if token]


def token_hash_vector(tokens: list[str], *, buckets: int = 64) -> dict[str, float]:
    vector: dict[str, float] = {}
    for token in tokens:
        bucket = (
            int(hashlib.sha256(token.encode("utf-8")).hexdigest()[:8], 16) % buckets
        )
        key = str(bucket)
        vector[key] = vector.get(key, 0.0) + 1.0
    return vector


def theorem_shape(signature: str) -> dict[str, Any]:
    binder_types = re.findall(r"\([^:()]+:\s*([^()]+?)\)", signature)
    typeclasses = re.findall(r"\[([^\[\]]+)\]", signature)
    after_colon = signature.split(":", 1)[1].strip() if ":" in signature else signature
    conclusion = after_colon.split(":=", 1)[0].strip()
    head = conclusion.split()[0] if conclusion.split() else ""
    return {
        "binder_type_heads": [
            item.strip().split()[0] for item in binder_types[:8] if item.strip()
        ],
        "typeclass_requirements": [
            item.strip() for item in typeclasses[:8] if item.strip()
        ],
        "conclusion_head": head,
        "proposition_kind": (
            "iff"
            if "↔" in conclusion
            else (
                "equality"
                if "=" in conclusion
                else (
                    "implication"
                    if "->" in conclusion or "→" in conclusion
                    else "predicate"
                )
            )
        ),
    }


def import_cost(module: str, imports: list[str]) -> int:
    return len(imports) + module.count(".")


def parse_mathlib(
    mathlib_root: Path, *, max_files: int | None = None
) -> dict[str, Any]:
    lean_files = sorted(mathlib_root.rglob("*.lean"))
    if max_files is not None:
        lean_files = lean_files[:max_files]
    modules: list[dict[str, Any]] = []
    declarations: list[dict[str, Any]] = []
    import_edges: dict[str, list[str]] = {}
    for path in lean_files:
        module = module_from_path(mathlib_root, path)
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        imports = parse_imports(lines)
        import_edges[module] = imports
        modules.append(
            {
                "module": module,
                "parent": ".".join(module.split(".")[:-1]) if "." in module else None,
                "depth": len(module.split(".")),
                "source_path": rel(path),
                "source_ref": path.relative_to(mathlib_root).as_posix(),
                "direct_imports": imports,
                "area_tags": area_tags(module),
            }
        )
        for line_no, raw in enumerate(lines, start=1):
            match = DECL_RE.match(raw)
            if not match:
                continue
            kind, short = match.groups()
            qualified = short if short.startswith(module) else f"{module}.{short}"
            doc = doc_comment_before(lines, line_no - 1)
            declarations.append(
                {
                    "qualified_name": qualified,
                    "short_name": short.split(".")[-1],
                    "namespace": ".".join(qualified.split(".")[:-1]),
                    "kind": kind,
                    "module": module,
                    "line": line_no,
                    "source_ref": source_ref(mathlib_root, path, line_no),
                    "signature": raw.strip(),
                    "doc_comment": doc,
                    "attributes": re.findall(
                        r"\[(simp|ext|norm_cast|aesop|refl)\]", raw
                    ),
                    "declaration_tokens": split_decl_tokens(short),
                    "namespace_tokens": split_decl_tokens(module),
                    "theorem_shape": theorem_shape(raw),
                    "lean_check_status": "unverified",
                    "import_cost": import_cost(module, imports),
                }
            )
    imported_by: dict[str, list[str]] = defaultdict(list)
    for module, imports in import_edges.items():
        for imported in imports:
            imported_by[imported].append(module)
    for row in modules:
        row["imported_by"] = sorted(imported_by.get(row["module"], []))
        row["leaf_count"] = sum(
            1
            for item in modules
            if item["module"] == row["module"]
            or item["module"].startswith(row["module"] + ".")
        )
    declaration_graph = build_declaration_graph(declarations)
    stamp = version_stamp(mathlib_root)
    stamp["file_count"] = len(lean_files)
    stamp["declaration_count"] = len(declarations)
    return {
        "schema_version": "mathformer.mathlib_index.v0.1",
        "version_stamp": stamp,
        "optional_rerankers": {
            "cache_path": rel(DEFAULT_RERANKER_CACHE),
            "enabled_by_default": False,
            "reranker_order": [
                "deterministic_score",
                "verified_lean_check",
                "optional_doc_namespace_similarity",
            ],
            "verification_guard": "optional rerankers may break ties among unverified candidates but must never override a failed Lean verification",
        },
        "modules": modules,
        "declarations": declarations,
        "declaration_graph": declaration_graph,
        "metadata_hash": hashlib.sha256(
            json.dumps(stamp, sort_keys=True).encode()
        ).hexdigest()[:16],
    }


def build_optional_reranker_cache(index: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for decl in index.get("declarations", []):
        doc_tokens = split_decl_tokens(decl.get("doc_comment", ""))
        namespace_tokens = list(decl.get("namespace_tokens", []))
        if not doc_tokens and not namespace_tokens:
            continue
        entries.append(
            {
                "qualified_name": decl["qualified_name"],
                "module": decl["module"],
                "doc_comment_token_hash_embedding": token_hash_vector(doc_tokens),
                "namespace_token_hash_embedding": token_hash_vector(namespace_tokens),
                "guard": "tie_break_only_never_override_failed_lean_verification",
            }
        )
    return {
        "schema_version": "mathformer.mathlib_optional_reranker_cache.v0.1",
        "source_index_hash": index.get("metadata_hash"),
        "embedding_kind": "deterministic_token_hash",
        "enabled_by_default": False,
        "entry_count": len(entries),
        "entries": entries,
    }


def build_declaration_graph(declarations: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_module: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_namespace: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for decl in declarations:
        by_module[decl["module"]].append(decl)
        by_namespace[decl["namespace"]].append(decl)
    graph: dict[str, list[str]] = {}
    for decl in declarations:
        related: set[str] = set()
        for peer in by_module[decl["module"]][:16]:
            if peer["qualified_name"] != decl["qualified_name"]:
                related.add(peer["qualified_name"])
        for peer in by_namespace[decl["namespace"]][:16]:
            if peer["qualified_name"] != decl["qualified_name"]:
                related.add(peer["qualified_name"])
        for token in decl["declaration_tokens"]:
            if token in {
                "assoc",
                "comm",
                "left",
                "right",
                "inter",
                "union",
                "compact",
                "convex",
                "measurable",
                "tendsto",
            }:
                for peer in declarations:
                    if (
                        token in peer["declaration_tokens"]
                        and peer["qualified_name"] != decl["qualified_name"]
                    ):
                        related.add(peer["qualified_name"])
                        if len(related) >= 12:
                            break
        graph[decl["qualified_name"]] = sorted(related)[:12]
    return graph


def load_index(path: Path = DEFAULT_INDEX) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_stamp_matches(
    index: dict[str, Any], mathlib_root: Path = DEFAULT_MATHLIB_ROOT
) -> bool:
    current = version_stamp(mathlib_root)
    previous = index.get("version_stamp", {})
    return current.get("lean_version") == previous.get("lean_version") and current.get(
        "mathlib_git_revision"
    ) == previous.get("mathlib_git_revision")

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

"""Map concepts from an informal proof to likely mathlib declarations.

The script scans mathlib declaration headers, ranks relevant modules, and then scores
declarations with token/synonym overlap plus module relevance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence

for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")


REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))
ONTOLOGY_SCRIPTS = (
    REPO_ROOT / "skills" / "mathlib" / "mathlib-concept-ontology-manager" / "scripts"
)
if str(ONTOLOGY_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ONTOLOGY_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry as append_shared_reasoning_log_entry,
)

try:
    from ontology import (
        keyword_hints,
        load_profile,
        phrase_hints,
        preferred_decls,
        synonym_map,
    )
except Exception:  # pragma: no cover - early bootstrap fallback.
    keyword_hints = load_profile = phrase_hints = preferred_decls = synonym_map = None


DECL_PATTERN = r"^(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+"
LEAN_ERROR_RE = re.compile(
    r"^.*:(?P<line>\d+):(?P<col>\d+):\s*error(?:\([^)]+\))?:\s*(?P<msg>.*)$"
)
DECL_NAME_RE = re.compile(
    r"^(?:@[\w.]+\s+)?(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "assume",
    "be",
    "by",
    "for",
    "from",
    "given",
    "if",
    "in",
    "is",
    "it",
    "let",
    "of",
    "on",
    "or",
    "prove",
    "show",
    "since",
    "suppose",
    "that",
    "the",
    "then",
    "there",
    "therefore",
    "this",
    "to",
    "we",
    "when",
    "with",
    "article",
    "base",
    "case",
    "classical",
    "document",
    "example",
    "follows",
    "idea",
    "item",
    "note",
    "overview",
    "proof",
    "references",
    "section",
    "source",
    "standard",
    "statement",
    "step",
    "subsection",
    "theorem",
    "version",
    "whole",
}

SYNONYMS = {
    "proposition": ["prop", "Prop"],
    "implication": ["implies", "arrow"],
    "negation": ["not", "Not"],
    "commutative": ["comm", "add_comm", "mul_comm", "commutative"],
    "associative": ["assoc", "add_assoc", "mul_assoc", "associative"],
    "identity": ["one", "zero", "identity", "left_id", "right_id"],
    "inverse": ["inv", "inverse", "neg", "mul_left_inv", "add_left_neg"],
    "distributive": ["distrib", "left_distrib", "right_distrib", "distributive"],
    "injective": ["injective", "Injective"],
    "surjective": ["surjective", "Surjective"],
    "bijective": ["bijective", "Bijective"],
    "subset": ["subset", "Subset", "subset_trans"],
    "union": ["union", "Union", "inter", "sup"],
    "intersection": ["inter", "intersection", "Inf"],
    "divisible": ["dvd", "divides", "Divides"],
    "prime": ["prime", "Prime"],
    "even": ["even", "Even"],
    "odd": ["odd", "Odd"],
    "bounded": ["bounded", "Bounded"],
    "continuous": ["continuous", "Continuous"],
    "differentiable": ["differentiable", "Differentiable", "deriv", "HasDerivAt"],
    "limit": ["limit", "tendsto", "Tendsto"],
    "compact": ["compact", "Compact"],
    "finite": ["finite", "Finite", "Fintype"],
    "monotone": ["monotone", "Monotone", "StrictMono", "StrictAnti"],
    "composition": ["comp", "Function.comp"],
    "type_variables": ["Type"],
    "order_relation": ["LE", "LE.le", "Preorder"],
    "extensionality": ["ext", "Set.ext", "funext", "propext"],
    "case_split": ["Or.elim", "Classical.byCases"],
    "natural_number": ["Nat"],
    "finite_sum": ["Finset.sum", "Finset.range", "Finset.sum_range_succ"],
    "arithmetic_normalization": ["ring_nf", "ring", "pow_two", "Nat.succ_eq_add_one"],
    "equivalence": ["equiv", "Equiv", "equivalence"],
    "isomorphism": ["iso", "Iso", "isomorphism"],
    "contradiction": ["False", "by_contra", "absurd"],
    "induction": ["induction", "Nat.rec", "Nat.recOn"],
}

KEYWORD_HINTS = set(SYNONYMS.keys()) | {
    "group",
    "ring",
    "field",
    "module",
    "homomorphism",
    "continuous",
    "differentiable",
    "compact",
    "closed",
    "open",
    "converges",
    "bounded",
    "integrable",
    "measurable",
    "monoid",
    "convex",
    "intersection",
    "nonempty",
    "cardinality",
    "radon",
    "helly",
    "colorful",
    "fractional",
    "euclidean",
    "dimension",
    "semiring",
    "ideal",
    "subgroup",
    "subset",
    "function",
    "equation",
    "inequality",
    "sum",
    "product",
    "prime",
    "divides",
}

PHRASE_HINTS = {
    "compact support",
    "compact convex",
    "finite set",
    "finite family",
    "finite intersection",
    "nonempty intersection",
    "open set",
    "closed set",
    "linearly independent",
    "measure zero",
    "convex sets",
    "convex subsets",
    "radon theorem",
    "helly theorem",
    "colorful helly",
    "fractional helly",
    "euclidean space",
    "well founded",
}

PREFERRED_DECLS = {
    "commutative": ["add_comm", "mul_comm"],
    "associative": ["add_assoc", "mul_assoc"],
    "proposition": ["Prop"],
    "implication": ["Function.comp"],
    "negation": ["Not"],
    "identity": ["one_mul", "mul_one", "zero_add", "add_zero"],
    "inverse": ["inv_mul_cancel", "mul_inv_cancel", "add_left_neg", "neg_add_cancel"],
    "injective": ["Function.Injective"],
    "surjective": ["Function.Surjective"],
    "bijective": ["Function.Bijective"],
    "subset": ["Set.Subset", "Set.Subset.trans"],
    "function": ["Function.comp", "id"],
    "union": ["Set.union_assoc", "Set.union_comm"],
    "intersection": ["Set.inter_assoc", "Set.inter_comm"],
    "divisible": ["Dvd.dvd"],
    "prime": ["Nat.Prime", "Prime"],
    "even": ["Even"],
    "odd": ["Odd"],
    "finite": ["Finite", "Fintype"],
    "monotone": ["Monotone", "StrictMono", "StrictAnti"],
    "composition": ["Function.comp"],
    "type_variables": ["Type"],
    "order_relation": ["LE.le", "Preorder"],
    "extensionality": ["Set.ext", "funext", "propext"],
    "case_split": ["Or.elim", "Classical.byCases"],
    "natural_number": ["Nat"],
    "finite_sum": ["Finset.sum", "Finset.range", "Finset.sum_range_succ"],
    "arithmetic_normalization": ["pow_two", "Nat.succ_eq_add_one"],
    "continuous": ["Continuous", "ContinuousAt"],
    "differentiable": ["Differentiable", "DifferentiableAt", "HasDerivAt"],
    "limit": ["Filter.Tendsto", "Tendsto"],
    "contradiction": ["False.elim", "absurd", "by_contradiction"],
    "induction": ["Nat.rec", "Nat.recOn"],
}


def apply_reviewed_ontology_overlay() -> None:
    """Overlay reviewed ontology policy onto the legacy concept mapper tables."""
    if (
        keyword_hints is None
        or load_profile is None
        or phrase_hints is None
        or preferred_decls is None
        or synonym_map is None
    ):
        return
    try:
        profile = load_profile()
    except Exception:
        return
    SYNONYMS.update(synonym_map(profile))
    KEYWORD_HINTS.update(keyword_hints(profile))
    KEYWORD_HINTS.update(SYNONYMS.keys())
    PHRASE_HINTS.update(phrase_hints(profile))
    PREFERRED_DECLS.update(preferred_decls(profile))


apply_reviewed_ontology_overlay()

MATHLIB_CONCEPT_MAPPER_SKILL = (
    "mathlib-concept-candidate-mapper/map_mathlib_concepts.py"
)
MATHLIB_CANDIDATE_VERIFIER_SKILL = "mathlib-candidate-verifier/map_mathlib_concepts.py"


def skill_name_for_run(*, verify_checks: bool) -> str:
    """Document the responsibility of ``skill_name_for_run``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return (
        MATHLIB_CANDIDATE_VERIFIER_SKILL
        if verify_checks
        else MATHLIB_CONCEPT_MAPPER_SKILL
    )


@dataclass
class Decl:
    """Document the responsibility of ``Decl``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/informal-proof-mathlib-concepts/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    name: str
    kind: str
    file: str
    line: int
    signature: str


@dataclass
class Match:
    """Document the responsibility of ``Match``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/informal-proof-mathlib-concepts/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    score: int
    decl: Decl


@dataclass
class ModuleRelevance:
    """Document the responsibility of ``ModuleRelevance``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathlib/informal-proof-mathlib-concepts/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    module: str
    score: int
    matched_terms: List[str]
    declaration_count: int


_REASONING_LOG_COUNTERS: Dict[str, int] = {}
_SOURCE_FILE_CACHE: Dict[str, List[str]] = {}
_QUALIFIED_DECL_CACHE: Dict[tuple[str, int, str], str] = {}


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


def _statement_hash(text: str, *, length: int = 12) -> str:
    """Document the responsibility of ``_statement_hash``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_statement_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest[:length]


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


def _augment_env_with_lean_path(
    env: Dict[str, str] | None = None,
) -> Dict[str, str]:
    """Document the responsibility of ``_augment_env_with_lean_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_augment_env_with_lean_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    updated = dict(os.environ if env is None else env)
    elan_bin = Path.home() / ".elan" / "bin"
    current_path = updated.get("PATH", "")
    if elan_bin.exists():
        path_parts = current_path.split(os.pathsep) if current_path else []
        if str(elan_bin) not in path_parts:
            updated["PATH"] = str(elan_bin) + (
                os.pathsep + current_path if current_path else ""
            )
    return updated


def _resolve_lake_executable(env: Dict[str, str] | None = None) -> str:
    """Document the responsibility of ``_resolve_lake_executable``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_resolve_lake_executable`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    updated = _augment_env_with_lean_path(env)
    found = shutil.which("lake", path=updated.get("PATH"))
    if found:
        return found
    elan_bin = Path.home() / ".elan" / "bin"
    for candidate in (elan_bin / "lake.exe", elan_bin / "lake"):
        if candidate.exists():
            return str(candidate)
    return "lake"


def resolve_mathlib_root(candidate: Path) -> Path:
    """Document the responsibility of ``resolve_mathlib_root``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``resolve_mathlib_root`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    repo_root = Path(__file__).resolve().parents[4]
    possible = [
        candidate.expanduser(),
        (Path.cwd() / candidate).resolve(),
        (repo_root / candidate).resolve(),
        (repo_root / ".lake" / "packages" / "mathlib" / "Mathlib").resolve(),
    ]
    for path in possible:
        if path.exists():
            return path.resolve()
    return candidate.expanduser().resolve()


def run_rg(mathlib_root: Path) -> Iterable[str]:
    """Document the responsibility of ``run_rg``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cmd = [
        "rg",
        "--no-heading",
        "--line-number",
        "--glob",
        "*.lean",
        DECL_PATTERN,
        str(mathlib_root),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "Failed to scan mathlib with rg")
    for line in proc.stdout.splitlines():
        if line:
            yield line


def parse_decl_line(raw: str, mathlib_root: Path) -> Decl | None:
    """Document the responsibility of ``parse_decl_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = raw.split(":", 2)
    if len(parts) != 3:
        return None
    file_path, line_s, signature = parts
    m = DECL_NAME_RE.match(signature.strip())
    if not m:
        return None
    kind, name = m.group(1), m.group(2)
    try:
        line = int(line_s)
    except ValueError:
        return None
    rel_file = Path(file_path).resolve().relative_to(mathlib_root.resolve()).as_posix()
    return Decl(
        name=name, kind=kind, file=rel_file, line=line, signature=signature.strip()
    )


def build_index(mathlib_root: Path) -> List[Decl]:
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
    decls: List[Decl] = []
    for raw in run_rg(mathlib_root):
        parsed = parse_decl_line(raw, mathlib_root)
        if parsed is not None:
            decls.append(parsed)
    return decls


def load_or_build_index(
    index_path: Path, mathlib_root: Path, rebuild: bool
) -> List[Decl]:
    """Document the responsibility of ``load_or_build_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if index_path.exists() and not rebuild:
        data = json.loads(index_path.read_text(encoding="utf-8"))
        decls: List[Decl] = []
        for item in data:
            normalized = dict(item)
            file_value = normalized.get("file")
            if isinstance(file_value, str):
                normalized["file"] = file_value.replace("\\", "/")
            decls.append(Decl(**normalized))
        return decls

    decls = build_index(mathlib_root)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps([d.__dict__ for d in decls], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return decls


def normalize_token(token: str) -> str:
    """Document the responsibility of ``normalize_token``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_token`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = token.strip().lower().strip("'")
    if normalized.endswith("'s"):
        normalized = normalized[:-2]
    elif normalized.endswith("s'"):
        normalized = normalized[:-1]
    return normalized


def read_source_lines(path: Path) -> List[str]:
    """Document the responsibility of ``read_source_lines``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    key = str(path.resolve())
    cached = _SOURCE_FILE_CACHE.get(key)
    if cached is not None:
        return cached
    lines = path.read_text(encoding="utf-8").splitlines()
    _SOURCE_FILE_CACHE[key] = lines
    return lines


def extract_source_excerpt(
    mathlib_root: Path,
    rel_file: str,
    line: int,
    *,
    context_before: int = 2,
    context_after: int = 6,
) -> str | None:
    """Document the responsibility of ``extract_source_excerpt``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_source_excerpt`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if rel_file.startswith("<") and rel_file.endswith(">"):
        return None
    source_path = mathlib_root / rel_file
    if not source_path.exists():
        return None
    lines = read_source_lines(source_path)
    if line <= 0 or line > len(lines):
        return None
    start = max(1, line - context_before)
    end = min(len(lines), line + context_after)
    excerpt_lines = [f"{idx:04d}: {lines[idx - 1]}" for idx in range(start, end + 1)]
    return "\n".join(excerpt_lines)


def source_ref(rel_file: str, line: int) -> str | None:
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
    if rel_file.startswith("<") and rel_file.endswith(">"):
        return None
    return f"{rel_file}:{line}" if line > 0 else rel_file


def module_to_rel_file(module: str) -> str | None:
    """Document the responsibility of ``module_to_rel_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_to_rel_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    normalized = module.strip()
    if not normalized or normalized.startswith("<"):
        return None
    if normalized.startswith("Mathlib."):
        normalized = normalized[len("Mathlib.") :]
    return normalized.replace(".", "/") + ".lean"


def qualify_decl_name(mathlib_root: Path, decl: Decl) -> str:
    """Document the responsibility of ``qualify_decl_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``qualify_decl_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if "." in decl.name or decl.file.startswith("<"):
        return decl.name
    cache_key = (decl.file, decl.line, decl.name)
    cached = _QUALIFIED_DECL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    source_path = mathlib_root / decl.file
    if not source_path.exists():
        _QUALIFIED_DECL_CACHE[cache_key] = decl.name
        return decl.name

    namespace_stack: List[str] = []
    frame_stack: List[tuple[str, str | None]] = []
    for idx, raw_line in enumerate(read_source_lines(source_path), start=1):
        stripped = re.sub(r"--.*$", "", raw_line).strip()
        namespace_match = re.match(r"^namespace\s+([A-Za-z0-9_.']+)\s*$", stripped)
        if namespace_match is not None:
            namespace_name = namespace_match.group(1)
            namespace_stack.append(namespace_name)
            frame_stack.append(("namespace", namespace_name))
        else:
            section_match = re.match(r"^section(?:\s+([A-Za-z0-9_.']+))?\s*$", stripped)
            if section_match is not None:
                frame_stack.append(("section", section_match.group(1)))
            else:
                end_match = re.match(r"^end(?:\s+([A-Za-z0-9_.']+))?\s*$", stripped)
                if end_match is not None and frame_stack:
                    end_name = end_match.group(1)
                    if end_name is None:
                        frame_type, frame_name = frame_stack.pop()
                        if frame_type == "namespace" and frame_name is not None:
                            namespace_stack.pop()
                    else:
                        while frame_stack:
                            frame_type, frame_name = frame_stack.pop()
                            if frame_type == "namespace" and frame_name is not None:
                                namespace_stack.pop()
                            if frame_name == end_name:
                                break
        if idx >= decl.line:
            break

    qualified = (
        ".".join(namespace_stack + [decl.name]) if namespace_stack else decl.name
    )
    _QUALIFIED_DECL_CACHE[cache_key] = qualified
    return qualified


def normalize_informal_text(proof_text: str) -> str:
    """Document the responsibility of ``normalize_informal_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_informal_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = proof_text
    document_match = re.search(
        r"\\begin\{document\}(.*?)\\end\{document\}",
        text,
        flags=re.DOTALL,
    )
    if document_match is not None:
        text = document_match.group(1)
    text = re.sub(r"(?<!\\)%.*", " ", text)
    for _ in range(4):
        text = re.sub(
            r"\\[A-Za-z]+(?:\*?)(?:\[[^\]]*\])?\{([^{}]*)\}",
            r" \1 ",
            text,
        )
    text = re.sub(r"\\begin\{[^{}]+\}|\\end\{[^{}]+\}", " ", text)
    text = re.sub(r"\\item\b", " ", text)
    text = re.sub(r"\\[A-Za-z]+(?:\*?)(?:\[[^\]]*\])?", " ", text)
    text = re.sub(r"[$\[\]\{\}_^&~]", " ", text)
    text = text.replace("\\", " ")
    return re.sub(r"\s+", " ", text).strip()


def concept_terms(concept: str) -> List[str]:
    """Document the responsibility of ``concept_terms``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``concept_terms`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tokens = [
        normalize_token(t) for t in re.findall(r"[A-Za-z][A-Za-z0-9_']*", concept)
    ]
    terms = set(tokens)
    for tok in tokens:
        for syn in SYNONYMS.get(tok, []):
            terms.add(syn.lower())
    if len(tokens) >= 2:
        terms.add("_".join(tokens))
    return sorted(t for t in terms if t and t not in STOPWORDS)


def extract_concepts(proof_text: str, limit: int = 12) -> List[str]:
    """Document the responsibility of ``extract_concepts``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_concepts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    proof_text = normalize_informal_text(proof_text)
    words = [
        normalize_token(t) for t in re.findall(r"[A-Za-z][A-Za-z0-9_']*", proof_text)
    ]
    words = [w for w in words if len(w) >= 4 and w not in STOPWORDS]
    freq = Counter(words)
    filtered_words = [w for w in words if (w in KEYWORD_HINTS or freq[w] >= 2)]
    if filtered_words:
        words = filtered_words
        freq = Counter(words)

    bigrams = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        if w1 == w2:
            continue
        if w1 in STOPWORDS or w2 in STOPWORDS:
            continue
        phrase = f"{w1} {w2}"
        if phrase in PHRASE_HINTS:
            bigrams.append(phrase)
    bigram_freq = Counter(bigrams)

    concepts: List[str] = []
    for bg, _ in bigram_freq.most_common(limit // 2):
        concepts.append(bg)
    for w, _ in freq.most_common(limit):
        if w not in concepts:
            concepts.append(w)
    return concepts[:limit]


def score_decl(decl: Decl, terms: Sequence[str]) -> tuple[int, List[str]]:
    """Document the responsibility of ``score_decl``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``score_decl`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    name_l = decl.name.lower()
    sig_l = decl.signature.lower()
    module = module_from_file(decl.file).lower()
    score = 0
    matched_terms = set()
    for term in terms:
        if term == name_l:
            score += 20
            matched_terms.add(term)
        if term in name_l:
            score += 8
            matched_terms.add(term)
        if term in sig_l:
            score += 3
            matched_terms.add(term)
        if term in module:
            score += 2
            matched_terms.add(term)
        if any(part == term for part in re.split(r"[._']", name_l)):
            score += 6
            matched_terms.add(term)
    if decl.kind in {"theorem", "lemma"}:
        score += 1
    if "." not in decl.name and "_" not in decl.name and decl.name.islower():
        # Local short names are often less reusable than namespaced/structured declarations.
        score -= 8
    return score, sorted(matched_terms)


def rank_modules(
    module_scores: Dict[str, List[int]],
    module_term_hits: Dict[str, set[str]],
    module_decl_counts: Dict[str, int],
    top_modules: int,
) -> List[ModuleRelevance]:
    """Document the responsibility of ``rank_modules``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``rank_modules`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    ranked: List[ModuleRelevance] = []
    for module, scores in module_scores.items():
        hits = sorted(module_term_hits[module])
        top_scores = sorted(scores, reverse=True)[:3]
        if not top_scores:
            continue
        # Prioritize modules containing the strongest matching declarations
        # rather than modules that merely accumulate many weak matches.
        blended_score = top_scores[0] * 5 + sum(top_scores[1:])
        blended_score += 4 * len(hits)
        blended_score += min(3, module_decl_counts.get(module, 0) // 200)
        ranked.append(
            ModuleRelevance(
                module=module,
                score=blended_score,
                matched_terms=hits,
                declaration_count=module_decl_counts.get(module, 0),
            )
        )
    ranked.sort(
        key=lambda item: (
            -item.score,
            -len(item.matched_terms),
            item.module,
        )
    )
    return ranked[:top_modules]


def preferred_matches(concept: str) -> List[Match]:
    """Document the responsibility of ``preferred_matches``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``preferred_matches`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    terms = set(concept_terms(concept))
    out: List[Match] = []
    for key, names in PREFERRED_DECLS.items():
        if key in terms:
            for i, name in enumerate(names):
                out.append(
                    Match(
                        score=100 - i,
                        decl=Decl(
                            name=name,
                            kind="hint",
                            file="<core/mathlib>",
                            line=0,
                            signature=name,
                        ),
                    )
                )
    return out


def dedupe_matches(matches: Sequence[Match]) -> List[Match]:
    """Document the responsibility of ``dedupe_matches``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``dedupe_matches`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen = set()
    out: List[Match] = []
    for m in matches:
        key = m.decl.name
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def map_concepts(
    concepts: Sequence[str],
    decls: Sequence[Decl],
    top_k: int,
    top_modules: int,
    module_rank_bonus: int,
) -> tuple[Dict[str, List[Match]], Dict[str, List[ModuleRelevance]]]:
    """Document the responsibility of ``map_concepts``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``map_concepts`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    out: Dict[str, List[Match]] = {}
    module_navigation: Dict[str, List[ModuleRelevance]] = {}
    module_decl_counts: Dict[str, int] = defaultdict(int)
    for decl in decls:
        module_decl_counts[module_from_file(decl.file)] += 1

    for concept in concepts:
        terms = concept_terms(concept)
        scored: List[Match] = preferred_matches(concept)
        base_matches: List[tuple[int, Decl, str]] = []
        module_scores: Dict[str, List[int]] = defaultdict(list)
        module_term_hits: Dict[str, set[str]] = defaultdict(set)

        for decl in decls:
            s, matched_terms = score_decl(decl, terms)
            if s <= 0:
                continue
            module = module_from_file(decl.file)
            base_matches.append((s, decl, module))
            module_scores[module].append(s)
            module_term_hits[module].update(matched_terms)

        ranked_modules = rank_modules(
            module_scores=module_scores,
            module_term_hits=module_term_hits,
            module_decl_counts=module_decl_counts,
            top_modules=top_modules,
        )
        module_navigation[concept] = ranked_modules
        module_rank = {item.module: i + 1 for i, item in enumerate(ranked_modules)}

        for base_score, decl, module in base_matches:
            bonus = 0
            rank = module_rank.get(module)
            if rank is not None:
                bonus = max(0, module_rank_bonus - rank + 1)
            scored.append(Match(score=base_score + bonus, decl=decl))

        scored.sort(
            key=lambda m: (
                -m.score,
                len(m.decl.name),
                m.decl.name,
            )
        )
        out[concept] = dedupe_matches(scored)[:top_k]
    return out, module_navigation


def module_from_file(rel_file: str) -> str:
    """Document the responsibility of ``module_from_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_from_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if rel_file.startswith("<") and rel_file.endswith(">"):
        placeholder = rel_file[1:-1]
        if placeholder == "core/mathlib":
            return "Mathlib"
        return placeholder
    # Analysis/Convex/Radon.lean -> Mathlib.Analysis.Convex.Radon
    module = rel_file.replace(".lean", "").replace("\\", "/").replace("/", ".")
    if not module.startswith("Mathlib."):
        module = f"Mathlib.{module}"
    return module


def parse_lean_errors(output: str) -> List[str]:
    """Document the responsibility of ``parse_lean_errors``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    errors: List[str] = []
    for line in output.splitlines():
        match = LEAN_ERROR_RE.match(line.strip())
        if match is None:
            continue
        errors.append(
            f"line {match.group('line')}:{match.group('col')}: {match.group('msg').strip()}"
        )
    return errors


def verify_check_with_lean(
    decl_name: str,
    lean_workdir: Path,
    timeout_sec: int,
) -> tuple[bool, List[str]]:
    """Document the responsibility of ``verify_check_with_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    scratch_dir = lean_workdir / "artifacts" / "tmp" / "mathlib_decl_checks"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    lean_env = _augment_env_with_lean_path()
    lake_executable = _resolve_lake_executable(lean_env)
    scratch_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".lean",
            prefix="check_",
            dir=scratch_dir,
            delete=False,
        ) as tmp:
            tmp.write("import Mathlib\n")
            tmp.write(f"#check {decl_name}\n")
            scratch_path = Path(tmp.name)

        proc = subprocess.run(
            [lake_executable, "env", "lean", str(scratch_path)],
            cwd=lean_workdir,
            env=lean_env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, [f"timeout after {timeout_sec}s while checking `{decl_name}`"]
    except FileNotFoundError as exc:
        return False, [f"failed to run lake/lean: {exc}"]
    finally:
        if scratch_path is not None:
            try:
                scratch_path.unlink()
            except OSError:
                pass

    if proc.returncode == 0:
        return True, []

    combined = "\n".join(
        part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip()
    )
    errors = parse_lean_errors(combined)
    if errors:
        return False, errors
    return False, [
        combined or f"`lake env lean` failed with exit code {proc.returncode}"
    ]


def verify_checks_with_lean(
    decl_names: Sequence[str],
    *,
    lean_workdir: Path,
    timeout_sec: int,
) -> Dict[str, tuple[bool, List[str]]]:
    """Document the responsibility of ``verify_checks_with_lean``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    ordered_names: List[str] = []
    seen: set[str] = set()
    for name in decl_names:
        stripped = name.strip()
        if not stripped or stripped in seen:
            continue
        seen.add(stripped)
        ordered_names.append(stripped)
    if not ordered_names:
        return {}

    scratch_dir = lean_workdir / "artifacts" / "tmp" / "mathlib_decl_checks"
    scratch_dir.mkdir(parents=True, exist_ok=True)

    lean_env = _augment_env_with_lean_path()
    lake_executable = _resolve_lake_executable(lean_env)
    scratch_path: Path | None = None
    check_line_to_name: Dict[int, str] = {}
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            suffix=".lean",
            prefix="check_batch_",
            dir=scratch_dir,
            delete=False,
        ) as tmp:
            tmp.write("import Mathlib\n")
            line_no = 1
            for decl_name in ordered_names:
                tmp.write(f"-- VERIFY: {decl_name}\n")
                line_no += 1
                tmp.write(f"#check {decl_name}\n")
                line_no += 1
                check_line_to_name[line_no] = decl_name
            scratch_path = Path(tmp.name)

        proc = subprocess.run(
            [lake_executable, "env", "lean", str(scratch_path)],
            cwd=lean_workdir,
            env=lean_env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            decl_name: (
                False,
                [f"timeout after {timeout_sec}s while checking `{decl_name}`"],
            )
            for decl_name in ordered_names
        }
    except FileNotFoundError as exc:
        return {
            decl_name: (False, [f"failed to run lake/lean: {exc}"])
            for decl_name in ordered_names
        }
    finally:
        if scratch_path is not None:
            try:
                scratch_path.unlink()
            except OSError:
                pass

    if proc.returncode == 0:
        return {decl_name: (True, []) for decl_name in ordered_names}

    combined = "\n".join(
        part.strip() for part in (proc.stdout, proc.stderr) if part and part.strip()
    )
    errors_by_decl: Dict[str, List[str]] = {
        decl_name: [] for decl_name in ordered_names
    }
    unmatched_errors: List[str] = []
    for line in combined.splitlines():
        match = LEAN_ERROR_RE.match(line.strip())
        if match is None:
            continue
        line_no = int(match.group("line"))
        message = (
            f"line {match.group('line')}:{match.group('col')}: "
            f"{match.group('msg').strip()}"
        )
        decl_name = check_line_to_name.get(line_no)
        if decl_name is None:
            unmatched_errors.append(message)
            continue
        errors_by_decl.setdefault(decl_name, []).append(message)

    if unmatched_errors and not any(errors_by_decl.values()):
        return {decl_name: (False, unmatched_errors) for decl_name in ordered_names}

    results: Dict[str, tuple[bool, List[str]]] = {}
    for decl_name in ordered_names:
        errors = errors_by_decl.get(decl_name, [])
        results[decl_name] = (len(errors) == 0, errors)
    return results


def parse_args() -> argparse.Namespace:
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
        "--proof-file", type=Path, help="Path to file containing informal proof text"
    )
    parser.add_argument("--proof-text", type=str, help="Inline informal proof text")
    parser.add_argument(
        "--concept",
        action="append",
        default=[],
        help="Concept to map (repeatable). If omitted, concepts are auto-extracted from proof text.",
    )
    parser.add_argument(
        "--top-k", type=int, default=8, help="Top candidates per concept"
    )
    parser.add_argument(
        "--mathlib-root",
        type=Path,
        default=Path(".lake/packages/mathlib/Mathlib"),
        help="Path to Mathlib source root",
    )
    parser.add_argument(
        "--index-file",
        type=Path,
        default=Path("artifacts/mathlib_decl_index.json"),
        help="Declaration index JSON cache path",
    )
    parser.add_argument(
        "--top-modules",
        type=int,
        default=12,
        help="How many relevant mathlib modules to keep per concept for navigation/ranking.",
    )
    parser.add_argument(
        "--show-modules",
        type=int,
        default=4,
        help="How many relevant modules to print per concept in text mode (0 disables).",
    )
    parser.add_argument(
        "--module-rank-bonus",
        type=int,
        default=6,
        help="Rank-based bonus added to declaration scores from top relevant modules.",
    )
    parser.add_argument(
        "--rebuild-index", action="store_true", help="Rebuild declaration index"
    )
    parser.add_argument(
        "--verify-checks",
        action="store_true",
        help="Run `lake env lean` #check verification for each candidate and include errors.",
    )
    parser.add_argument(
        "--lean-workdir",
        type=Path,
        default=Path("."),
        help="Project directory where `lake env lean` is executed for verification.",
    )
    parser.add_argument(
        "--verify-timeout-sec",
        type=int,
        default=60,
        help="Timeout in seconds for each verification call.",
    )
    parser.add_argument(
        "--verify-max-concepts",
        type=int,
        default=6,
        help="Maximum number of ranked concepts whose top candidates are verified.",
    )
    parser.add_argument(
        "--verify-max-candidates",
        type=int,
        default=3,
        help="Maximum number of ranked candidates verified per concept.",
    )
    parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        help="Optional JSONL file where structured reasoning events are appended.",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON")
    return parser.parse_args()


def read_proof_text(args: argparse.Namespace) -> str:
    """Document the responsibility of ``read_proof_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if args.proof_text:
        return args.proof_text
    if args.proof_file:
        return args.proof_file.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return ""


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
    args = parse_args()
    skill_name = skill_name_for_run(verify_checks=args.verify_checks)
    write_reasoning_event = make_reasoning_logger(args.reasoning_log_file)

    def hook_id_for_step(step: str) -> str:
        """Document the responsibility of ``main.hook_id_for_step``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``main.hook_id_for_step`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if step == "concept_mapping_verify_result":
            return "mathlib.verify"
        return "mathlib.discovery"

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
                "skill": skill_name,
                "hook_id": hook_id_for_step(step),
                **payload,
            },
        )

    proof_text = read_proof_text(args)
    explicit_concepts = list(args.concept)
    mathlib_root = resolve_mathlib_root(args.mathlib_root)
    trace_event(
        "concept_mapping_cli_start",
        {
            "skill": skill_name,
            "proof_text_hash": None if not proof_text else _statement_hash(proof_text),
            "proof_text_length": len(proof_text),
            "proof_file": None if args.proof_file is None else str(args.proof_file),
            "explicit_concepts": explicit_concepts,
            "top_k": args.top_k,
            "top_modules": args.top_modules,
            "module_rank_bonus": args.module_rank_bonus,
            "verify_checks": args.verify_checks,
            "verify_timeout_sec": args.verify_timeout_sec,
            "verify_max_concepts": args.verify_max_concepts,
            "verify_max_candidates": args.verify_max_candidates,
            "requested_mathlib_root": str(args.mathlib_root),
            "resolved_mathlib_root": str(mathlib_root),
            "index_file": str(args.index_file),
        },
    )

    if not mathlib_root.exists():
        trace_event(
            "concept_mapping_input_error",
            {
                "skill": skill_name,
                "error": "mathlib_root_missing",
                "mathlib_root": str(mathlib_root),
                "requested_mathlib_root": str(args.mathlib_root),
            },
        )
        print(
            f"mathlib root not found at {mathlib_root}. Run `lake update` in the project first.",
            file=sys.stderr,
        )
        return 2

    concepts = explicit_concepts
    if not concepts:
        if not proof_text.strip():
            trace_event(
                "concept_mapping_input_error",
                {
                    "skill": skill_name,
                    "error": "missing_concepts_and_proof_text",
                },
            )
            print(
                "No concepts provided and no proof text found. Use --concept or --proof-file/--proof-text.",
                file=sys.stderr,
            )
            return 2
        concepts = extract_concepts(proof_text)
        trace_event(
            "concept_mapping_concepts_extracted",
            {
                "skill": skill_name,
                "concepts": concepts,
                "concept_count": len(concepts),
            },
        )
    else:
        trace_event(
            "concept_mapping_concepts_provided",
            {
                "skill": skill_name,
                "concepts": concepts,
                "concept_count": len(concepts),
            },
        )

    used_cached_index = args.index_file.exists() and not args.rebuild_index
    decls = load_or_build_index(args.index_file, mathlib_root, args.rebuild_index)
    trace_event(
        "concept_mapping_index_loaded",
        {
            "skill": skill_name,
            "index_file": str(args.index_file),
            "used_cached_index": used_cached_index,
            "declaration_count": len(decls),
        },
    )
    mapping, module_navigation = map_concepts(
        concepts,
        decls,
        top_k=args.top_k,
        top_modules=args.top_modules,
        module_rank_bonus=args.module_rank_bonus,
    )
    for concept in concepts:
        relevant_modules = module_navigation.get(concept, [])
        matches = mapping.get(concept, [])
        trace_event(
            "concept_mapping_concept_ranked",
            {
                "skill": skill_name,
                "concept": concept,
                "terms": concept_terms(concept),
                "relevant_modules": [
                    {
                        "rank": idx + 1,
                        "module": item.module,
                        "import": item.module,
                        "source_path": (
                            None
                            if module_to_rel_file(item.module) is None
                            else str(
                                (
                                    mathlib_root
                                    / (module_to_rel_file(item.module) or "")
                                ).resolve()
                            )
                        ),
                        "source_ref": module_to_rel_file(item.module),
                        "score": item.score,
                        "matched_terms": item.matched_terms,
                        "declaration_count": item.declaration_count,
                    }
                    for idx, item in enumerate(relevant_modules)
                ],
                "top_candidates": [
                    {
                        "rank": idx + 1,
                        "name": match.decl.name,
                        "qualified_name": qualify_decl_name(mathlib_root, match.decl),
                        "kind": match.decl.kind,
                        "score": match.score,
                        "module": module_from_file(match.decl.file),
                        "import": module_from_file(match.decl.file),
                        "file": match.decl.file,
                        "line": match.decl.line,
                        "source_ref": source_ref(match.decl.file, match.decl.line),
                    }
                    for idx, match in enumerate(matches)
                ],
            },
        )

    verify_cache: Dict[str, tuple[bool, List[str]]] = {}
    lean_workdir = args.lean_workdir.resolve()
    if args.verify_checks and not lean_workdir.exists():
        trace_event(
            "concept_mapping_input_error",
            {
                "skill": skill_name,
                "error": "lean_workdir_missing",
                "lean_workdir": str(lean_workdir),
            },
        )
        print(
            f"lean workdir not found at {lean_workdir}.",
            file=sys.stderr,
        )
        return 2

    if args.verify_checks:
        scheduled_decl_names: List[str] = []
        for concept_index, (_, matches) in enumerate(mapping.items()):
            if concept_index >= args.verify_max_concepts:
                break
            for match in matches[: args.verify_max_candidates]:
                scheduled_decl_names.append(qualify_decl_name(mathlib_root, match.decl))
        verify_cache = verify_checks_with_lean(
            scheduled_decl_names,
            lean_workdir=lean_workdir,
            timeout_sec=args.verify_timeout_sec,
        )
        for decl_name, (check_ok, errors) in verify_cache.items():
            trace_event(
                "concept_mapping_verify_result",
                {
                    "skill": skill_name,
                    "decl_name": decl_name,
                    "check_ok": check_ok,
                    "check_errors": errors,
                    "lean_workdir": str(lean_workdir),
                },
            )

    def get_verify_result(decl_name: str) -> tuple[bool, List[str]]:
        """Document the responsibility of ``main.get_verify_result``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if decl_name not in verify_cache:
            verify_cache[decl_name] = verify_check_with_lean(
                decl_name,
                lean_workdir=lean_workdir,
                timeout_sec=args.verify_timeout_sec,
            )
            check_ok, errors = verify_cache[decl_name]
            trace_event(
                "concept_mapping_verify_result",
                {
                    "skill": skill_name,
                    "decl_name": decl_name,
                    "check_ok": check_ok,
                    "check_errors": errors,
                    "lean_workdir": str(lean_workdir),
                },
            )
        return verify_cache[decl_name]

    if args.json:
        payload = {}
        for concept_index, (concept, matches) in enumerate(mapping.items()):
            ranked_modules = module_navigation.get(concept, [])
            module_lookup = {item.module: item for item in ranked_modules}
            module_rank = {item.module: i + 1 for i, item in enumerate(ranked_modules)}
            rows = []
            for match_index, m in enumerate(matches):
                module = module_from_file(m.decl.file)
                module_info = module_lookup.get(module)
                qualified_name = qualify_decl_name(mathlib_root, m.decl)
                source_path = None
                source_excerpt_text = None
                if not (m.decl.file.startswith("<") and m.decl.file.endswith(">")):
                    source_path = str((mathlib_root / m.decl.file).resolve())
                    source_excerpt_text = extract_source_excerpt(
                        mathlib_root,
                        m.decl.file,
                        m.decl.line,
                    )
                row = {
                    "score": m.score,
                    "name": m.decl.name,
                    "qualified_name": qualified_name,
                    "kind": m.decl.kind,
                    "file": m.decl.file,
                    "line": m.decl.line,
                    "module": module,
                    "import": module,
                    "signature": m.decl.signature,
                    "source_path": source_path,
                    "source_ref": source_ref(m.decl.file, m.decl.line),
                    "source_excerpt": source_excerpt_text,
                    "module_rank": module_rank.get(module),
                    "module_relevance": (
                        None if module_info is None else module_info.score
                    ),
                    "module_matched_terms": (
                        [] if module_info is None else module_info.matched_terms
                    ),
                }
                should_verify = (
                    args.verify_checks
                    and concept_index < args.verify_max_concepts
                    and match_index < args.verify_max_candidates
                )
                if should_verify:
                    check_ok, errors = get_verify_result(qualified_name)
                    row["check_ok"] = check_ok
                    row["check_errors"] = errors
                rows.append(row)
            payload[concept] = {
                "relevant_modules": [
                    {
                        "rank": i + 1,
                        "module": item.module,
                        "import": item.module,
                        "source_path": (
                            None
                            if module_to_rel_file(item.module) is None
                            else str(
                                (
                                    mathlib_root
                                    / (module_to_rel_file(item.module) or "")
                                ).resolve()
                            )
                        ),
                        "source_ref": module_to_rel_file(item.module),
                        "score": item.score,
                        "matched_terms": item.matched_terms,
                        "declaration_count": item.declaration_count,
                    }
                    for i, item in enumerate(ranked_modules)
                ],
                "candidates": rows,
            }
        trace_event(
            "concept_mapping_output_emitted",
            {
                "skill": skill_name,
                "output_format": "json",
                "concept_count": len(payload),
                "verified_declaration_count": len(verify_cache),
            },
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    trace_event(
        "concept_mapping_output_emitted",
        {
            "skill": skill_name,
            "output_format": "text",
            "concept_count": len(mapping),
            "verified_declaration_count": len(verify_cache),
        },
    )
    print("Concept -> candidate mathlib declarations")
    for concept_index, (concept, matches) in enumerate(mapping.items()):
        print(f"\n[{concept}]")
        relevant_modules = module_navigation.get(concept, [])
        if args.show_modules > 0 and relevant_modules:
            print("  relevant modules:")
            for idx, item in enumerate(relevant_modules[: args.show_modules], start=1):
                terms = ", ".join(item.matched_terms[:5]) if item.matched_terms else "-"
                module_rel_file = module_to_rel_file(item.module)
                print(
                    "    "
                    f"{idx}. {item.module} "
                    f"[score={item.score}, decls={item.declaration_count}, terms={terms}]"
                )
                if module_rel_file is not None:
                    print(f"       source: {module_rel_file}")
        if not matches:
            print("  (no candidates found)")
            continue
        module_rank = {item.module: i + 1 for i, item in enumerate(relevant_modules)}
        for idx, match in enumerate(matches, start=1):
            d = match.decl
            module = module_from_file(d.file)
            qualified_name = qualify_decl_name(mathlib_root, d)
            location = d.file if d.line <= 0 else f"{d.file}:{d.line}"
            print(f"  {idx}. {d.name} ({d.kind}) [score={match.score}]  {location}")
            if qualified_name != d.name:
                print(f"     qualified_name: {qualified_name}")
            print(f"     module: {module}")
            print(f"     import: {module}")
            if module in module_rank:
                print(f"     module_rank: {module_rank[module]}")
            print(f"     #check {qualified_name}")
            should_verify = (
                args.verify_checks
                and concept_index < args.verify_max_concepts
                and (idx - 1) < args.verify_max_candidates
            )
            if should_verify:
                check_ok, errors = get_verify_result(qualified_name)
                print(f"     lean_check: {'ok' if check_ok else 'error'}")
                if not check_ok:
                    for err in errors:
                        print(f"       - {err}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

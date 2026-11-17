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

"""Generate repository-browsable Markdown docs for Mathformer Lean modules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import os
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "mathformer-library-docs-generator"
HOOK_ID = "library.documentation"
DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance)\s+([^\s(:{]+)"
)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*(?:--.*)?$")
NAMESPACE_RE = re.compile(r"^\s*namespace\s+([A-Za-z0-9_.']+)\s*$")
END_RE = re.compile(r"^\s*end(?:\s+([A-Za-z0-9_.']+))?\s*$")
SOURCE_TAG_RE = re.compile(
    r"^(Original source|Generated note|Generated equivalent)\s*\((NL|LaTeX)\):\s*(.*)$"
)
MATH_SYMBOL_RE = re.compile(
    r"(\\[A-Za-z]+|[_^{}=<>≤≥∈∀∃]|\\le|\\ge|\\to|\\mathbb|\\mathrm)"
)


@dataclass
class DocComment:
    """Document the responsibility of ``DocComment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathformerlib/mathformer-library-docs-generator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    start_line: int
    end_line: int
    raw: str
    body: str


@dataclass
class Declaration:
    """Document the responsibility of ``Declaration``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathformerlib/mathformer-library-docs-generator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    kind: str
    name: str
    qualified_name: str
    line: int
    code: str
    comment: Optional[DocComment]


@dataclass
class ModuleDoc:
    """Document the responsibility of ``ModuleDoc``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/mathformerlib/mathformer-library-docs-generator/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    module: str
    path: Path
    rel_path: str
    sha256: str
    imports: List[str]
    module_comment: Optional[DocComment]
    declarations: List[Declaration]
    status: str


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


def anchor(text: str) -> str:
    """Document the responsibility of ``anchor``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``anchor`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    value = re.sub(r"[^A-Za-z0-9 _.-]+", "", text).strip().lower()
    value = re.sub(r"[\s_.]+", "-", value)
    return value or "item"


def module_page_name(module: str) -> str:
    """Document the responsibility of ``module_page_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``module_page_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"{module.replace('.', '/')}.md"


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


def parse_imports(lines: Sequence[str]) -> List[str]:
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
    for raw in lines:
        match = IMPORT_RE.match(raw)
        if match is None:
            continue
        imports.extend(part for part in match.group(1).split() if part)
    return imports


def strip_comment_delimiters(raw_lines: Sequence[str]) -> str:
    """Document the responsibility of ``strip_comment_delimiters``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_comment_delimiters`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not raw_lines:
        return ""
    lines = list(raw_lines)
    lines[0] = re.sub(r"^\s*/-+!?\s?", "", lines[0])
    lines[-1] = re.sub(r"\s*-+/\s*$", "", lines[-1])
    return "\n".join(line.rstrip() for line in lines).strip()


def find_doc_comments(lines: Sequence[str]) -> List[DocComment]:
    """Document the responsibility of ``find_doc_comments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    comments: List[DocComment] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].lstrip()
        if not (stripped.startswith("/--") or stripped.startswith("/-!")):
            i += 1
            continue
        start = i
        raw_lines = [lines[i]]
        while i < len(lines) and "-/" not in lines[i]:
            i += 1
            if i < len(lines):
                raw_lines.append(lines[i])
        end = i
        raw = "\n".join(raw_lines)
        comments.append(
            DocComment(
                start_line=start + 1,
                end_line=end + 1,
                raw=raw,
                body=strip_comment_delimiters(raw_lines),
            )
        )
        i += 1
    return comments


def find_attached_comment(
    declaration_line: int, comments: Sequence[DocComment], lines: Sequence[str]
) -> Optional[DocComment]:
    """Document the responsibility of ``find_attached_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for comment in comments:
        if comment.end_line >= declaration_line:
            continue
        between = lines[comment.end_line : declaration_line - 1]
        if all(not line.strip() for line in between):
            return comment
    return None


def parse_declarations(
    lines: Sequence[str], comments: Sequence[DocComment]
) -> List[Declaration]:
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
    namespace_stack: List[str] = []
    decl_starts: List[Tuple[int, str, str, str]] = []
    for index, raw in enumerate(lines, 1):
        stripped = re.sub(r"--.*$", "", raw).strip()
        namespace_match = NAMESPACE_RE.match(stripped)
        if namespace_match is not None:
            namespace_stack.append(namespace_match.group(1))
            continue
        end_match = END_RE.match(stripped)
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
        decl_starts.append((index, kind, name, qualified))

    declarations: List[Declaration] = []
    comment_by_decl_line: Dict[int, Optional[DocComment]] = {
        line: find_attached_comment(line, comments, lines) for line, *_ in decl_starts
    }
    attached_comment_starts = {
        comment.start_line
        for comment in comment_by_decl_line.values()
        if comment is not None
    }
    for pos, (line, kind, name, qualified) in enumerate(decl_starts):
        next_boundary = len(lines) + 1
        if pos + 1 < len(decl_starts):
            next_line = decl_starts[pos + 1][0]
            next_comment = comment_by_decl_line.get(next_line)
            next_boundary = (
                next_comment.start_line if next_comment is not None else next_line
            )
        later_attached = [start for start in attached_comment_starts if start > line]
        if later_attached:
            next_boundary = min(next_boundary, min(later_attached))
        code_lines = lines[line - 1 : max(line, next_boundary - 1)]
        declarations.append(
            Declaration(
                kind=kind,
                name=name,
                qualified_name=qualified,
                line=line,
                code="\n".join(code_lines).rstrip(),
                comment=comment_by_decl_line[line],
            )
        )
    return declarations


def load_registry_statuses(registry_file: Optional[Path]) -> Dict[str, str]:
    """Document the responsibility of ``load_registry_statuses``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if registry_file is None:
        return {}
    path = (REPO_ROOT / registry_file).resolve()
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    statuses: Dict[str, str] = {}
    for module in payload.get("modules", []):
        module_name = module.get("module")
        status = module.get("status")
        if isinstance(module_name, str) and isinstance(status, str):
            statuses[module_name] = status
    return statuses


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


def scan_module(path: Path, registry_statuses: Dict[str, str]) -> ModuleDoc:
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
    lines = text.splitlines()
    comments = find_doc_comments(lines)
    declarations = parse_declarations(lines, comments)
    module_comment = None
    for comment in comments:
        if comment.raw.lstrip().startswith("/-!"):
            module_comment = comment
            break
    module = module_from_path(path)
    status = registry_statuses.get(module)
    if status is None:
        status = "accepted" if rel(path).startswith("MathformerLib") else "candidate"
    return ModuleDoc(
        module=module,
        path=path,
        rel_path=rel(path),
        sha256=file_sha256(path),
        imports=parse_imports(lines),
        module_comment=module_comment,
        declarations=declarations,
        status=status,
    )


def split_tagged_comment(body: str) -> Dict[str, List[str]]:
    """Document the responsibility of ``split_tagged_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_tagged_comment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    sections: Dict[str, List[str]] = {
        "original_nl": [],
        "original_latex": [],
        "generated_nl": [],
        "generated_latex": [],
        "other": [],
    }
    current = "other"
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if sections[current]:
                sections[current].append("")
            continue
        match = SOURCE_TAG_RE.match(line)
        if match is not None:
            tag, kind, remainder = match.groups()
            if tag == "Original source" and kind == "NL":
                current = "original_nl"
            elif tag == "Original source" and kind == "LaTeX":
                current = "original_latex"
            elif tag == "Generated note" and kind == "NL":
                current = "generated_nl"
            elif tag in {"Generated note", "Generated equivalent"} and kind == "LaTeX":
                current = "generated_latex"
            else:
                current = "other"
            if remainder:
                sections[current].append(remainder)
            continue
        sections[current].append(line)
    return {
        key: trim_blank(value) for key, value in sections.items() if trim_blank(value)
    }


def trim_blank(lines: Sequence[str]) -> List[str]:
    """Document the responsibility of ``trim_blank``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``trim_blank`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    values = list(lines)
    while values and not values[0].strip():
        values.pop(0)
    while values and not values[-1].strip():
        values.pop()
    return values


def prose(lines: Sequence[str]) -> str:
    """Document the responsibility of ``prose``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``prose`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    paragraphs: List[str] = []
    current: List[str] = []
    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line.strip())
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def latex_candidates(lines: Sequence[str]) -> List[str]:
    """Document the responsibility of ``latex_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``latex_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = prose(lines)
    candidates = [item.strip("` .") for item in re.findall(r"`([^`]+)`", text)]
    if not candidates and MATH_SYMBOL_RE.search(text):
        candidates = [text.strip()]
    return [item for item in candidates if item]


def render_comment(comment: Optional[DocComment]) -> List[str]:
    """Document the responsibility of ``render_comment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if comment is None or not comment.body.strip():
        return []
    sections = split_tagged_comment(comment.body)
    lines: List[str] = []
    if "original_nl" in sections:
        lines.extend(["**Original Source**", "", prose(sections["original_nl"]), ""])
    if "original_latex" in sections:
        lines.extend(["**Original LaTeX**", "", "```latex"])
        lines.extend(sections["original_latex"])
        lines.extend(["```", ""])
        for candidate in latex_candidates(sections["original_latex"])[:3]:
            lines.extend(["$$", candidate, "$$", ""])
    if "generated_nl" in sections:
        lines.extend(["**Generated Notes**", "", prose(sections["generated_nl"]), ""])
    if "generated_latex" in sections:
        lines.extend(["**Generated LaTeX**", "", "```latex"])
        lines.extend(sections["generated_latex"])
        lines.extend(["```", ""])
        for candidate in latex_candidates(sections["generated_latex"])[:3]:
            lines.extend(["$$", candidate, "$$", ""])
    if "other" in sections:
        lines.extend(["**Comment**", "", prose(sections["other"]), ""])
    return lines


def render_module_page(module: ModuleDoc, output_dir: Path) -> str:
    """Document the responsibility of ``render_module_page``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    page_file = output_dir / "modules" / module_page_name(module.module)
    index_link = relative_link(page_file, output_dir / "INDEX.md")
    source_link = relative_link(page_file, REPO_ROOT / module.rel_path)
    lines = [
        f"# `{module.module}`",
        "",
        f"[Back to index]({index_link})",
        "",
        "## Metadata",
        "",
        f"- Source: [{module.rel_path}]({source_link})",
        f"- Status: `{module.status}`",
        f"- SHA-256: `{module.sha256}`",
        f"- Declarations: `{len(module.declarations)}`",
        "",
    ]
    if module.imports:
        lines.extend(["## Imports", "", "```lean"])
        lines.extend(f"import {item}" for item in module.imports)
        lines.extend(["```", ""])
    if module.module_comment is not None:
        lines.extend(["## Module Source Notes", ""])
        lines.extend(render_comment(module.module_comment))
    if module.declarations:
        lines.extend(["## Declarations", ""])
        for decl in module.declarations:
            lines.append(
                f"- [`{decl.qualified_name}`](#{anchor(decl.qualified_name)}) "
                f"({decl.kind}, line {decl.line})"
            )
        lines.append("")
    for decl in module.declarations:
        lines.extend(
            [
                # Match the stable slugs used by the index and declaration list.
                f'<a id="{anchor(decl.qualified_name)}"></a>',
                "",
                f"## `{decl.qualified_name}`",
                "",
                f"- Kind: `{decl.kind}`",
                f"- Source line: [{module.rel_path}:{decl.line}]({source_link}#L{decl.line})",
                "",
            ]
        )
        lines.extend(render_comment(decl.comment))
        lines.extend(["**Lean**", "", "```lean", decl.code, "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def relative_link(from_file: Path, to_file: Path) -> str:
    """Document the responsibility of ``relative_link``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``relative_link`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return Path(os.path.relpath(to_file, from_file.parent)).as_posix()


def render_index(modules: Sequence[ModuleDoc], output_dir: Path) -> str:
    """Document the responsibility of ``render_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    status_counts: Dict[str, int] = {}
    for module in modules:
        status_counts[module.status] = status_counts.get(module.status, 0) + 1
    declaration_count = sum(len(module.declarations) for module in modules)
    theorem_like_count = sum(
        1
        for module in modules
        for decl in module.declarations
        if decl.kind in {"theorem", "lemma"}
    )
    lines = [
        "# Mathformer Library",
        "",
        "Generated Markdown documentation for Mathformer Lean modules.",
        "",
        "## Summary",
        "",
        f"- Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Modules: `{len(modules)}`",
        f"- Declarations: `{declaration_count}`",
        f"- Theorem-like declarations: `{theorem_like_count}`",
        f"- Status counts: `{json.dumps(status_counts, sort_keys=True)}`",
        "",
        "## Modules",
        "",
        "| Module | Status | Declarations | Lean Source |",
        "| --- | --- | ---: | --- |",
    ]
    for module in sorted(modules, key=lambda item: item.module):
        page = output_dir / "modules" / module_page_name(module.module)
        page_link = relative_link(output_dir / "INDEX.md", page)
        source_link = relative_link(
            output_dir / "INDEX.md", REPO_ROOT / module.rel_path
        )
        lines.append(
            f"| [`{module.module}`]({page_link}) | `{module.status}` | "
            f"{len(module.declarations)} | [{module.rel_path}]({source_link}) |"
        )
    lines.extend(["", "## Declarations", ""])
    current_module = None
    for module in sorted(modules, key=lambda item: item.module):
        if current_module != module.module:
            current_module = module.module
            page = output_dir / "modules" / module_page_name(module.module)
            page_link = relative_link(output_dir / "INDEX.md", page)
            lines.extend(["", f"### [`{module.module}`]({page_link})", ""])
        for decl in module.declarations:
            page = output_dir / "modules" / module_page_name(module.module)
            decl_link = f"{relative_link(output_dir / 'INDEX.md', page)}#{anchor(decl.qualified_name)}"
            lines.append(f"- [`{decl.qualified_name}`]({decl_link}) `{decl.kind}`")
    return "\n".join(lines).rstrip() + "\n"


def build_docs(
    roots: Sequence[Path],
    output_dir: Path,
    registry_file: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_docs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    modules = collect_docs(roots, registry_file)
    return publish_docs(roots, output_dir, modules)


def collect_docs(roots, registry_file):
    """Collect in native root/file order, carrying discovery deduplication."""
    registry_statuses = load_registry_statuses(registry_file)
    return [scan_module(path, registry_statuses) for path in iter_lean_files(roots)]


def publish_docs(roots, output_dir, modules):
    """Publish the collected native records in their original order."""
    output_dir = (REPO_ROOT / output_dir).resolve()
    modules_dir = output_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)
    written_pages: List[str] = []
    for module in modules:
        page = modules_dir / module_page_name(module.module)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(render_module_page(module, output_dir), encoding="utf-8")
        written_pages.append(rel(page))
    index_file = output_dir / "INDEX.md"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(render_index(modules, output_dir), encoding="utf-8")
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "ok": bool(modules),
        "roots": [str(root) for root in roots],
        "output_dir": rel(output_dir),
        "index_file": rel(index_file),
        "summary": {
            "module_count": len(modules),
            "declaration_count": sum(len(module.declarations) for module in modules),
            "theorem_like_count": sum(
                1
                for module in modules
                for decl in module.declarations
                if decl.kind in {"theorem", "lemma"}
            ),
            "module_page_count": len(written_pages),
        },
        "modules": [
            {
                "module": module.module,
                "path": module.rel_path,
                "status": module.status,
                "page": written_pages[index],
                "declaration_count": len(module.declarations),
                "declarations": [
                    {
                        "kind": decl.kind,
                        "name": decl.name,
                        "qualified_name": decl.qualified_name,
                        "line": decl.line,
                    }
                    for decl in module.declarations
                ],
            }
            for index, module in enumerate(modules)
        ],
    }
    manifest_file = output_dir / "manifest.json"
    manifest_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest["manifest_file"] = rel(manifest_file)
    return manifest


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


def render_text(manifest: Dict[str, Any]) -> str:
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
    summary = manifest["summary"]
    lines = [
        f"ok: {manifest['ok']}",
        f"index: {manifest['index_file']}",
        f"modules: {summary['module_count']}",
        f"declarations: {summary['declaration_count']}",
        f"module_pages: {summary['module_page_count']}",
    ]
    for module in manifest["modules"]:
        lines.append(
            f"- {module['status']} {module['module']} "
            f"decls={module['declaration_count']} page={module['page']}"
        )
    return "\n".join(lines)


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
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "Fixture.lean"
        source.write_text(
            "\n".join(
                [
                    "import Mathlib.Data.Nat.Basic",
                    "",
                    "namespace Fixture",
                    "",
                    "/--",
                    "Original source (NL): Zero equals zero.",
                    "Original source (LaTeX): `0=0`.",
                    "-/",
                    "theorem zero_eq_zero : (0 : Nat) = 0 := by",
                    "  rfl",
                    "",
                    "/--",
                    "Generated note (NL): A simple reusable truth lemma.",
                    "Generated equivalent (LaTeX): `\\mathrm{True}`.",
                    "-/",
                    "lemma true_intro : True := by",
                    "  trivial",
                    "",
                    "end Fixture",
                ]
            ),
            encoding="utf-8",
        )
        rel_source = (
            source.relative_to(REPO_ROOT)
            if source.is_relative_to(REPO_ROOT)
            else source
        )
        # The scanner expects roots under the repo. Copy the fixture into artifacts
        # so relative links and module names exercise the normal path logic.
        fixture_root = (
            REPO_ROOT / "artifacts" / "mathformer_docs_self_test" / "Fixture.lean"
        )
        fixture_root.parent.mkdir(parents=True, exist_ok=True)
        fixture_root.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        output_dir = Path("artifacts/mathformer_docs_self_test/docs")
        manifest = build_docs(
            [Path("artifacts/mathformer_docs_self_test/Fixture.lean")], output_dir, None
        )
        index_text = (REPO_ROOT / output_dir / "INDEX.md").read_text(encoding="utf-8")
        page_text = (
            REPO_ROOT
            / output_dir
            / "modules"
            / module_page_name("artifacts.mathformer_docs_self_test.Fixture")
        ).read_text(encoding="utf-8")
        checks = {
            "has_index": "# Mathformer Library" in index_text,
            "has_lean_fence": "```lean" in page_text,
            "has_latex_fence": "```latex" in page_text,
            "has_display_math": "$$\n0=0\n$$" in page_text,
            "has_declaration_anchor": '<a id="fixture-zero-eq-zero"></a>' in page_text,
        }
        return {
            "ok": all(checks.values())
            and manifest["summary"]["declaration_count"] == 2,
            "checks": checks,
            "manifest": manifest,
            "fixture": str(rel_source),
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
        "--include-root",
        action="append",
        type=Path,
        default=[],
        help="Lean file or directory to include. Defaults to MathformerLib, libraries/MathformerLib.lean, and Mathformer.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/libraries/mathformerlib")
    )
    parser.add_argument("--registry-file", type=Path)
    parser.add_argument("--reasoning-log-file", type=Path)
    parser.add_argument("--expect-docs", action="store_true")
    parser.add_argument("--self-test", action="store_true")
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
    if args.self_test:
        result = run_self_test()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 3
    roots = prepare_generation(args)
    manifest = build_docs(roots, args.output_dir, args.registry_file)
    return complete_generation(args, manifest)


def prepare_generation(args):
    """Select default roots and emit the source-owned start event."""
    roots = args.include_root or [
        Path("MathformerLib"),
        Path("libraries/MathformerLib.lean"),
        Path("Mathformer"),
    ]
    append_event(
        args.reasoning_log_file,
        "mathformer_library_docs_start",
        {
            "roots": [str(root) for root in roots],
            "output_dir": str(args.output_dir),
            "registry_file": str(args.registry_file) if args.registry_file else None,
        },
    )
    return roots


def complete_generation(args, manifest):
    """Emit source completion/error events, stdout and exit status."""
    append_event(
        args.reasoning_log_file,
        "mathformer_library_docs_complete",
        {
            "ok": manifest["ok"],
            **manifest["summary"],
            "index_file": manifest["index_file"],
        },
    )
    if args.expect_docs and not manifest["ok"]:
        append_event(
            args.reasoning_log_file,
            "mathformer_library_docs_error",
            {"reason": "no module docs generated"},
        )
        if args.json:
            print(json.dumps(manifest, ensure_ascii=False, indent=2))
        else:
            print(render_text(manifest))
        return 3
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_text(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

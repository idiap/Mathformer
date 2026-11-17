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

"""Extract theorem-like LaTeX units from an archive or source tree."""

from __future__ import annotations

import argparse
import bisect
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple
import zipfile

DEFAULT_ENV_KINDS: Dict[str, str] = {
    "theorem": "theorem",
    "lemma": "lemma",
    "corollary": "corollary",
    "proposition": "proposition",
    "definition": "definition",
    "terminology": "definition",
    "assumption": "assumption",
    "notation": "notation",
    "axiom": "axiom",
    "claim": "claim",
    "conjecture": "conjecture",
    "condition": "condition",
    "construction": "construction",
    "criterion": "criterion",
    "conclusion": "conclusion",
    "case": "case",
    "example": "example",
    "exercise": "exercise",
    "problem": "problem",
    "remark": "remark",
    "summary": "summary",
    "acknowledgement": "acknowledgement",
    "proof": "proof",
}

FORMAL_ENV_KIND_HINTS: Dict[str, str] = {
    "thm": "theorem",
    "theo": "theorem",
    "theorem": "theorem",
    "lem": "lemma",
    "lemma": "lemma",
    "cor": "corollary",
    "coro": "corollary",
    "corollary": "corollary",
    "prop": "proposition",
    "proposition": "proposition",
    "def": "definition",
    "defs": "definition",
    "definition": "definition",
    "terminology": "definition",
    "ass": "assumption",
    "assumption": "assumption",
    "notation": "notation",
    "claim": "claim",
}

BEGIN_END_RE = re.compile(r"\\(begin|end)\{([A-Za-z*]+)\}(?:\s*\[([^\]]*)\])?")
NEWTHEOREM_RE = re.compile(
    r"\\newtheorem\*?\{([A-Za-z*]+)\}(?:\[[^\]]*\])?\{([^{}]*)\}"
)
NEWENV_RE = re.compile(r"\\newenvironment\*?\{([A-Za-z*]+)\}")
INPUT_RE = re.compile(r"\\(?:include|input)\{([^{}]+)\}")
SECTION_RE = re.compile(
    r"\\(chapter|section|subsection|subsubsection)\*?(?:\[[^\]]*\])?\{((?:[^{}]|\{[^{}]*\})*)\}",
    re.DOTALL,
)
LABEL_RE = re.compile(r"\\label\{([^{}]+)\}")
REF_RE = re.compile(r"\\(?:eqref|ref|cref|Cref|autoref)\{([^{}]+)\}")
CITE_RE = re.compile(
    r"\\(?:cite|citet|citep|citealp|citeyear)(?:\[[^\]]*\])*\{([^{}]+)\}"
)
NON_CONTENT_TEX_STEMS = {
    "main",
    "header",
    "header_packages",
    "header_macros",
    "header_letters",
    "macros",
    "packages",
    "commands",
}


def archive_stem(path: Path) -> str:
    """Document the responsibility of ``archive_stem``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``archive_stem`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    name = path.name
    for suffix in (".tar.gz", ".tgz", ".zip", ".tar"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def safe_extract_tar(archive: Path, target: Path) -> None:
    """Document the responsibility of ``safe_extract_tar``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``safe_extract_tar`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    target_resolved = target.resolve()
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            dest = (target / member.name).resolve()
            if not str(dest).startswith(str(target_resolved)):
                raise ValueError(f"unsafe archive path: {member.name}")
        try:
            tf.extractall(target, filter="data")
        except TypeError:
            tf.extractall(target)


def safe_extract_zip(archive: Path, target: Path) -> None:
    """Document the responsibility of ``safe_extract_zip``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``safe_extract_zip`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    target_resolved = target.resolve()
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            dest = (target / member.filename).resolve()
            if not str(dest).startswith(str(target_resolved)):
                raise ValueError(f"unsafe archive path: {member.filename}")
        zf.extractall(target)


def prepare_source_tree(
    archive: Optional[Path], source_dir: Optional[Path], output_dir: Path
) -> Path:
    """Document the responsibility of ``prepare_source_tree``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``prepare_source_tree`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if source_dir is not None:
        return source_dir.resolve()
    if archive is None:
        raise ValueError("provide --archive or --source-dir")
    extracted = output_dir / "source"
    if extracted.exists():
        shutil.rmtree(extracted)
    extracted.mkdir(parents=True)
    if archive.suffix == ".zip":
        safe_extract_zip(archive, extracted)
    else:
        safe_extract_tar(archive, extracted)
    tex_roots = sorted({path.parent for path in extracted.rglob("main.tex")})
    if tex_roots:
        return tex_roots[0]
    tex_files = sorted(extracted.rglob("*.tex"))
    if not tex_files:
        raise ValueError(f"no .tex files found in {archive}")
    common = Path(*Path(tex_files[0]).relative_to(extracted).parts[:1])
    return extracted / common if (extracted / common).is_dir() else extracted


def read_text(path: Path) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def rel(path: Path, root: Path) -> str:
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
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def is_commented(text: str, pos: int) -> bool:
    """Document the responsibility of ``is_commented``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_commented`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    line_start = text.rfind("\n", 0, pos) + 1
    percent = line_start
    while True:
        percent = text.find("%", percent, pos)
        if percent == -1:
            return False
        slash_count = 0
        cursor = percent - 1
        while cursor >= line_start and text[cursor] == "\\":
            slash_count += 1
            cursor -= 1
        if slash_count % 2 == 0:
            return True
        percent += 1


def newline_positions(text: str) -> List[int]:
    """Document the responsibility of ``newline_positions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``newline_positions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [idx for idx, char in enumerate(text) if char == "\n"]


def line_for_pos(newlines: Sequence[int], pos: int) -> int:
    """Document the responsibility of ``line_for_pos``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``line_for_pos`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return bisect.bisect_right(newlines, pos) + 1


def clean_latex_title(value: Optional[str]) -> Optional[str]:
    """Document the responsibility of ``clean_latex_title``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``clean_latex_title`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None:
        return None
    text = value.strip()
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def slugify(value: str, default: str = "unit") -> str:
    """Document the responsibility of ``slugify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``slugify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:80] or default


def discover_env_kinds(tex_files: Sequence[Path]) -> Dict[str, str]:
    """Document the responsibility of ``discover_env_kinds``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``discover_env_kinds`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    env_kinds = dict(DEFAULT_ENV_KINDS)
    for path in tex_files:
        text = read_text(path)
        for match in NEWTHEOREM_RE.finditer(text):
            env = match.group(1)
            title = clean_latex_title(match.group(2)) or env
            low = f"{env} {title}".lower()
            kind = next(
                (kind for hint, kind in FORMAL_ENV_KIND_HINTS.items() if hint in low),
                env.lower(),
            )
            env_kinds.setdefault(env, kind)
        for match in NEWENV_RE.finditer(text):
            env = match.group(1)
            low = env.lower().rstrip("*")
            if low in DEFAULT_ENV_KINDS:
                env_kinds.setdefault(env, DEFAULT_ENV_KINDS[low])
    return env_kinds


def resolve_inputs(
    main_file: Path, root: Path, seen: Optional[set[Path]] = None
) -> List[Path]:
    """Document the responsibility of ``resolve_inputs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``resolve_inputs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    seen = seen or set()
    if main_file in seen or not main_file.exists():
        return []
    seen.add(main_file)
    text = read_text(main_file)
    ordered: List[Path] = [main_file]
    for match in INPUT_RE.finditer(text):
        if is_commented(text, match.start()):
            continue
        name = match.group(1)
        candidate = main_file.parent / name
        if candidate.suffix != ".tex":
            candidate = candidate.with_suffix(".tex")
        if not candidate.exists():
            candidate = root / name
            if candidate.suffix != ".tex":
                candidate = candidate.with_suffix(".tex")
        ordered.extend(resolve_inputs(candidate, root, seen))
    return ordered


def ordered_tex_files(root: Path) -> List[Path]:
    """Document the responsibility of ``ordered_tex_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ordered_tex_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    main = root / "main.tex"
    if main.exists():
        ordered = resolve_inputs(main, root)
        extras = sorted(
            path for path in root.rglob("*.tex") if path not in set(ordered)
        )
        return ordered + extras
    return sorted(root.rglob("*.tex"))


def is_content_tex_file(path: Path) -> bool:
    """Document the responsibility of ``is_content_tex_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_content_tex_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stem = path.stem.lower()
    if stem in NON_CONTENT_TEX_STEMS or stem.startswith("header_"):
        return False
    return True


def section_entries(text: str, newlines: Sequence[int]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``section_entries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``section_entries`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    entries: List[Dict[str, Any]] = []
    for match in SECTION_RE.finditer(text):
        if is_commented(text, match.start()):
            continue
        entries.append(
            {
                "pos": match.start(),
                "line": line_for_pos(newlines, match.start()),
                "level": match.group(1),
                "title": clean_latex_title(match.group(2)) or "",
            }
        )
    return entries


def context_at(
    sections: Sequence[Dict[str, Any]], pos: int, fallback_chapter: str
) -> Dict[str, Optional[str]]:
    """Document the responsibility of ``context_at``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``context_at`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    context: Dict[str, Optional[str]] = {
        "chapter": fallback_chapter,
        "section": None,
        "subsection": None,
        "subsubsection": None,
    }
    for entry in sections:
        if entry["pos"] > pos:
            break
        level = entry["level"]
        context[level] = entry["title"]
        if level == "chapter":
            context["section"] = None
            context["subsection"] = None
            context["subsubsection"] = None
        elif level == "section":
            context["subsection"] = None
            context["subsubsection"] = None
        elif level == "subsection":
            context["subsubsection"] = None
    return context


def split_refs(pattern: re.Pattern[str], text: str) -> List[str]:
    """Document the responsibility of ``split_refs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_refs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    values: List[str] = []
    for match in pattern.finditer(text):
        for part in match.group(1).split(","):
            cleaned = part.strip()
            if cleaned:
                values.append(cleaned)
    return sorted(set(values))


def extract_units_from_file(
    path: Path,
    root: Path,
    env_kinds: Dict[str, str],
    next_index: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Document the responsibility of ``extract_units_from_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_units_from_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = read_text(path)
    newlines = newline_positions(text)
    sections = section_entries(text, newlines)
    events = [
        match
        for match in BEGIN_END_RE.finditer(text)
        if not is_commented(text, match.start())
    ]
    target_envs = set(env_kinds)
    stack: List[re.Match[str]] = []
    units: List[Dict[str, Any]] = []

    for match in events:
        action, env = match.group(1), match.group(2)
        if env not in target_envs:
            continue
        if action == "begin":
            stack.append(match)
            continue
        for idx in range(len(stack) - 1, -1, -1):
            begin = stack[idx]
            if begin.group(2) == env:
                del stack[idx:]
                block = text[begin.start() : match.end()]
                body = text[begin.end() : match.start()]
                labels = LABEL_RE.findall(block)
                title = clean_latex_title(begin.group(3))
                context = context_at(sections, begin.start(), path.stem)
                first_label = labels[0] if labels else None
                base = first_label or title or f"{env}-{next_index}"
                unit_id = f"latex-unit-{next_index:05d}-{slugify(base)}"
                next_index += 1
                line_start = line_for_pos(newlines, begin.start())
                line_end = line_for_pos(newlines, match.end())
                unit = {
                    "id": unit_id,
                    "kind": env_kinds.get(env, env.lower()),
                    "env": env,
                    "title": title,
                    "label": first_label,
                    "labels": labels,
                    "file": rel(path, root),
                    "line_start": line_start,
                    "line_end": line_end,
                    "chapter": context["chapter"],
                    "section": context["section"],
                    "subsection": context["subsection"],
                    "subsubsection": context["subsubsection"],
                    "latex": block,
                    "body": body.strip(),
                    "references": split_refs(REF_RE, block),
                    "citations": split_refs(CITE_RE, block),
                    "proof_for_unit_id": None,
                    "proof_for_label": None,
                    "paired_proof_unit_ids": [],
                }
                units.append(unit)
                break
    units.sort(key=lambda item: (item["file"], item["line_start"], item["line_end"]))
    return units, next_index


def pair_proofs(units: List[Dict[str, Any]]) -> None:
    """Document the responsibility of ``pair_proofs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``pair_proofs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    label_index: Dict[str, Dict[str, Any]] = {}
    for unit in units:
        if unit["kind"] == "proof":
            continue
        for label in unit.get("labels", []):
            label_index[label] = unit

    previous_by_file: Dict[str, List[Dict[str, Any]]] = {}
    for unit in sorted(
        units, key=lambda item: (item["file"], item["line_start"], item["line_end"])
    ):
        if unit["kind"] != "proof":
            previous_by_file.setdefault(unit["file"], []).append(unit)
            continue

        target: Optional[Dict[str, Any]] = None
        # Only an explicit proof title such as "Proof of Theorem \ref{...}" should
        # override adjacency. References in the proof body are dependencies.
        for label in split_refs(REF_RE, unit.get("title") or ""):
            if label in label_index:
                target = label_index[label]
                break
        if target is None:
            candidates = [
                item
                for item in previous_by_file.get(unit["file"], [])
                if item["line_end"] <= unit["line_start"]
                and item["kind"]
                not in {"proof", "remark", "example", "exercise", "problem", "summary"}
            ]
            if candidates:
                target = candidates[-1]

        if target is not None:
            unit["proof_for_unit_id"] = target["id"]
            unit["proof_for_label"] = target.get("label")
            target.setdefault("paired_proof_unit_ids", []).append(unit["id"])


def build_report(
    archive: Optional[Path], source_root: Path, output_dir: Path
) -> Dict[str, Any]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tex_files = ordered_tex_files(source_root)
    content_tex_files = [path for path in tex_files if is_content_tex_file(path)]
    env_kinds = discover_env_kinds(tex_files)
    units: List[Dict[str, Any]] = []
    next_index = 1
    for path in content_tex_files:
        file_units, next_index = extract_units_from_file(
            path, source_root, env_kinds, next_index
        )
        units.extend(file_units)
    for source_order, unit in enumerate(units, start=1):
        unit["source_order"] = source_order
    pair_proofs(units)

    kind_counts = Counter(unit["kind"] for unit in units)
    env_counts = Counter(unit["env"] for unit in units)
    file_counts = Counter(unit["file"] for unit in units)
    proof_count = kind_counts.get("proof", 0)
    paired_proofs = sum(
        1 for unit in units if unit["kind"] == "proof" and unit.get("proof_for_unit_id")
    )
    report = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "archive": str(archive) if archive else None,
        "source_root": str(source_root),
        "output_dir": str(output_dir),
        "environment_kinds": dict(sorted(env_kinds.items())),
        "summary": {
            "tex_file_count": len(content_tex_files),
            "scanned_tex_file_count": len(tex_files),
            "unit_count": len(units),
            "proof_count": proof_count,
            "paired_proof_count": paired_proofs,
            "unpaired_proof_count": proof_count - paired_proofs,
            "kind_counts": dict(sorted(kind_counts.items())),
            "env_counts": dict(sorted(env_counts.items())),
            "file_counts": dict(sorted(file_counts.items())),
        },
        "tex_files": [rel(path, source_root) for path in content_tex_files],
        "scanned_tex_files": [rel(path, source_root) for path in tex_files],
        "skipped_non_content_tex_files": [
            rel(path, source_root)
            for path in tex_files
            if path not in set(content_tex_files)
        ],
        "units": units,
    }
    return report


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
        source = tmp_path / "src"
        source.mkdir()
        (source / "header_macros.tex").write_text(
            "\\newtheorem{theorem}{Theorem}\n\\newtheorem{definition}{Definition}\n",
            encoding="utf-8",
        )
        (source / "main.tex").write_text(
            "\\input{header_macros}\n\\include{chapter1}\n",
            encoding="utf-8",
        )
        (source / "chapter1.tex").write_text(
            "\\chapter{Foundations}\n"
            "\\section{Metric facts}\n"
            "\\begin{definition}[Lipschitz map]\\label{def:lipschitz}\n"
            "A map $f$ is Lipschitz if $d(fx,fy) \\le K d(x,y)$.\n"
            "\\end{definition}\n"
            "\\begin{theorem}[Uniform continuity]\\label{thm:uniform}\n"
            "Every Lipschitz map is uniformly continuous.\n"
            "\\end{theorem}\n"
            "\\begin{proof}\n"
            "Choose $\\delta=\\epsilon/K$ and apply Definition~\\ref{def:lipschitz}.\n"
            "\\end{proof}\n",
            encoding="utf-8",
        )
        archive = tmp_path / "fixture.tar.gz"
        with tarfile.open(archive, "w:gz") as tf:
            for path in source.rglob("*"):
                tf.add(path, arcname=path.relative_to(source))
        output = tmp_path / "out"
        output.mkdir()
        root = prepare_source_tree(archive, None, output)
        report = build_report(archive, root, output)
        assert report["summary"]["unit_count"] == 3, report["summary"]
        assert report["summary"]["paired_proof_count"] == 1, report["summary"]
        theorem = next(unit for unit in report["units"] if unit["kind"] == "theorem")
        assert theorem["paired_proof_unit_ids"], theorem
        return {"ok": True, "summary": report["summary"]}


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
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--archive", type=Path, help="LaTeX source archive (.tar.gz, .tgz, .tar, .zip)"
    )
    source.add_argument(
        "--source-dir", type=Path, help="Already-unpacked LaTeX source directory"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for extracted source and JSON report",
    )
    parser.add_argument(
        "--json", action="store_true", help="Print compact JSON summary"
    )
    parser.add_argument(
        "--self-test", action="store_true", help="Run deterministic self-test"
    )
    return parser.parse_args()


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
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    archive = args.archive.resolve() if args.archive else None
    if archive is not None and not archive.exists():
        raise SystemExit(f"archive does not exist: {archive}")
    source_dir = args.source_dir.resolve() if args.source_dir else None
    if source_dir is not None and not source_dir.exists():
        raise SystemExit(f"source directory does not exist: {source_dir}")
    assert archive is not None or source_dir is not None
    default_name = (
        archive_stem(archive)
        if archive
        else source_dir.name if source_dir is not None else ""
    )
    output_dir = (
        args.output_dir or Path("artifacts") / "textbook_theory" / default_name
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_root = prepare_source_tree(archive, source_dir, output_dir)
    report = build_report(archive, source_root, output_dir)
    report_file = output_dir / "theory_units.json"
    report_file.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = {"ok": True, "report_file": str(report_file), **report["summary"]}
    print(json.dumps(summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

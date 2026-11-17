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

"""Extract a layout-aware paper packet, preferring docling for PDFs."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.request import Request, urlopen

HEADING_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:[0-9]+(?:\.[0-9]+)*\.?\s+)?"
    r"(Abstract|Introduction|Background|Preliminaries|Related Work|Method|Methods|Theory|"
    r"Theoretical Analysis|Main Results|Results|Experiments|Conclusion|References|Appendix|"
    r"[A-Z][A-Za-z0-9 ,:;()/\\-]{2,80})$"
)
ROLE_PATTERNS = {
    "definition": re.compile(
        r"\bDefinition\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b|\bis called\b|\bdefined as\b",
        re.I,
    ),
    "assumption": re.compile(
        r"\bAssumption\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b|\bSuppose\b|\bAssume\b", re.I
    ),
    "theorem": re.compile(
        r"\bTheorem\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b|\bMain theorem\b", re.I
    ),
    "proposition": re.compile(r"\bProposition\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b", re.I),
    "lemma": re.compile(r"\bLemma\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b", re.I),
    "corollary": re.compile(r"\bCorollary\s+(?:[0-9]+(?:\.[0-9]+)*|[A-Z])\b", re.I),
    "proof": re.compile(
        r"\bProof\b|\bProof sketch\b|\bwe prove\b|\bit remains to show\b", re.I
    ),
    "equation": re.compile(r"(\\\(|\\\[|\$\$?|≤|≥|:=|=|\\sum|\\int|\\mathbb|\\mathrm)"),
    "reference": re.compile(r"^\s*(?:\[[0-9]+\]|[A-Z][A-Za-z-]+,\s+[A-Z])"),
}
CITATION_RE = re.compile(
    r"\[([0-9,;\- ]+)\]|\(([A-Z][A-Za-z-]+(?: et al\.)?,\s*[0-9]{4}[a-z]?)\)"
)


@dataclass
class Block:
    """Document the responsibility of ``Block``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Group related state and behavior so callers can use this part of the skills/paper/paper-docling-layout-extractor/scripts workflow through a clear object boundary.

    Function:
        Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    id: str
    section: str
    page: Optional[int]
    text: str
    role_hints: List[str]
    citations: List[str]
    labels: List[str]


def now() -> str:
    """Document the responsibility of ``now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def compact(text: str) -> str:
    """Document the responsibility of ``compact``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compact`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return re.sub(r"\s+", " ", text).strip()


def fetch_bytes(url: str, timeout: int = 30) -> bytes:
    """Document the responsibility of ``fetch_bytes``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``fetch_bytes`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    request = Request(url, headers={"User-Agent": "MathformerPaperLayoutExtractor/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def try_docling(source: str) -> Tuple[Optional[str], Optional[str]]:
    """Document the responsibility of ``try_docling``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``try_docling`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except Exception as exc:
        return None, f"docling unavailable: {type(exc).__name__}: {exc}"
    try:
        converter = DocumentConverter()
        result = converter.convert(source)
        document = result.document
        if hasattr(document, "export_to_markdown"):
            return str(document.export_to_markdown()), None
        if hasattr(document, "export_to_text"):
            return str(document.export_to_text()), None
        if hasattr(document, "export_to_dict"):
            return json.dumps(document.export_to_dict()), None
        return str(document), None
    except Exception as exc:
        return None, f"docling conversion failed: {type(exc).__name__}: {exc}"


def try_pdftotext(pdf_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Document the responsibility of ``try_pdftotext``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``try_pdftotext`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "paper.pdf"
        txt_path = Path(tmp) / "paper.txt"
        pdf_path.write_bytes(pdf_bytes)
        try:
            proc = subprocess.run(
                ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
                text=True,
                capture_output=True,
                timeout=60,
            )
        except FileNotFoundError:
            return None, "pdftotext unavailable"
        except subprocess.TimeoutExpired:
            return None, "pdftotext timed out"
        if proc.returncode != 0:
            return None, f"pdftotext failed: {proc.stderr[-500:]}"
        return txt_path.read_text(encoding="utf-8", errors="replace"), None


def role_hints(text: str) -> List[str]:
    """Document the responsibility of ``role_hints``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``role_hints`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return [role for role, pattern in ROLE_PATTERNS.items() if pattern.search(text)]


def citations(text: str) -> List[str]:
    """Document the responsibility of ``citations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``citations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    found: List[str] = []
    for match in CITATION_RE.finditer(text):
        raw = match.group(1) or match.group(2) or ""
        for piece in re.split(r"[,;]", raw):
            piece = piece.strip()
            if piece and piece not in found:
                found.append(piece)
    return found[:12]


def labels(text: str) -> List[str]:
    """Document the responsibility of ``labels``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``labels`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    found = re.findall(
        r"\b(?:Definition|Assumption|Theorem|Proposition|Lemma|Corollary)\s+([A-Z]?[0-9]+(?:\.[0-9]+)*)",
        text,
        re.I,
    )
    return found[:6]


def split_text_blocks(
    text: str,
) -> Tuple[List[Dict[str, Any]], List[Block], List[Dict[str, Any]]]:
    """Document the responsibility of ``split_text_blocks``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``split_text_blocks`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = re.sub(r"\r\n?", "\n", text)
    normalized_lines: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if (
            stripped
            and len(stripped) < 120
            and HEADING_RE.match(stripped)
            and not ROLE_PATTERNS["equation"].search(stripped)
        ):
            normalized_lines.append("")
            normalized_lines.append(stripped)
            normalized_lines.append("")
        else:
            normalized_lines.append(line)
    text = "\n".join(normalized_lines)
    paragraphs = [
        compact(part)
        for part in re.split(
            r"\n\s*\n|(?<=[.!?])\s+(?=(?:Definition|Assumption|Theorem|Proposition|Lemma|Corollary|Proof)\b)",
            text,
        )
    ]
    current_section = "Lead"
    section_order: List[str] = []
    section_blocks: Dict[str, List[str]] = {}
    blocks: List[Block] = []
    references: List[Dict[str, Any]] = []
    in_references = False

    def ensure_section(title: str) -> None:
        """Document the responsibility of ``split_text_blocks.ensure_section``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``split_text_blocks.ensure_section`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if title not in section_blocks:
            section_order.append(title)
            section_blocks[title] = []

    ensure_section(current_section)
    for raw in paragraphs:
        if not raw or len(raw) < 2:
            continue
        if (
            len(raw) < 120
            and HEADING_RE.match(raw)
            and not ROLE_PATTERNS["equation"].search(raw)
        ):
            current_section = raw.strip("# ").strip()
            in_references = current_section.lower().startswith("references")
            ensure_section(current_section)
            continue
        if in_references or ROLE_PATTERNS["reference"].search(raw):
            references.append(
                {
                    "id": f"ref_{len(references) + 1:03d}",
                    "text": raw[:1200],
                    "citations": citations(raw),
                }
            )
            continue
        hints = role_hints(raw)
        if len(raw) < 25 and not hints:
            continue
        block_id = f"block_{len(blocks) + 1:04d}"
        block = Block(
            id=block_id,
            section=current_section,
            page=None,
            text=raw[:2000],
            role_hints=hints,
            citations=citations(raw),
            labels=labels(raw),
        )
        blocks.append(block)
        section_blocks[current_section].append(block_id)

    sections = [
        {
            "id": f"section_{idx + 1:03d}",
            "title": title,
            "block_ids": section_blocks[title],
        }
        for idx, title in enumerate(section_order)
    ]
    return sections, blocks, references


def extract_layout(
    *,
    text: str,
    source_input: str,
    title: str,
    engine_name: str,
    engine_ok: bool,
    engine_details: str,
    warnings: List[str],
) -> Dict[str, Any]:
    """Document the responsibility of ``extract_layout``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_layout`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    sections, blocks, references = split_text_blocks(text)
    return {
        "source": {
            "input": source_input,
            "title": title,
            "retrieved_at_utc": now(),
        },
        "engine": {
            "name": engine_name,
            "ok": engine_ok,
            "details": engine_details,
        },
        "sections": sections,
        "blocks": [asdict(block) for block in blocks],
        "references": references,
        "warnings": warnings,
    }


def from_input(args: argparse.Namespace) -> Dict[str, Any]:
    """Document the responsibility of ``from_input``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``from_input`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    warnings: List[str] = []
    if args.self_test:
        return self_test_report()["layout_packet"]
    if args.text:
        return extract_layout(
            text=args.text,
            source_input="inline-text",
            title=args.title or "",
            engine_name="text",
            engine_ok=True,
            engine_details="direct text input",
            warnings=[],
        )
    if args.text_file:
        path = Path(args.text_file)
        return extract_layout(
            text=path.read_text(encoding="utf-8", errors="replace"),
            source_input=str(path),
            title=args.title or path.stem,
            engine_name="text",
            engine_ok=True,
            engine_details="text file input",
            warnings=[],
        )
    if args.url or args.pdf_file:
        source = args.url or str(Path(args.pdf_file).resolve())
        text, docling_warning = try_docling(source)
        if text is not None:
            return extract_layout(
                text=text,
                source_input=source,
                title=args.title or "",
                engine_name="docling",
                engine_ok=True,
                engine_details="docling document conversion",
                warnings=[],
            )
        warnings.append(docling_warning or "docling unavailable")
        pdf_bytes: Optional[bytes] = None
        if args.url:
            try:
                pdf_bytes = fetch_bytes(args.url)
            except Exception as exc:
                warnings.append(f"download failed: {type(exc).__name__}: {exc}")
        elif args.pdf_file:
            pdf_bytes = Path(args.pdf_file).read_bytes()
        if pdf_bytes is not None:
            text, pdf_warning = try_pdftotext(pdf_bytes)
            if text is not None:
                return extract_layout(
                    text=text,
                    source_input=source,
                    title=args.title or "",
                    engine_name="pdftotext",
                    engine_ok=True,
                    engine_details="pdftotext -layout fallback",
                    warnings=warnings,
                )
            warnings.append(pdf_warning or "pdftotext unavailable")
        return {
            "source": {
                "input": source,
                "title": args.title or "",
                "retrieved_at_utc": now(),
            },
            "engine": {
                "name": "unavailable",
                "ok": False,
                "details": "Install docling or pdftotext to extract PDF layout.",
            },
            "sections": [],
            "blocks": [],
            "references": [],
            "warnings": warnings,
        }
    raise SystemExit("Provide --url, --pdf-file, --text-file, --text, or --self-test.")


def sample_text() -> str:
    """Document the responsibility of ``sample_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``sample_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return """
Understanding Scaling Laws with Statistical and Approximation Theory

Abstract
We prove scaling laws for transformer neural networks on intrinsically low-dimensional data.

3 Main theoretical results
Definition 3.1. A distribution has intrinsic dimension d if its support is contained in a d-dimensional regular set.

Assumption 3.2. Let the regression function be smooth on the intrinsic support and let the samples be independent.

Theorem 3.3. Under Assumption 3.2, the excess risk of the transformer estimator is bounded by C n^{-2s/(2s+d)} up to logarithmic factors.

Proof. The result follows by combining Lemma 3.4 with the approximation theorem of Yarotsky [1].

Lemma 3.4. The approximation error is bounded by epsilon when the network width is large enough.

References
[1] Yarotsky. Error bounds for approximations with deep ReLU networks. Neural Networks, 2017.
"""


def self_test_report() -> Dict[str, Any]:
    """Document the responsibility of ``self_test_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    packet = extract_layout(
        text=sample_text(),
        source_input="self-test",
        title="Scaling Laws",
        engine_name="text",
        engine_ok=True,
        engine_details="self-test text",
        warnings=[],
    )
    roles = {role for block in packet["blocks"] for role in block["role_hints"]}
    ok = {"definition", "assumption", "theorem", "lemma", "proof"} <= roles and bool(
        packet["references"]
    )
    return {"ok": ok, "layout_packet": packet}


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
    if "layout_packet" in report:
        report = report["layout_packet"]
    return "\n".join(
        [
            f"engine: {report['engine']['name']} ok={report['engine']['ok']}",
            f"sections: {len(report['sections'])}",
            f"blocks: {len(report['blocks'])}",
            f"references: {len(report['references'])}",
            f"warnings: {len(report['warnings'])}",
        ]
    )


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
    parser.add_argument("--url")
    parser.add_argument("--pdf-file")
    parser.add_argument("--text-file")
    parser.add_argument("--text")
    parser.add_argument("--title")
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
    report = self_test_report() if args.self_test else from_input(args)
    ok = bool(report.get("ok", report.get("engine", {}).get("ok", False)))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Keep external benchmark adapters isolated from core framework code.
#
# Intent:
#   Represent benchmark loading, evaluation, and documentation conventions clearly for repeatable experiments.
#
# Function:
#   Defines adapters and notes for benchmark families used in evaluation workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Utilities for informal-first FormalScience physics benchmark intake.

Dataset source:
  https://github.com/jmeadows17/formal-science

The source repository contains formal answers, but this integration intentionally
exports only the informal question and answer fields for the first Mathformer
formalization pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any, Iterable, List, Sequence
from urllib.error import URLError
from urllib.request import urlopen

SOURCE_REPO_URL = "https://github.com/jmeadows17/formal-science"
RAW_BASE_URL = "https://raw.githubusercontent.com/jmeadows17/formal-science/main"
DATASET_FILENAME = "FormalPhysics.json"
DATASET_URL = f"{RAW_BASE_URL}/data/{DATASET_FILENAME}"
DEFAULT_DATA_DIR = Path("data/benchmarks/formal_science")
DEFAULT_FIELDS = ("Electromagnetism", "Quantum Mechanics", "Other")
WITHHELD_FIELDS = ("formal_answer",)

LATEX_COMMAND_RE = re.compile(r"\\[A-Za-z]+")
DISPLAY_MATH_RE = re.compile(r"(\$\$.*?\$\$|\\\[.*?\\\])", re.DOTALL)
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", re.DOTALL)
DERIVATION_SIGNAL_RE = re.compile(
    r"\\partial|\\nabla|\\int|\\oiint|\\iiint|\\delta|\\frac|\\times|"
    r"\\cdot|\\exp|\\sin|\\cos|\\sqrt|commutator|Hamiltonian|"
    r"Lagrangian|Euler|Fourier|Poisson|Maxwell",
    re.IGNORECASE,
)


class FormalScienceError(RuntimeError):
    """Raised when FormalScience benchmark data is missing or malformed."""


@dataclass(frozen=True)
class InformalPhysicsExample:
    """A source-side benchmark record with formal answers withheld."""

    source_index: int
    field: str
    question: str
    answer: str
    formal_answer_present: bool

    @property
    def id(self) -> str:
        """Document the responsibility of ``InformalPhysicsExample.id``.

        Motivation:
            Keep external benchmark adapters isolated from core framework code.

        Intent:
            Provide the local operation named ``InformalPhysicsExample.id`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return f"formalphysics_{self.source_index:04d}"

    @property
    def source_text(self) -> str:
        """Document the responsibility of ``InformalPhysicsExample.source_text``.

        Motivation:
            Keep external benchmark adapters isolated from core framework code.

        Intent:
            Provide the local operation named ``InformalPhysicsExample.source_text`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return f"{self.question}\n\n{self.answer}".strip()


def _clean_informal_text(text: Any) -> str:
    """Remove dataset delimiter sentinels while preserving source math."""
    lines = str(text).replace("\r\n", "\n").replace("\r", "\n").splitlines()
    while lines and lines[0].strip() in {"{", "}", "**"}:
        lines.pop(0)
    while lines and lines[-1].strip() in {"{", "}", "**"}:
        lines.pop()
    return "\n".join(lines).strip()


def _read_json_url(url: str) -> Any:
    """Document the responsibility of ``_read_json_url``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        with urlopen(url) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise FormalScienceError(f"failed to fetch {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise FormalScienceError(f"failed to parse JSON from {url}: {exc}") from exc


def download_dataset(output_dir: Path, force: bool = False) -> Path:
    """Download the source FormalPhysics JSON into a local benchmark directory."""
    output_path = output_dir / DATASET_FILENAME
    if output_path.exists() and not force:
        return output_path

    records = _read_json_url(DATASET_URL)
    if not isinstance(records, list):
        raise FormalScienceError("expected FormalPhysics JSON to be a list")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def load_examples(data_path: Path) -> List[InformalPhysicsExample]:
    """Load source-side examples from local FormalPhysics JSON."""
    if not data_path.exists():
        raise FormalScienceError(f"dataset file not found: {data_path}")

    try:
        records = json.loads(data_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FormalScienceError(f"failed to parse {data_path}: {exc}") from exc

    if not isinstance(records, list):
        raise FormalScienceError(f"expected {data_path} to contain a JSON list")

    examples: List[InformalPhysicsExample] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise FormalScienceError(f"record #{index} is not an object")
        missing = [key for key in ("field", "question", "answer") if key not in record]
        if missing:
            raise FormalScienceError(
                f"record #{index} missing fields: {', '.join(missing)}"
            )
        examples.append(
            InformalPhysicsExample(
                source_index=index,
                field=str(record["field"]),
                question=_clean_informal_text(record["question"]),
                answer=_clean_informal_text(record["answer"]),
                formal_answer_present=bool(record.get("formal_answer")),
            )
        )
    return examples


def complexity_features(example: InformalPhysicsExample) -> dict:
    """Compute transparent source-text complexity features."""
    text = example.source_text
    answer_lines = [line for line in example.answer.splitlines() if line.strip()]
    latex_commands = LATEX_COMMAND_RE.findall(text)
    display_math = DISPLAY_MATH_RE.findall(text)
    inline_math = INLINE_MATH_RE.findall(text)
    derivation_signals = DERIVATION_SIGNAL_RE.findall(text)
    score = (
        len(text) / 250.0
        + 0.8 * len(latex_commands)
        + 4.0 * len(display_math)
        + 2.0 * len(inline_math)
        + 4.0 * len(derivation_signals)
        + 0.6 * len(answer_lines)
    )
    return {
        "score": round(score, 4),
        "char_count": len(text),
        "answer_line_count": len(answer_lines),
        "latex_command_count": len(latex_commands),
        "display_math_count": len(display_math),
        "inline_math_count": len(inline_math),
        "derivation_signal_count": len(derivation_signals),
    }


def _field_filter(
    examples: Iterable[InformalPhysicsExample], fields: Sequence[str]
) -> List[InformalPhysicsExample]:
    """Document the responsibility of ``_field_filter``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_field_filter`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    allowed = {field.strip() for field in fields if field.strip()}
    if not allowed:
        return list(examples)
    return [example for example in examples if example.field in allowed]


def rank_examples(
    examples: Sequence[InformalPhysicsExample], fields: Sequence[str]
) -> List[InformalPhysicsExample]:
    """Rank examples by descending informal-source complexity."""
    filtered = _field_filter(examples, fields)
    return sorted(
        filtered,
        key=lambda example: (complexity_features(example)["score"], example.id),
        reverse=True,
    )


def _payload(example: InformalPhysicsExample, rank: int) -> dict:
    """Document the responsibility of ``_payload``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    features = complexity_features(example)
    source_text = example.source_text
    return {
        "id": example.id,
        "rank": rank,
        "benchmark": "jmeadows17/formal-science:data/FormalPhysics.json",
        "source_repo": SOURCE_REPO_URL,
        "source_index": example.source_index,
        "field": example.field,
        "question": example.question,
        "answer": example.answer,
        "source_text": source_text,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "complexity": features,
        "withheld_fields": list(WITHHELD_FIELDS),
        "formal_answer_present_in_source": example.formal_answer_present,
        "intended_use": "informal_first_physics_formalization",
    }


def export_informal_sample(
    data_path: Path,
    output_file: Path,
    sample_size: int,
    fields: Sequence[str],
    bundle_dir: Path | None = None,
) -> List[dict]:
    """Export the top-ranked informal examples without formal answers."""
    examples = load_examples(data_path)
    selected = rank_examples(examples, fields)[:sample_size]
    payloads = [
        _payload(example, rank=index + 1) for index, example in enumerate(selected)
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as out:
        for payload in payloads:
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")

    if bundle_dir is not None:
        write_source_bundles(payloads, bundle_dir)

    return payloads


def write_source_bundles(payloads: Sequence[dict], bundle_dir: Path) -> None:
    """Write one LaTeX source packet per selected informal derivation."""
    bundle_dir.mkdir(parents=True, exist_ok=True)
    for payload in payloads:
        path = bundle_dir / f"{payload['rank']:02d}_{payload['id']}.tex"
        content = "\n".join(
            [
                "% benchmark: jmeadows17/formal-science",
                "% source-file: data/FormalPhysics.json",
                f"% benchmark-id: {payload['id']}",
                f"% source-index: {payload['source_index']}",
                "% formal-answer-withheld: true",
                "% backend-style: sympy_physics_derivation_trace",
                f"\\section*{{Informal physics derivation {payload['id']}}}",
                f"\\paragraph{{Field}} {payload['field']}",
                "\\paragraph{Question}",
                payload["question"],
                "\\paragraph{Informal derivation}",
                payload["answer"],
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")


def dataset_stats(data_path: Path) -> dict:
    """Document the responsibility of ``dataset_stats``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``dataset_stats`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    examples = load_examples(data_path)
    fields: dict[str, int] = {}
    formal_answers = 0
    for example in examples:
        fields[example.field] = fields.get(example.field, 0) + 1
        formal_answers += int(example.formal_answer_present)
    return {
        "benchmark": "jmeadows17/formal-science:data/FormalPhysics.json",
        "source_repo": SOURCE_REPO_URL,
        "count": len(examples),
        "fields": fields,
        "formal_answer_records_present_but_withheld": formal_answers,
    }


def _resolve_dataset_path(output_dir: Path) -> Path:
    """Document the responsibility of ``_resolve_dataset_path``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_resolve_dataset_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return output_dir / DATASET_FILENAME


def _cmd_download(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_download``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path = download_dataset(args.output, force=args.force)
    print(f"Downloaded FormalScience source data to {path}")
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_stats``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_stats`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    print(
        json.dumps(
            dataset_stats(_resolve_dataset_path(args.output)),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_rank(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_rank``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_rank`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    examples = load_examples(_resolve_dataset_path(args.output))
    for rank, example in enumerate(
        rank_examples(examples, args.fields)[: args.n], start=1
    ):
        payload = {
            "rank": rank,
            "id": example.id,
            "field": example.field,
            "source_index": example.source_index,
            "complexity": complexity_features(example),
            "question_preview": " ".join(example.question.split())[:160],
        }
        print(json.dumps(payload, ensure_ascii=False))
    return 0


def _cmd_export_informal_sample(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_export_informal_sample``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_export_informal_sample`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    payloads = export_informal_sample(
        data_path=_resolve_dataset_path(args.output),
        output_file=args.output_file,
        sample_size=args.sample_size,
        fields=args.fields,
        bundle_dir=args.bundle_dir,
    )
    print(f"Wrote {len(payloads)} informal sample row(s) to {args.output_file}")
    if args.bundle_dir is not None:
        print(f"Wrote LaTeX source bundle(s) to {args.bundle_dir}")
    return 0


def _cmd_self_test(_: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_self_test``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_self_test`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    example = InformalPhysicsExample(
        source_index=7,
        field="Electromagnetism",
        question="{\nShow $\\nabla\\cdot E=\\rho$.\n}",
        answer="}\nUse Gauss law.\n{",
        formal_answer_present=True,
    )
    payload = _payload(example, rank=1)
    if "formal_answer" in payload:
        raise FormalScienceError("formal_answer leaked into payload")
    if payload["withheld_fields"] != ["formal_answer"]:
        raise FormalScienceError("withheld formal field was not declared")
    if complexity_features(example)["score"] <= 0:
        raise FormalScienceError("complexity score should be positive")
    print("formal_science self-test passed")
    return 0


def _fields_arg(parser: argparse.ArgumentParser) -> None:
    """Document the responsibility of ``_fields_arg``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_fields_arg`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser.add_argument(
        "--fields",
        nargs="+",
        default=list(DEFAULT_FIELDS),
        help="Dataset field names to include. Default: Electromagnetism Quantum Mechanics Other.",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    dl = subparsers.add_parser("download", help="Download FormalPhysics source data")
    dl.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    dl.add_argument(
        "--force", action="store_true", help="Redownload even if target exists"
    )
    dl.set_defaults(func=_cmd_download)

    st = subparsers.add_parser("stats", help="Print dataset statistics")
    st.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    st.set_defaults(func=_cmd_stats)

    rk = subparsers.add_parser("rank", help="Print top informal examples by complexity")
    rk.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    rk.add_argument("-n", type=int, default=10)
    _fields_arg(rk)
    rk.set_defaults(func=_cmd_rank)

    ex = subparsers.add_parser(
        "export-informal-sample", help="Export top informal-only records as JSONL"
    )
    ex.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    ex.add_argument("--output-file", type=Path, required=True)
    ex.add_argument("--sample-size", type=int, default=10)
    ex.add_argument(
        "--bundle-dir",
        type=Path,
        default=None,
        help="Optional directory for per-sample TeX packets",
    )
    _fields_arg(ex)
    ex.set_defaults(func=_cmd_export_informal_sample)

    test = subparsers.add_parser("self-test", help="Run lightweight validation")
    test.set_defaults(func=_cmd_self_test)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return dispatch_args(parse_args(argv))


def dispatch_args(args: argparse.Namespace) -> int:
    """Run the selected native handler with main's error boundary."""
    try:
        return args.func(args)
    except FormalScienceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

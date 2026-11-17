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

"""Utilities for integrating the ProofNet benchmark in this repository.

Dataset source:
  https://huggingface.co/datasets/hoskinson-center/proofnet
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from huggingface_hub import hf_hub_download

DATASET_REPO_ID = "hoskinson-center/proofnet"
DATASET_REPO_TYPE = "dataset"

SPLIT_TO_FILE = {
    "validation": "valid.jsonl",
    "test": "test.jsonl",
}

OPTIONAL_FILES = [
    "README.md",
    "common.lean",
    "proofnet.py",
    "test_loader.py",
]

REQUIRED_FIELDS = [
    "id",
    "nl_statement",
    "nl_proof",
    "formal_statement",
    "src_header",
]

DEFAULT_DATA_DIR = Path("data/benchmarks/proofnet")


@dataclass
class ProofNetExample:
    """Document the responsibility of ``ProofNetExample``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Group related state and behavior so callers can use this part of the benchmarks/proofnet workflow through a clear object boundary.

    Function:
        Defines adapters and notes for benchmark families used in evaluation workflows.

    Maintenance:
        Keep the class contract explicit when adding fields, constructor requirements, or externally visible methods.
    """

    id: str
    nl_statement: str
    nl_proof: str
    formal_statement: str
    src_header: str


class ProofNetError(RuntimeError):
    """Raised when benchmark data is malformed or missing."""


def _download_file(
    filename: str,
    output_dir: Path,
    force: bool,
    cache_dir: Path,
) -> Path:
    """Document the responsibility of ``_download_file``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    output_path = output_dir / filename
    if output_path.exists() and not force:
        return output_path

    cached_path = Path(
        hf_hub_download(
            repo_id=DATASET_REPO_ID,
            repo_type=DATASET_REPO_TYPE,
            filename=filename,
            cache_dir=str(cache_dir),
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached_path, output_path)
    return output_path


def download_proofnet(
    output_dir: Path,
    include_optional: bool = True,
    force: bool = False,
    cache_dir: Path | None = None,
) -> Dict[str, Path]:
    """Download ProofNet files into a local benchmark directory."""
    files = list(SPLIT_TO_FILE.values())
    if include_optional:
        files.extend(OPTIONAL_FILES)

    resolved_cache_dir = cache_dir or (output_dir / ".hf_cache")
    downloaded: Dict[str, Path] = {}
    for filename in files:
        downloaded[filename] = _download_file(
            filename,
            output_dir=output_dir,
            force=force,
            cache_dir=resolved_cache_dir,
        )
    return downloaded


def _iter_jsonl(path: Path) -> Iterable[dict]:
    """Document the responsibility of ``_iter_jsonl``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_iter_jsonl`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with path.open("r", encoding="utf-8") as infile:
        for line_number, line in enumerate(infile, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                record = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ProofNetError(
                    f"Failed to parse JSON on line {line_number} in {path}: {exc}"
                ) from exc
            yield record


def _validate_record(record: dict, split: str, index: int) -> None:
    """Document the responsibility of ``_validate_record``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    missing = [k for k in REQUIRED_FIELDS if k not in record]
    if missing:
        raise ProofNetError(
            f"Missing fields in split '{split}' record #{index}: {', '.join(missing)}"
        )


def load_split(output_dir: Path, split: str) -> List[ProofNetExample]:
    """Load validation/test split from local downloaded files."""
    if split not in SPLIT_TO_FILE:
        raise ProofNetError(
            f"Unknown split '{split}'. Expected one of: {', '.join(SPLIT_TO_FILE)}"
        )

    split_path = output_dir / SPLIT_TO_FILE[split]
    if not split_path.exists():
        raise ProofNetError(
            f"Split file not found: {split_path}. Run the download command first."
        )

    examples: List[ProofNetExample] = []
    for idx, record in enumerate(_iter_jsonl(split_path)):
        _validate_record(record, split=split, index=idx)
        examples.append(
            ProofNetExample(
                id=str(record["id"]),
                nl_statement=str(record["nl_statement"]),
                nl_proof=str(record["nl_proof"]),
                formal_statement=str(record["formal_statement"]),
                src_header=str(record["src_header"]),
            )
        )
    return examples


def dataset_stats(output_dir: Path) -> dict:
    """Compute basic split and field statistics for local dataset files."""
    stats = {
        "dataset": DATASET_REPO_ID,
        "splits": {},
        "required_fields": REQUIRED_FIELDS,
    }
    total = 0
    for split in SPLIT_TO_FILE:
        examples = load_split(output_dir, split)
        count = len(examples)
        total += count
        stats["splits"][split] = {
            "count": count,
            "unique_ids": len({x.id for x in examples}),
        }
    stats["total_examples"] = total
    return stats


def build_autoformalization_prompt(
    nl_statement: str,
    formal_language: str = "Lean3",
) -> str:
    """Document the responsibility of ``build_autoformalization_prompt``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return (
        f"Natural language statement: {nl_statement}\n"
        f"Give me the {formal_language} formal code of the statement:\n"
    )


def export_generation_inputs(
    output_dir: Path,
    split: str,
    output_file: Path,
    formal_language: str = "Lean3",
    include_proof: bool = False,
) -> int:
    """Export benchmark prompts as JSONL for model generation pipelines."""
    examples = load_split(output_dir, split)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as out:
        for ex in examples:
            payload = {
                "id": ex.id,
                "split": split,
                "nl_statement": ex.nl_statement,
                "prompt": build_autoformalization_prompt(
                    nl_statement=ex.nl_statement,
                    formal_language=formal_language,
                ),
            }
            if include_proof:
                payload["nl_proof"] = ex.nl_proof
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return len(examples)


def _print_sample(output_dir: Path, split: str, n: int) -> None:
    """Document the responsibility of ``_print_sample``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_print_sample`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    examples = load_split(output_dir, split)
    for ex in examples[:n]:
        payload = {
            "id": ex.id,
            "nl_statement": ex.nl_statement,
            "formal_statement": ex.formal_statement,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))


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
    downloaded = download_proofnet(
        output_dir=args.output,
        include_optional=not args.no_optional,
        force=args.force,
        cache_dir=args.cache_dir,
    )
    print(f"Downloaded {len(downloaded)} file(s) to {args.output}")
    for name in sorted(downloaded):
        print(f"- {name}")
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
    stats = dataset_stats(args.output)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def _cmd_sample(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_sample``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_sample`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    _print_sample(args.output, split=args.split, n=args.n)
    return 0


def _cmd_export_inputs(args: argparse.Namespace) -> int:
    """Document the responsibility of ``_cmd_export_inputs``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``_cmd_export_inputs`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    count = export_generation_inputs(
        output_dir=args.output,
        split=args.split,
        output_file=args.output_file,
        formal_language=args.formal_language,
        include_proof=args.include_proof,
    )
    print(f"Wrote {count} prompt rows to {args.output_file}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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

    dl = subparsers.add_parser("download", help="Download ProofNet dataset files")
    dl.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    dl.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory for Hugging Face downloads (defaults to <output>/.hf_cache).",
    )
    dl.add_argument(
        "--force", action="store_true", help="Redownload even if target files exist"
    )
    dl.add_argument(
        "--no-optional", action="store_true", help="Download only split JSONL files"
    )
    dl.set_defaults(func=_cmd_download)

    st = subparsers.add_parser("stats", help="Print dataset split statistics")
    st.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    st.set_defaults(func=_cmd_stats)

    sm = subparsers.add_parser("sample", help="Print sample examples")
    sm.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    sm.add_argument("--split", choices=list(SPLIT_TO_FILE), default="validation")
    sm.add_argument("-n", type=int, default=1)
    sm.set_defaults(func=_cmd_sample)

    ex = subparsers.add_parser(
        "export-inputs", help="Export generation prompts as JSONL"
    )
    ex.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    ex.add_argument("--split", choices=list(SPLIT_TO_FILE), default="validation")
    ex.add_argument("--output-file", type=Path, required=True)
    ex.add_argument("--formal-language", default="Lean3")
    ex.add_argument("--include-proof", action="store_true")
    ex.set_defaults(func=_cmd_export_inputs)

    return parser.parse_args(argv)


def main() -> int:
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
    return dispatch_args(parse_args())


def dispatch_args(args: argparse.Namespace) -> int:
    """Invoke the selected native callback with the CLI error boundary."""
    try:
        return args.func(args)
    except ProofNetError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

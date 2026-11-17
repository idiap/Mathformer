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

"""Evaluate ProofNet prediction files against local gold splits.

Prediction JSONL format (default):
  {"id": "...", "pred_formal_statement": "..."}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict

from proofnet import DEFAULT_DATA_DIR, SPLIT_TO_FILE, load_split


def normalize_formal_statement(text: str) -> str:
    """Document the responsibility of ``normalize_formal_statement``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``normalize_formal_statement`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return " ".join(text.split())


def load_prediction_map(
    predictions_file: Path,
    id_key: str,
    prediction_key: str,
) -> Dict[str, str]:
    """Document the responsibility of ``load_prediction_map``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    state = prediction_state(predictions_file, id_key, prediction_key)
    with predictions_file.open("r", encoding="utf-8") as infile:
        while not read_prediction(infile, state):
            pass
    return state["predictions"]


def consume_prediction_line(state: dict, line: str) -> None:
    """Consume one physical line, preserving native diagnostics and overwrite order."""
    predictions_file = state["predictions_file"]
    line_number = state["line_number"]
    id_key, prediction_key = state["id_key"], state["prediction_key"]
    prediction_by_id = state["predictions"]
    text = line.strip()
    if not text:
        return
    try:
        row = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Failed to parse JSON in {predictions_file} line {line_number}: {exc}"
        ) from exc

    if id_key not in row:
        raise RuntimeError(
            f"Missing '{id_key}' in predictions line {line_number}: {row}"
        )
    if prediction_key not in row:
        raise RuntimeError(
            f"Missing '{prediction_key}' in predictions line {line_number}: {row}"
        )

    prediction_by_id[str(row[id_key])] = str(row[prediction_key])


def prediction_state(predictions_file: Path, id_key: str, prediction_key: str) -> dict:
    return {
        "predictions_file": str(predictions_file),
        "id_key": id_key,
        "prediction_key": prediction_key,
        "line_number": 0,
        "predictions": {},
    }


def read_prediction(infile, state: dict) -> bool:
    """Advance the native UTF-8 iterator once; true denotes exhaustion."""
    line = next(infile, None)
    if line is None:
        return True
    state["line_number"] += 1
    consume_prediction_line(state, line)
    return False


def evaluate(
    gold_dir: Path,
    split: str,
    predictions_file: Path,
    id_key: str,
    prediction_key: str,
) -> dict:
    """Document the responsibility of ``evaluate``.

    Motivation:
        Keep external benchmark adapters isolated from core framework code.

    Intent:
        Provide the local operation named ``evaluate`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    gold_examples = load_gold(gold_dir, split)
    pred_by_id = load_prediction_map(predictions_file, id_key, prediction_key)
    state = initialize_scores(gold_examples, pred_by_id)
    while not score_example(state):
        pass
    return score_metrics(gold_dir, split, predictions_file, state)


def load_gold(gold_dir: Path, split: str) -> list:
    gold_examples = load_split(gold_dir, split)
    _gold_by_id = {x.id: x for x in gold_examples}
    return [{"id": x.id, "formal_statement": x.formal_statement} for x in gold_examples]


def initialize_scores(gold: list, predictions: dict) -> dict:
    return {
        "gold": gold,
        "predictions": predictions,
        "index": 0,
        "total": len(gold),
        "answered": 0,
        "exact": 0,
        "normalized_exact": 0,
        "details": [],
    }


def score_example(state: dict) -> bool:
    """Visit one gold example; return true only upon list exhaustion."""
    if state["index"] == state["total"]:
        return True
    example = state["gold"][state["index"]]
    state["index"] += 1
    pred_by_id, details = state["predictions"], state["details"]
    pred = pred_by_id.get(example["id"])
    if pred is None:
        details.append(
            {
                "id": example["id"],
                "answered": False,
                "exact_match": False,
                "normalized_exact_match": False,
            }
        )
        return False

    state["answered"] += 1
    em = pred == example["formal_statement"]
    nem = normalize_formal_statement(pred) == normalize_formal_statement(
        example["formal_statement"]
    )
    if em:
        state["exact"] += 1
    if nem:
        state["normalized_exact"] += 1
    details.append(
        {
            "id": example["id"],
            "answered": True,
            "exact_match": em,
            "normalized_exact_match": nem,
        }
    )
    return False


def score_metrics(
    gold_dir: Path, split: str, predictions_file: Path, state: dict
) -> dict:
    total, answered = state["total"], state["answered"]
    exact, normalized_exact, details = (
        state["exact"],
        state["normalized_exact"],
        state["details"],
    )
    return {
        "dataset": "hoskinson-center/proofnet",
        "split": split,
        "gold_file": str(gold_dir / SPLIT_TO_FILE[split]),
        "predictions_file": str(predictions_file),
        "total": total,
        "answered": answered,
        "missing": total - answered,
        "coverage": answered / total if total else 0.0,
        "exact_match": exact / total if total else 0.0,
        "normalized_exact_match": normalized_exact / total if total else 0.0,
        "exact_match_on_answered": exact / answered if answered else 0.0,
        "normalized_exact_match_on_answered": (
            normalized_exact / answered if answered else 0.0
        ),
        "details": details,
    }


def parse_args(argv=None) -> argparse.Namespace:
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
    parser.add_argument("--gold-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--split", choices=list(SPLIT_TO_FILE), default="validation")
    parser.add_argument("--predictions-file", type=Path, required=True)
    parser.add_argument("--id-key", default="id")
    parser.add_argument("--prediction-key", default="pred_formal_statement")
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional output file. If omitted, prints JSON to stdout.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Drop per-example details from output payload.",
    )
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
    args = parse_args()

    metrics = evaluate(
        gold_dir=args.gold_dir,
        split=args.split,
        predictions_file=args.predictions_file,
        id_key=args.id_key,
        prediction_key=args.prediction_key,
    )

    _, payload, write_file = finalize_output(vars(args), metrics)
    if write_file:
        return write_output(vars(args), payload)
    return print_output(payload)


def finalize_output(config: dict, metrics: dict) -> tuple:
    if config["summary_only"]:
        metrics.pop("details", None)
    return (
        metrics,
        json.dumps(metrics, ensure_ascii=False, indent=2),
        bool(config["output_json"]),
    )


def write_output(config: dict, payload: str) -> int:
    output_json = Path(config["output_json"])
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(payload + "\n", encoding="utf-8")
    print(f"Wrote evaluation summary to {output_json}")
    return 0


def print_output(payload: str) -> int:
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

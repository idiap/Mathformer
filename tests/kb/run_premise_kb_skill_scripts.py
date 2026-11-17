#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.
#
# Intent:
#   Encode regression checks that catch parser breakage, semantic drift, and missing workflow evidence.
#
# Function:
#   Contains executable tests, fixtures, and manifests used for local and CI validation.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Regression for premise-KB theorem generation and indexing skills."""

from __future__ import annotations

from typing import Any

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = (
    REPO_ROOT
    / "skills"
    / "premise-kb"
    / "premise-kb-theorem-seed-generator"
    / "scripts"
    / "generate_theorem_axiom_seed_list.py"
)
INDEXER = (
    REPO_ROOT
    / "skills"
    / "premise-kb"
    / "premise-kb-indexer"
    / "scripts"
    / "index_premise_kb.py"
)


def run_json(command: list[str]) -> dict[str, Any]:
    """Document the responsibility of ``run_json``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(command)}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return json.loads(completed.stdout)


def prepare(request):
    """Resolve paths and perform the native destructive reset exactly once."""
    artifact_root = (
        Path(request["artifact_root"])
        if Path(request["artifact_root"]).is_absolute()
        else REPO_ROOT / Path(request["artifact_root"])
    )
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
    seed_jsonl = artifact_root / "generated_seeds.jsonl"
    kb_root = artifact_root / "kb"

    return {
        "artifact_root": str(artifact_root),
        "seed_jsonl": str(seed_jsonl),
        "kb_root": str(kb_root),
    }


def generate(paths):
    """Run the native generator with its original fixed arguments."""
    generated = run_json(
        [
            sys.executable,
            str(GENERATOR),
            "--family",
            "all",
            "--include-axioms",
            "--include-theorems",
            "--output",
            paths["seed_jsonl"],
            "--json",
        ]
    )
    return generated


def index(paths, context):
    """Run the native indexer; context locates the existing Vampire reports."""
    indexed = run_json(
        [
            sys.executable,
            str(INDEXER),
            "--kb-root",
            paths["kb_root"],
            "--seed-jsonl",
            paths["seed_jsonl"],
            "--vampire-artifact-root",
            context["vampire_artifact_root"],
            "--vampire-limit",
            "8",
            "--build-bloom",
            "--build-embeddings",
            "--embedding-dimension",
            "256",
            "--smoke-query",
            "inverse of a triple product in a group reverses order",
            "--json",
        ]
    )
    return indexed


def finish(request, paths, generated, indexed):
    """Evaluate and emit the original assertions, including empty-hit falsiness."""
    artifact_root = Path(paths["artifact_root"])
    seed_jsonl = Path(paths["seed_jsonl"])
    top_ids = [hit["entry"]["id"] for hit in indexed["smoke_hits"]]
    assertions = {
        "generator_ok": generated["ok"],
        "generator_wrote_seed_jsonl": seed_jsonl.is_file(),
        "generator_has_axioms_and_theorems": generated["entry_count"] >= 10,
        "indexer_ok": indexed["ok"],
        "indexer_added_entries": indexed["added_count"] >= 10,
        "bloom_manifest_written": Path(indexed["bloom_paths"]["manifest"]).is_file(),
        "embedding_index_written": Path(indexed["embedding_index"]).is_file(),
        "smoke_query_finds_triple": top_ids
        and top_ids[0] == "group.inverse_triple_product_reverse_order",
    }
    payload = {
        "ok": all(assertions.values()),
        "artifact_root": str(artifact_root),
        "assertions": assertions,
        "top_hit_ids": top_ids,
        "generated_entry_count": generated["entry_count"],
        "indexed_entry_count": indexed["entry_count"],
    }
    if request["json"]:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {payload['ok']}")
        print(f"artifact_root: {payload['artifact_root']}")
        print(f"top_hit_ids: {', '.join(top_ids)}")
    return {"result": payload, "exit_code": 0 if payload["ok"] else 3}


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Protect Mathformer behavior while the framework evolves across Lean, ATP, KB, SymPy, docs, and skills.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("artifacts/kb/premise_kb_skill_script_test"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    request = {"artifact_root": str(args.artifact_root), "json": args.json}
    paths = prepare(request)
    generated = generate(paths)
    indexed = index(paths, {"vampire_artifact_root": "artifacts/vampire_atp"})
    return finish(request, paths, generated, indexed)["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

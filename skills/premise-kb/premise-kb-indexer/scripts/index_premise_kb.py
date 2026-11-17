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

"""Index theorem/axiom seed lists and proof artifacts into backends.premise_kb.MathformerKB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.premise_kb.MathformerKB.indexing import (
    build_bloom_indexes,
    build_embedding_index,
)
from backends.premise_kb.MathformerKB.ingest import (
    entries_from_vampire_artifacts,
)
from backends.premise_kb.MathformerKB.schema import (
    KBEntry,
)
from backends.premise_kb.MathformerKB.search import (
    PremiseKB,
)
from backends.premise_kb.MathformerKB.storage import (
    KBStore,
)


def parse_options(extra_args=None):
    """Parse the native CLI without initializing or writing a store."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb-root", type=Path, default=Path("artifacts/kb/premise_kb"))
    parser.add_argument("--seed-jsonl", action="append", type=Path, default=[])
    parser.add_argument("--corpus-jsonl", action="append", type=Path, default=[])
    parser.add_argument("--vampire-artifact-root", type=Path)
    parser.add_argument("--vampire-limit", type=int)
    parser.add_argument("--build-bloom", action="store_true")
    parser.add_argument("--build-embeddings", action="store_true")
    parser.add_argument("--embedding-dimension", type=int, default=512)
    parser.add_argument("--smoke-query")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(extra_args)


def initialize(extra_args=None, before_write=None):
    """Initialize native locals as JSON-safe state; the store remains on disk."""
    args = parse_options(extra_args)
    kb_root = repo_path(args.kb_root)
    if before_write is not None:
        before_write(kb_root)
    store = KBStore(kb_root)
    store.init()
    options = vars(args).copy()
    for key in ("kb_root", "vampire_artifact_root"):
        options[key] = str(options[key]) if options[key] is not None else None
    for key in ("seed_jsonl", "corpus_jsonl"):
        options[key] = [str(path) for path in options[key]]
    files = options["seed_jsonl"] + options["corpus_jsonl"]
    return {
        "options": options,
        "store": {"root": str(kb_root)},
        "files": files,
        "cursor": 0,
        "results": [],
        "vampire_count": 0,
        "bloom_paths": {},
        "embedding_index": None,
        "smoke_hits": [],
        "has_files": bool(files),
        "vampire": bool(args.vampire_artifact_root),
        "bloom": bool(args.build_bloom),
        "embeddings": bool(args.build_embeddings),
        "smoke": bool(args.smoke_query),
    }


def ingest_file(state):
    """Fully read one seed/corpus before insertion, preserving duplicate history."""
    entries = read_entry_jsonl(repo_path(Path(state["files"][state["cursor"]])))
    results = KBStore(Path(state["store"]["root"])).add_entries(entries)
    state["results"].extend(result.to_dict() for result in results)
    state["cursor"] += 1
    return {"state": state, "done": state["cursor"] >= len(state["files"])}


def retain(state):
    """Carry locals across an inactive native branch."""
    return state


def ingest_vampire(state):
    """Accumulate all entries from sorted, sliced reports before inserting."""
    options = state["options"]
    entries = entries_from_vampire_artifacts(
        repo_path(Path(options["vampire_artifact_root"])),
        limit=options["vampire_limit"],
    )
    state["vampire_count"] = len(entries)
    results = KBStore(Path(state["store"]["root"])).add_entries(entries)
    state["results"].extend(result.to_dict() for result in results)
    return state


def build_bloom(state):
    """Build the native Bloom indexes after all ingestion."""
    state["bloom_paths"] = build_bloom_indexes(KBStore(Path(state["store"]["root"])))
    return state


def build_embeddings(state):
    """Build deterministic native embeddings using the original dimension."""
    state["embedding_index"] = build_embedding_index(
        KBStore(Path(state["store"]["root"])),
        dimension=state["options"]["embedding_dimension"],
    )
    return state


def search(state):
    """Search the completed index with the native fixed top-five bound."""
    state["smoke_hits"] = PremiseKB(Path(state["store"]["root"])).search_semantic(
        state["options"]["smoke_query"], k=5
    )
    return state


def report(state):
    """Emit the source-owned report and return its payload and native exit code."""
    from argparse import Namespace

    options = state["options"].copy()
    for key in ("seed_jsonl", "corpus_jsonl"):
        options[key] = [Path(path) for path in options[key]]
    args = Namespace(**options)
    kb_root = Path(state["store"]["root"])
    store = KBStore(kb_root)
    results = state["results"]
    vampire_count = state["vampire_count"]
    bloom_paths = state["bloom_paths"]
    embedding_path = state["embedding_index"]
    smoke_hits = state["smoke_hits"]
    payload = {
        "ok": True,
        "kb_root": str(kb_root),
        "seed_jsonl": [str(repo_path(path)) for path in args.seed_jsonl],
        "corpus_jsonl": [str(repo_path(path)) for path in args.corpus_jsonl],
        "vampire_candidate_count": vampire_count,
        "add_results": state["results"],
        "added_count": sum(1 for result in results if result["added"]),
        "duplicate_count": sum(1 for result in results if not result["added"]),
        "bloom_paths": bloom_paths,
        "embedding_index": embedding_path,
        "smoke_hits": smoke_hits,
        **store.report(),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {payload['ok']}")
        print(f"kb_root: {payload['kb_root']}")
        print(f"added_count: {payload['added_count']}")
        print(f"duplicate_count: {payload['duplicate_count']}")
        print(f"entry_count: {payload['entry_count']}")
        if embedding_path:
            print(f"embedding_index: {embedding_path}")
    return {"result": payload, "exit_code": 0}


def main() -> int:
    """Run the same shared steps through the original unbounded native CLI."""
    state = initialize()
    while state["cursor"] < len(state["files"]):
        state = ingest_file(state)["state"]
    if state["vampire"]:
        state = ingest_vampire(state)
    if state["bloom"]:
        state = build_bloom(state)
    if state["embeddings"]:
        state = build_embeddings(state)
    if state["smoke"]:
        if not state["embeddings"]:
            state = build_embeddings(state)
        state = search(state)
    return report(state)["exit_code"]


def repo_path(path: Path) -> Path:
    """Document the responsibility of ``repo_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``repo_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return path if path.is_absolute() else REPO_ROOT / path


def read_entry_jsonl(path: Path) -> list[KBEntry]:
    """Document the responsibility of ``read_entry_jsonl``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entries.append(KBEntry.from_dict(json.loads(line)))
    return entries


if __name__ == "__main__":
    raise SystemExit(main())

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

"""Generate theorem/axiom seed lists as MathformerKB JSONL entries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backends.premise_kb.MathformerKB.canonicalize import (
    infer_theorem_shape,
    populate_canonical_fields,
)
from backends.premise_kb.MathformerKB.ingest import (
    now,
)
from backends.premise_kb.MathformerKB.schema import (
    FormalSurface,
    KBEntry,
    ProvenanceRecord,
)

SEEDS: list[dict[str, object]] = [
    {
        "id": "group.associativity",
        "family": "group",
        "kind": "axiom",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, multiplication is associative.",
        "latex": "(xy)z = x(yz)",
        "formal": "! [X,Y,Z] : ( mul(mul(X,Y),Z) = mul(X,mul(Y,Z)) )",
        "symbols": ["mul"],
    },
    {
        "id": "group.left_identity",
        "family": "group",
        "kind": "axiom",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, the identity element multiplied on the left leaves every element unchanged.",
        "latex": "ex = x",
        "formal": "! [X] : ( mul(e,X) = X )",
        "symbols": ["e", "mul"],
    },
    {
        "id": "group.right_identity",
        "family": "group",
        "kind": "axiom",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, every element multiplied by the identity element on the right is unchanged.",
        "latex": "xe = x",
        "formal": "! [X] : ( mul(X,e) = X )",
        "symbols": ["e", "mul"],
    },
    {
        "id": "group.left_inverse",
        "family": "group",
        "kind": "axiom",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, the inverse of an element multiplied on the left gives the identity.",
        "latex": "x^{-1}x = e",
        "formal": "! [X] : ( mul(inv(X),X) = e )",
        "symbols": ["e", "inv", "mul"],
    },
    {
        "id": "group.right_inverse",
        "family": "group",
        "kind": "axiom",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, an element multiplied by its inverse on the right gives the identity.",
        "latex": "xx^{-1} = e",
        "formal": "! [X] : ( mul(X,inv(X)) = e )",
        "symbols": ["e", "inv", "mul"],
    },
    {
        "id": "group.inverse_identity",
        "family": "group",
        "kind": "theorem",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, the inverse of the identity element is the identity element.",
        "latex": "e^{-1} = e",
        "formal": "inv(e) = e",
        "symbols": ["e", "inv"],
    },
    {
        "id": "group.inverse_product_reverse_order",
        "family": "group",
        "kind": "theorem",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, the inverse of a product is the product of the inverses in reverse order.",
        "latex": "(xy)^{-1} = y^{-1}x^{-1}",
        "formal": "! [X,Y] : ( inv(mul(X,Y)) = mul(inv(Y),inv(X)) )",
        "symbols": ["e", "inv", "mul"],
    },
    {
        "id": "group.inverse_triple_product_reverse_order",
        "family": "group",
        "kind": "theorem",
        "domain_tags": ["algebra", "group", "equality"],
        "informal": "In a group, the inverse of a product of three elements is the product of the inverses in reverse order.",
        "latex": "(xyz)^{-1} = z^{-1}y^{-1}x^{-1}",
        "formal": "! [X,Y,Z] : ( inv(mul(mul(X,Y),Z)) = mul(inv(Z),mul(inv(Y),inv(X))) )",
        "symbols": ["e", "inv", "mul"],
    },
    {
        "id": "relation.transitivity_axiom",
        "family": "relation",
        "kind": "axiom",
        "domain_tags": ["relation", "first_order"],
        "informal": "A transitive relation carries a link from x to z whenever it has links from x to y and y to z.",
        "latex": "r(x,y) \\land r(y,z) \\Rightarrow r(x,z)",
        "formal": "! [X,Y,Z] : ( ( r(X,Y) & r(Y,Z) ) => r(X,Z) )",
        "symbols": ["r"],
    },
    {
        "id": "relation.irreflexivity_axiom",
        "family": "relation",
        "kind": "axiom",
        "domain_tags": ["relation", "first_order"],
        "informal": "An irreflexive relation never relates an element to itself.",
        "latex": "\\neg r(x,x)",
        "formal": "! [X] : ~ r(X,X)",
        "symbols": ["r"],
    },
    {
        "id": "relation.transitive_irreflexive_asymmetric",
        "family": "relation",
        "kind": "theorem",
        "domain_tags": ["relation", "first_order"],
        "informal": "Every transitive and irreflexive binary relation is asymmetric.",
        "latex": "transitive(r) \\land irreflexive(r) \\Rightarrow asymmetric(r)",
        "formal": "! [X,Y] : ( r(X,Y) => ~ r(Y,X) )",
        "symbols": ["r"],
    },
    {
        "id": "set.subset_definition",
        "family": "set",
        "kind": "axiom",
        "domain_tags": ["set", "membership", "first_order"],
        "informal": "A set is a subset of another set exactly when every member of the first is a member of the second.",
        "latex": "A \\subseteq B \\Leftrightarrow \\forall x, x \\in A \\Rightarrow x \\in B",
        "formal": "! [A,B] : ( subset(A,B) <=> (! [X] : ( member(X,A) => member(X,B) )) )",
        "symbols": ["member", "subset"],
    },
    {
        "id": "set.subset_transitive",
        "family": "set",
        "kind": "theorem",
        "domain_tags": ["set", "membership", "first_order"],
        "informal": "If one set is a subset of a second and the second is a subset of a third, then the first is a subset of the third.",
        "latex": "R \\subseteq S \\land S \\subseteq T \\Rightarrow R \\subseteq T",
        "formal": "subset(r,s) & subset(s,t) => subset(r,t)",
        "symbols": ["member", "subset"],
    },
]


def parse_options(extra_args: list[str] | None = None) -> dict:
    """Parse the native CLI, retaining argparse exits."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family",
        action="append",
        choices=["all", "group", "relation", "set"],
        default=[],
    )
    parser.add_argument("--include-axioms", action="store_true")
    parser.add_argument("--include-theorems", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/kb/generated_theorem_axiom_seeds.jsonl"),
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(extra_args)

    families = set(args.family or ["all"])
    if "all" in families:
        families = {"group", "relation", "set"}
    kinds = set()
    if args.include_axioms:
        kinds.add("axiom")
    if args.include_theorems:
        kinds.add("theorem")
    if not kinds:
        kinds = {"axiom", "theorem"}

    return {
        "families": sorted(families),
        "kinds": sorted(kinds),
        "output": str(args.output),
        "json": args.json,
    }


def inspect_seed(options: dict, state: dict) -> dict:
    """Inspect the next source seed in order."""
    seed = SEEDS[state["index"]]
    return {
        "seed": seed,
        "matches": str(seed["family"]) in options["families"]
        and str(seed["kind"]) in options["kinds"],
    }


def retain_advance(state: dict, seed: dict) -> dict:
    return {
        "index": state["index"] + 1,
        "entries": [*state["entries"], make_entry(seed).to_dict()],
    }


def skip_advance(state: dict) -> dict:
    return {"index": state["index"] + 1, "entries": state["entries"]}


def scan_done(state: dict) -> bool:
    return state["index"] == len(SEEDS)


def write_report(options: dict, state: dict) -> dict:
    """Write and report using native serialization and path semantics."""
    entries = state["entries"]
    output = (
        Path(options["output"])
        if Path(options["output"]).is_absolute()
        else REPO_ROOT / options["output"]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
            for entry in entries
        ),
        encoding="utf-8",
    )
    payload = {
        "ok": True,
        "output": str(output),
        "entry_count": len(entries),
        "families": options["families"],
        "kinds": options["kinds"],
        "entry_ids": [entry["id"] for entry in entries],
    }
    if options["json"]:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {payload['ok']}")
        print(f"output: {payload['output']}")
        print(f"entry_count: {payload['entry_count']}")
    return {"report": payload, "exit_code": 0}


def main() -> int:
    """Coordinate shared native steps."""
    options = parse_options()
    state = {"index": 0, "entries": []}
    while not scan_done(state):
        inspected = inspect_seed(options, state)
        state = (
            retain_advance(state, inspected["seed"])
            if inspected["matches"]
            else skip_advance(state)
        )
    return write_report(options, state)["exit_code"]


def make_entry(seed: dict[str, object]) -> KBEntry:
    """Document the responsibility of ``make_entry``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    kind = str(seed["kind"])
    provenance = ProvenanceRecord(
        kind="generated",
        source="premise-kb-theorem-seed-generator",
        retrieved_at=now(),
        confidence="medium",
        notes=f"seed_kind={kind}; family={seed['family']}",
    )
    entry = KBEntry(
        id=str(seed["id"]),
        status="generated_candidate",
        domain_tags=list(seed["domain_tags"]),  # type: ignore[arg-type]
        informal_statement=str(seed["informal"]),
        latex_statement=str(seed["latex"]),
        formal_statements=[
            FormalSurface(
                system="tptp", statement=str(seed["formal"]), status="candidate"
            )
        ],
        symbols=list(seed["symbols"]),  # type: ignore[arg-type]
        theorem_shape=sorted(infer_theorem_shape(str(seed["formal"]))),
        provenance=[provenance],
        notes=f"seed_kind={kind}",
    )
    return populate_canonical_fields(entry)


if __name__ == "__main__":
    raise SystemExit(main())

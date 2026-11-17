#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test held-out physics IR intake and cross-backend semantic parity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from libraries.MathformerPhysicsLib.physics_ir import (  # noqa: E402 - direct-script path setup above
    backend_packet,
    compare_backend_packets,
    from_case_spec,
    validate_ir,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    held_out = {
        "statement_nl": "A held-out wave travels a distance d = v t.",
        "statement_latex": "d=v t",
        "target": "distance",
        "source_anchors": ["heldout_L001"],
        "quantities": {
            "d": ["distance", "length", "meter"],
            "v": ["speed", "velocity", "meter/second"],
            "t": ["duration", "time", "second"],
        },
        "assumptions": ["constant speed", "one-dimensional path"],
        "frame": {"dimension": "1D", "axis": "path"},
        "laws": ["distance equals speed times time"],
    }
    steps = [
        {
            "id": "heldout_source_law",
            "kind": "source_equation",
            "expression": "Eq(d, v*t)",
            "source_anchors": ["heldout_L001"],
        }
    ]
    ir = from_case_spec("heldout_wave_9001", held_out, steps=steps)
    lean = backend_packet(ir, backend="lean", artifact_path="candidate.lean")
    sympy = backend_packet(ir, backend="sympy", artifact_path="candidate.py")
    isabelle = backend_packet(ir, backend="isabelle", artifact_path="Candidate.thy")
    parity = compare_backend_packets([lean, sympy, isabelle])
    hidden_assumption = dict(sympy)
    hidden_assumption["assumption_ids"] = [
        *sympy["assumption_ids"],
        "assumption_hidden_positivity",
    ]
    hidden = compare_backend_packets([lean, hidden_assumption])
    cases = {
        "held_out_intake_without_registry_branch": not validate_ir(ir),
        "shared_obligations_cross_backends": parity["semantic_parity"] is True,
        "hidden_backend_assumption_detected": hidden["semantic_parity"] is False
        and any(
            item["code"] == "cross_backend_assumption_ids_mismatch"
            for item in hidden["findings"]
        ),
        "source_digest_shared": len(
            {item["source_digest"] for item in (lean, sympy, isabelle)}
        )
        == 1,
    }
    payload = {
        "schema_version": 1,
        "suite": "physics_ir_contract",
        "ok": all(cases.values()),
        "cases": cases,
        "ir_digest": ir.ir_digest,
        "parity": parity,
        "hidden_assumption_parity": hidden,
    }
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

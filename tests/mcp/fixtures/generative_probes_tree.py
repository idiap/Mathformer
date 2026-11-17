# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic validation inputs; the unmodified native leaf executes locally.

There is no model/provider or external compiler in this selected workflow.
The independent reasoning_route_compiler fixture covers the hub's generic
external compiler timeout/launch/audit boundary without replacing this leaf.
"""

import json

LEAF = "tests/run_generative.py"
CRITERIA = "tests/generative/quality_criteria.json"
PROBES = "tests/generative/probes/probes.json"
REPORT = "artifacts/test_program/generative/probe_validation_report.json"


def put(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path


def populate(root, project, mode="valid"):
    put(root, LEAF, (project / LEAF).read_text())
    put(
        root,
        CRITERIA,
        json.dumps({"required_fields": ["probe_id", "prompt", "forbidden_claims"]}),
    )
    good = {
        "probe_id": "fixture-good",
        "prompt": "synthetic input",
        "forbidden_claims": ["proof established"],
    }
    probes = [good]
    if mode == "empty":
        probes = []
    elif mode == "invalid":
        # Beyond the route bound: the leaf must visit every probe, without an
        # invented count cap or stopping after the first error.
        probes = [good] * 129 + [
            {"probe_id": "broken-first"},
            {"probe_id": "broken-last", "prompt": "x", "forbidden_claims": []},
        ]
    put(root, PROBES, json.dumps({"probes": probes}))
    if mode == "malformed":
        put(root, PROBES, "{invalid json")


def stable(value):
    """Remove only the native wall-clock run id when comparing executions."""
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items() if key != "run_id"}
    if isinstance(value, list):
        return [stable(item) for item in value]
    if isinstance(value, str) and value.startswith("{"):
        try:
            return stable(json.loads(value))
        except json.JSONDecodeError:
            pass
    return value

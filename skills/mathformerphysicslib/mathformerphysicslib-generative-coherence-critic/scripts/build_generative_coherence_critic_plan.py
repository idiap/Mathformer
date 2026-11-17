#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Build generative critic probes for MathformerPhysicsLib coherence."""

from __future__ import annotations

from typing import Any

import argparse
import json
from pathlib import Path
import sys

SCRIPT_ROOT = (
    Path(__file__).resolve().parents[2]
    / "mathformerphysicslib-coherence-inventory-builder"
    / "scripts"
)
sys.path.insert(0, str(SCRIPT_ROOT))

from coherence_common import (  # noqa: E402 - direct-script path setup above
    audit_grounding,
    build_inventory,
    canonicalize,
    critic_api,
    critic_integration,
    critic_redefinitions,
    generative_plan,
    load_json,
    self_test_payload,
    write_json,
)


def default_reports(
    self_test: bool = False, repository_root: Path | None = None
) -> list[dict[str, Any]]:
    inventory = (
        self_test_payload(repository_root)
        if self_test
        else build_inventory(repository_root)
    )
    graph = canonicalize(inventory)
    grounding = audit_grounding(graph)
    return [
        grounding,
        critic_redefinitions(graph, grounding),
        critic_integration(inventory, graph, repository_root),
        critic_api(graph, repository_root),
    ]


def main(
    argv: list[str] | None = None,
    *,
    repository_root: Path | None = None,
    stage_observer=None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    reports = (
        [load_json(path) for path in args.report]
        if args.report
        else default_reports(args.self_test, repository_root)
    )
    if stage_observer is not None:
        stage_observer("reports", reports)
    payload = generative_plan(reports)
    if stage_observer is not None:
        stage_observer("plan", payload)
    if args.self_test:
        assert payload["probe_count"] == 7
        assert payload["codex_exec_policy"]["enabled"] is True
        assert (
            payload["blocking_policy"]["may_block_only_with_deterministic_evidence"]
            is True
        )
        assert all(probe.get("expected_report_schema") for probe in payload["probes"])
        assert any(
            probe["id"] == "negative_control_incoherent_repair"
            for probe in payload["probes"]
        )
    if args.output:
        write_json(payload, args.output)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    # A controller may observe/pause the real child between source stages.
    # This is a transport channel, never an alternate planning implementation.
    import os

    if os.environ.get("MATHFORMER_GENERATIVE_STAGE_IO") == "1":

        def observe(stage, value):
            print(
                "mathformer-stage:" + stage + ":" + json.dumps(value),
                file=sys.stderr,
                flush=True,
            )
            if sys.stdin.readline().strip() != stage:
                raise RuntimeError("staged child continuation was closed or mismatched")

        raise SystemExit(
            main(
                sys.argv[1:],
                repository_root=Path(
                    os.environ["MATHFORMER_GENERATIVE_REPOSITORY_ROOT"]
                ),
                stage_observer=observe,
            )
        )
    raise SystemExit(main(sys.argv[1:]))

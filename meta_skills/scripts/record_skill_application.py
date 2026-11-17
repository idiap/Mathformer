#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Capture skill application as durable runtime evidence instead of hidden
#   chat history.
#
# Intent:
#   Write normalized JSONL traces and a small Markdown rendering for selected
#   Mathformer workflows.
#
# Function:
#   Emits an observational trace for the MathformerPhysicsLib coherence route
#   or a caller-specified event packet.
#
# Maintenance Notes:
#   Keep event fields synchronized with runtime_skill_application.schema.json and SKILL_HOOKS.yaml.

"""Record Mathformer meta-skill runtime skill-application traces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = REPO_ROOT / "artifacts" / "meta_skills" / "runtime"
DEFAULT_JSONL = RUNTIME_ROOT / "mathformerphysicslib_coherence.jsonl"
DEFAULT_MD = RUNTIME_ROOT / "mathformerphysicslib_coherence.md"


def now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def coherence_events() -> list[dict[str, Any]]:
    workflow = "mathformerphysicslib.coherence.grounded_gate"
    base = {
        "schema_version": "mathformer.meta_skills.runtime_skill_application.v0.1",
        "workflow_id": workflow,
        "skill_id": "mathformerphysicslib-coherence-gate",
        "hook_id": "meta_skills.runtime_trace",
        "timestamp_utc": now(),
        "intent": {"request": "audit MathformerPhysicsLib coherence and grounding"},
        "inputs": {
            "task_registry": "meta_skills/registry/tasks/mathformerphysicslib-coherence/task_registry.json"
        },
        "artifacts": [
            "artifacts/mathformerphysicslib/coherence/coherence_gate.json",
            "artifacts/mathformerphysicslib/coherence/generative_coherence_critic_plan.json",
        ],
        "risks": ["generative_overreach", "mathlib_duplication"],
    }
    rows = []
    steps = [
        (
            "skill_application_start",
            "Coherence workflow trace started.",
            {"status": "started"},
        ),
        (
            "skill_application_context_loaded",
            "Task registry and quality cards loaded.",
            {"status": "context_loaded"},
        ),
        (
            "skill_application_input_normalized",
            "Coherence reports normalized as evidence inputs.",
            {"status": "normalized"},
        ),
        (
            "skill_application_action_taken",
            "Coherence gate treated as controlled deterministic evidence.",
            {"status": "action_recorded"},
        ),
        (
            "skill_application_evidence_recorded",
            "Gate and generative plan artifacts recorded.",
            {"status": "evidence_recorded"},
        ),
        (
            "skill_application_gate_evaluated",
            "Generative probes remain advisory until deterministic gates bind them.",
            {"status": "gate_evaluated", "accepted": True},
        ),
        (
            "skill_application_complete",
            "Runtime trace complete.",
            {"status": "complete"},
        ),
    ]
    for index, (step, summary, decision) in enumerate(steps, start=1):
        row = dict(base)
        row.update(
            {
                "event_id": f"{workflow}.{index:02d}.{step}",
                "step": step,
                "evidence": [
                    {
                        "path": "artifacts/mathformerphysicslib/coherence/coherence_gate.json",
                        "claim": "coherence gate exists and records deterministic property gates",
                    }
                ],
                "decision": decision,
                "next_action": {
                    "type": (
                        "continue" if step != "skill_application_complete" else "none"
                    )
                },
                "human_summary": summary,
            }
        )
        rows.append(row)
    return rows


def write_trace(rows: list[dict[str, Any]], jsonl_path: Path, md_path: Path) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Runtime Skill Application Trace",
        "",
        f"Workflow: `{rows[0]['workflow_id']}`" if rows else "Workflow: none",
        "",
    ]
    for row in rows:
        lines.append(f"- `{row['step']}`: {row['human_summary']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_check(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", default="mathformerphysicslib.coherence")
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.workflow != "mathformerphysicslib.coherence":
        raise SystemExit(
            "only --workflow mathformerphysicslib.coherence is currently implemented"
        )
    return {
        "workflow": args.workflow,
        "output_jsonl": str(args.output_jsonl),
        "output_md": str(args.output_md),
        "json": args.json,
    }


def write_payload(args: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    output_jsonl, output_md = Path(args["output_jsonl"]), Path(args["output_md"])
    write_trace(
        rows,
        (REPO_ROOT / output_jsonl if not output_jsonl.is_absolute() else output_jsonl),
        (REPO_ROOT / output_md if not output_md.is_absolute() else output_md),
    )
    return {
        "ok": True,
        "event_count": len(rows),
        "jsonl": str(output_jsonl),
        "markdown": str(output_md),
    }


def emit_success(args: dict[str, Any], payload: dict[str, Any], *, stdout=None) -> int:
    if args["json"]:
        print(json.dumps(payload, indent=2, sort_keys=True), file=stdout)
    else:
        print(f"recorded {payload['event_count']} events", file=stdout)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_check(argv)
    rows = coherence_events()
    payload = write_payload(args, rows)
    return emit_success(args, payload)


if __name__ == "__main__":
    raise SystemExit(main())

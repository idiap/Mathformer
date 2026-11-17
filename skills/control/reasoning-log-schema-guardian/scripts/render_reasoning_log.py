#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Reasoning logs should be inspectable by humans, not only by schema
#   validators or downstream metrics.
#
# Intent:
#   Render JSONL events into a compact Markdown trace grouped by skill
#   invocation, with artifact references, evidence, risks, and decisions.
#
# Function:
#   Reads a Mathformer reasoning-log JSONL file and writes Markdown or JSON
#   summary output.
#
# Maintenance Notes:
#   Keep this renderer tolerant of older logs. Missing skill-application fields
#   should degrade gracefully instead of blocking inspection.

"""Render Mathformer reasoning logs as human-readable Markdown."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence


def load_events(path: Path) -> List[Dict[str, Any]]:
    """Load parseable JSONL events and preserve malformed lines as findings."""
    events: List[Dict[str, Any]] = []
    for line_no, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            events.append(
                {
                    "event_index": None,
                    "step": "invalid_json",
                    "payload": {
                        "skill": "reasoning-log-schema-guardian",
                        "human_summary": f"Line {line_no} is invalid JSON: {exc.msg}",
                    },
                    "_line": line_no,
                }
            )
            continue
        if isinstance(parsed, dict):
            parsed["_line"] = line_no
            events.append(parsed)
    return events


def event_skill_application(event: Dict[str, Any]) -> Dict[str, Any]:
    """Return the canonical skill-application object or a compatibility view."""
    payload = event.get("payload")
    if not isinstance(payload, dict):
        payload = {}
    application = payload.get("skill_application")
    if isinstance(application, dict):
        return application
    return {
        "schema_version": 0,
        "skill": payload.get("skill", "unknown-skill"),
        "hook_id": payload.get("hook_id"),
        "run_id": payload.get("run_id"),
        "skill_call_id": payload.get("skill_call_id")
        or f"legacy-{payload.get('skill', 'unknown')}",
        "parent_call_id": payload.get("parent_call_id"),
        "status": payload.get("status", "observed"),
        "intent": payload.get("intent", ""),
        "inputs": {},
        "artifacts": payload.get("artifacts", {}),
        "evidence": {
            key: value
            for key, value in payload.items()
            if key not in {"skill", "hook_id", "agent_usage", "convergence_criteria"}
        },
        "decision": {},
        "risks": {},
        "next_action": "",
        "human_summary": payload.get("human_summary", ""),
    }


def compact_json(value: Any) -> str:
    """Render small JSON snippets on one line for Markdown tables."""
    if value in ({}, [], None, ""):
        return ""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_summary(events: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Group events by skill invocation and collect high-signal fields."""
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in events:
        application = event_skill_application(event)
        call_id = application.get("skill_call_id") or "unknown-call"
        groups[str(call_id)].append(event)

    invocations: List[Dict[str, Any]] = []
    for call_id, grouped_events in groups.items():
        first = event_skill_application(grouped_events[0])
        last = event_skill_application(grouped_events[-1])
        invocations.append(
            {
                "skill_call_id": call_id,
                "skill": last.get("skill") or first.get("skill"),
                "hook_id": last.get("hook_id") or first.get("hook_id"),
                "run_id": last.get("run_id") or first.get("run_id"),
                "parent_call_id": last.get("parent_call_id")
                or first.get("parent_call_id"),
                "status": last.get("status"),
                "intent": last.get("intent") or first.get("intent"),
                "inputs": first.get("inputs") or {},
                "artifacts": last.get("artifacts") or first.get("artifacts") or {},
                "evidence": last.get("evidence") or {},
                "decision": last.get("decision") or {},
                "risks": last.get("risks") or {},
                "next_action": last.get("next_action") or "",
                "human_summary": last.get("human_summary")
                or first.get("human_summary")
                or "",
                "event_count": len(grouped_events),
                "steps": [event.get("step") for event in grouped_events],
            }
        )

    return {
        "event_count": len(events),
        "skill_invocation_count": len(invocations),
        "invocations": invocations,
    }


def render_markdown(summary: Dict[str, Any], *, title: str) -> str:
    """Render a summary packet as Markdown."""
    lines = [
        f"# {title}",
        "",
        f"- events: `{summary['event_count']}`",
        f"- skill invocations: `{summary['skill_invocation_count']}`",
        "",
    ]
    for index, invocation in enumerate(summary["invocations"], 1):
        lines.extend(
            [
                f"## {index}. {invocation['skill']}",
                "",
                f"- status: `{invocation.get('status')}`",
                f"- hook: `{invocation.get('hook_id')}`",
                f"- skill call: `{invocation.get('skill_call_id')}`",
            ]
        )
        if invocation.get("intent"):
            lines.append(f"- intent: {invocation['intent']}")
        if invocation.get("human_summary"):
            lines.append(f"- summary: {invocation['human_summary']}")
        if invocation.get("next_action"):
            lines.append(f"- next action: {invocation['next_action']}")
        lines.extend(["", "| Section | Content |", "| --- | --- |"])
        for label in ("inputs", "artifacts", "evidence", "decision", "risks"):
            lines.append(f"| {label} | `{compact_json(invocation.get(label))}` |")
        lines.append(
            f"| steps | `{', '.join(str(step) for step in invocation['steps'])}` |"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, required=True)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--title", default="Mathformer Reasoning Trace")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Render the requested reasoning log."""
    args = parse_args(argv)
    events = load_events(args.log_file)
    summary = build_summary(events)
    rendered = (
        json.dumps(summary, ensure_ascii=False, indent=2)
        if args.json
        else render_markdown(summary, title=args.title)
    )
    if args.output_file is not None:
        args.output_file.parent.mkdir(parents=True, exist_ok=True)
        args.output_file.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="" if rendered.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

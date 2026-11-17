#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make every deterministic Mathformer script usable inside a self-explaining
#   reasoning-log envelope, even before that script has native instrumentation.
#
# Intent:
#   Provide a thin, dependency-free wrapper that records skill start, action,
#   completion, and error events around an arbitrary subprocess command.
#
# Function:
#   Emits canonical skill-application events through reasoning_log.py, runs the
#   target command, and returns the target command's exit code.
#
# Maintenance Notes:
#   Keep this wrapper conservative. It should not parse target output or hide
#   subprocess failures; it only records structured execution evidence.

"""Run a command while emitting canonical Mathformer skill-application logs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reasoning_log import (  # noqa: E402
    append_skill_complete,
    append_skill_error,
    append_skill_progress,
    append_skill_start,
)


def parse_json_object(raw: Optional[str], *, label: str) -> Dict[str, Any]:
    """Parse an optional JSON object argument with a clear error boundary."""
    if raw in (None, ""):
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError(f"{label} must be a JSON object")
    return parsed


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse wrapper arguments and the command passed after `--`."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reasoning-log-file", type=Path, required=True)
    parser.add_argument("--skill", required=True)
    parser.add_argument("--hook-id")
    parser.add_argument("--run-id")
    parser.add_argument("--parent-call-id")
    parser.add_argument("--intent", default="")
    parser.add_argument("--inputs-json")
    parser.add_argument("--artifacts-json")
    parser.add_argument("--risks-json")
    parser.add_argument("--human-summary", default="")
    parser.add_argument("--next-action", default="")
    parser.add_argument(
        "--update-index",
        action="store_true",
        help="Update artifacts/reasoning/index.json after the wrapped command finishes.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run. Separate wrapper options from the command with --.",
    )
    args = parser.parse_args(argv)
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a command must be provided after --")
    return args


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the target command and log a complete skill-application lifecycle."""
    args = parse_args(argv)
    inputs = parse_json_object(args.inputs_json, label="--inputs-json")
    artifacts = parse_json_object(args.artifacts_json, label="--artifacts-json")
    risks = parse_json_object(args.risks_json, label="--risks-json")
    command_text = " ".join(args.command)
    inputs.setdefault("command", args.command)

    skill_call_id = append_skill_start(
        args.reasoning_log_file,
        skill=args.skill,
        hook_id=args.hook_id,
        parent_call_id=args.parent_call_id,
        run_id=args.run_id,
        intent=args.intent or f"Run {args.skill} through a logged wrapper.",
        inputs=inputs,
        artifacts=artifacts,
        risks=risks,
        human_summary=args.human_summary
        or f"Started logged execution of `{command_text}`.",
    )
    append_skill_progress(
        args.reasoning_log_file,
        phase="action_taken",
        skill=args.skill,
        hook_id=args.hook_id,
        skill_call_id=skill_call_id,
        parent_call_id=args.parent_call_id,
        run_id=args.run_id,
        intent=args.intent,
        inputs=inputs,
        artifacts=artifacts,
        risks=risks,
        evidence={"command": args.command},
        human_summary=f"Running `{command_text}`.",
    )
    try:
        completed = subprocess.run(args.command, check=False)
    except OSError as exc:
        append_skill_error(
            args.reasoning_log_file,
            skill=args.skill,
            hook_id=args.hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=args.parent_call_id,
            run_id=args.run_id,
            intent=args.intent,
            inputs=inputs,
            artifacts=artifacts,
            risks={"subprocess_error": str(exc), **risks},
            next_action=args.next_action or "Inspect command availability and paths.",
            error=str(exc),
        )
        return 127

    evidence = {"returncode": completed.returncode, "command": args.command}
    if completed.returncode == 0:
        append_skill_complete(
            args.reasoning_log_file,
            skill=args.skill,
            hook_id=args.hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=args.parent_call_id,
            run_id=args.run_id,
            intent=args.intent,
            inputs=inputs,
            artifacts=artifacts,
            evidence=evidence,
            decision={"status": "pass", "returncode": completed.returncode},
            risks=risks,
            next_action=args.next_action,
            human_summary=f"`{command_text}` completed successfully.",
        )
    else:
        append_skill_error(
            args.reasoning_log_file,
            skill=args.skill,
            hook_id=args.hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=args.parent_call_id,
            run_id=args.run_id,
            intent=args.intent,
            inputs=inputs,
            artifacts=artifacts,
            evidence=evidence,
            risks={"nonzero_returncode": completed.returncode, **risks},
            next_action=args.next_action or "Inspect the failing command output.",
            error=f"command exited with {completed.returncode}",
        )
    if args.update_index:
        from index_reasoning_logs import (
            build_index,
        )  # local import avoids a wrapper startup dependency

        build_index(
            log_files=[args.reasoning_log_file],
            hooks_file=Path(__file__).resolve().parents[4]
            / "skills"
            / "SKILL_HOOKS.yaml",
            output_file=Path(__file__).resolve().parents[4]
            / "artifacts"
            / "reasoning"
            / "index.json",
        )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
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

"""Validate Mathformer reasoning-log JSONL files against the hook contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence, Set

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3}
GENERIC_SKILL_APPLICATION_STEPS = {
    "skill_application_start",
    "skill_application_context_loaded",
    "skill_application_input_normalized",
    "skill_application_action_taken",
    "skill_application_evidence_recorded",
    "skill_application_gate_evaluated",
    "skill_application_complete",
    "skill_application_error",
}
SKILL_APPLICATION_REQUIRED_FIELDS = {
    "schema_version",
    "skill",
    "skill_call_id",
    "status",
    "intent",
    "inputs",
    "artifacts",
    "evidence",
    "decision",
    "risks",
    "next_action",
    "human_summary",
}
SKILL_APPLICATION_NONEMPTY_FIELDS = {
    "schema_version",
    "skill",
    "skill_call_id",
    "status",
    "intent",
    "human_summary",
}


def finding(
    severity: str,
    code: str,
    message: str,
    *,
    line: Optional[int] = None,
    event_index: Optional[int] = None,
    step: Optional[str] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``finding``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result: Dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if line is not None:
        result["line"] = line
    if event_index is not None:
        result["event_index"] = event_index
    if step is not None:
        result["step"] = step
    return result


def parse_hook_contract(hooks_file: Optional[Path]) -> Dict[str, Any]:
    """Document the responsibility of ``parse_hook_contract``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    known_hooks: Set[str] = set()
    hook_steps: Dict[str, Set[str]] = {}
    required_payload_fields: List[str] = ["skill"]
    if hooks_file is None or not hooks_file.exists():
        return {
            "known_hooks": known_hooks,
            "hook_steps": hook_steps,
            "required_payload_fields": required_payload_fields,
        }

    current_hook: Optional[str] = None
    current_list: Optional[str] = None
    in_runtime_contract = False
    for raw_line in hooks_file.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped == "runtime_contract:":
            in_runtime_contract = True
            current_hook = None
            current_list = None
            continue
        if stripped == "hooks:":
            in_runtime_contract = False
            current_hook = None
            current_list = None
            continue
        if stripped == "direct_request_routing:":
            in_runtime_contract = False
            current_hook = None
            current_list = None
            continue

        if in_runtime_contract and stripped == "reasoning_log_required_payload_fields:":
            required_payload_fields = []
            current_list = "runtime.required_payload_fields"
            continue
        if in_runtime_contract and stripped.endswith(":"):
            current_list = None
            continue
        if in_runtime_contract and current_list == "runtime.required_payload_fields":
            if stripped.startswith("- "):
                required_payload_fields.append(stripped[2:].strip())
            continue

        hook_match = re.match(r"^-\s+id:\s*(\S+)\s*$", stripped)
        if hook_match:
            current_hook = str(hook_match.group(1))
            known_hooks.add(current_hook)
            hook_steps.setdefault(current_hook, set())
            current_list = None
            continue

        if current_hook is None:
            continue
        if stripped == "reasoning_log_steps:":
            current_list = "hook.reasoning_log_steps"
            continue
        if stripped.endswith(":"):
            current_list = None
            continue
        if current_list == "hook.reasoning_log_steps" and stripped.startswith("- "):
            hook_steps[current_hook].add(stripped[2:].strip())

    return {
        "known_hooks": known_hooks,
        "hook_steps": hook_steps,
        "required_payload_fields": required_payload_fields or ["skill"],
    }


def load_entries(log_file: Path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Document the responsibility of ``load_entries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    entries: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    if not log_file.exists():
        findings.append(
            finding("high", "log_missing", f"Reasoning log not found: {log_file}")
        )
        return entries, findings

    for line_no, raw_line in enumerate(
        log_file.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(
                finding(
                    "high",
                    "invalid_json",
                    f"Line is not valid JSON: {exc.msg}",
                    line=line_no,
                )
            )
            continue
        if not isinstance(parsed, dict):
            findings.append(
                finding(
                    "high",
                    "non_object_event",
                    "Reasoning log event must be a JSON object.",
                    line=line_no,
                )
            )
            continue
        parsed["_line"] = line_no
        entries.append(parsed)
    return entries, findings


def validate_entries(
    entries: Sequence[Dict[str, Any]],
    *,
    known_hooks: Set[str],
    hook_steps: Dict[str, Set[str]],
    required_payload_fields: Sequence[str],
    strict: bool,
    require_instrumentation: bool = False,
    require_skill_application: bool = False,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``validate_entries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    findings: List[Dict[str, Any]] = []
    previous_index: Optional[int] = None
    previous_timestamp_ms: Optional[int] = None

    for ordinal, event in enumerate(entries, 1):
        line = event.get("_line")
        step = event.get("step")
        event_index = event.get("event_index")

        if not isinstance(step, str) or not step:
            findings.append(
                finding(
                    "high",
                    "missing_step",
                    "Event is missing a non-empty step.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                )
            )

        payload = event.get("payload")
        if not isinstance(payload, dict):
            findings.append(
                finding(
                    "high",
                    "missing_payload",
                    "Event is missing a payload object.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )
            payload = {}

        for field in required_payload_fields:
            if field not in payload or payload.get(field) in (None, ""):
                findings.append(
                    finding(
                        "high" if strict else "medium",
                        "missing_payload_field",
                        f"payload.{field} is required by the runtime contract.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )

        if not isinstance(event_index, int) or event_index <= 0:
            findings.append(
                finding(
                    "high" if strict else "medium",
                    "invalid_event_index",
                    "event_index must be a positive integer.",
                    line=line,
                    step=step if isinstance(step, str) else None,
                )
            )
        elif previous_index is not None:
            if event_index <= previous_index:
                findings.append(
                    finding(
                        "high",
                        "nonmonotonic_event_index",
                        "event_index must increase monotonically.",
                        line=line,
                        event_index=event_index,
                        step=step if isinstance(step, str) else None,
                    )
                )
            elif event_index != previous_index + 1:
                findings.append(
                    finding(
                        "low",
                        "event_index_gap",
                        f"event_index jumps from {previous_index} to {event_index}.",
                        line=line,
                        event_index=event_index,
                        step=step if isinstance(step, str) else None,
                    )
                )
        if isinstance(event_index, int) and event_index > 0:
            previous_index = event_index

        if not isinstance(event.get("timestamp_utc"), str):
            findings.append(
                finding(
                    "high" if strict else "medium",
                    "missing_timestamp_utc",
                    "timestamp_utc must be present.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )

        timestamp_ms = event.get("timestamp_unix_ms")
        if not isinstance(timestamp_ms, int):
            findings.append(
                finding(
                    "high" if strict else "medium",
                    "missing_timestamp_unix_ms",
                    "timestamp_unix_ms must be an integer.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )
        elif previous_timestamp_ms is not None and timestamp_ms < previous_timestamp_ms:
            findings.append(
                finding(
                    "medium",
                    "timestamp_regression",
                    "timestamp_unix_ms moves backwards.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )
        if isinstance(timestamp_ms, int):
            previous_timestamp_ms = timestamp_ms

        if not isinstance(event.get("monotonic_ns"), int):
            findings.append(
                finding(
                    "high" if strict else "medium",
                    "missing_monotonic_ns",
                    "monotonic_ns must be an integer.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )

        if "elapsed_ms_since_log_start" not in event:
            findings.append(
                finding(
                    "low",
                    "missing_elapsed_since_start",
                    "elapsed_ms_since_log_start is absent; migrate this writer to the shared helper.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )
        if "elapsed_ms_since_prev_event" not in event:
            findings.append(
                finding(
                    "low",
                    "missing_elapsed_since_prev",
                    "elapsed_ms_since_prev_event is absent; migrate this writer to the shared helper.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )

        hook_id = payload.get("hook_id")
        agent_usage = payload.get("agent_usage")
        convergence_criteria = payload.get("convergence_criteria")
        if require_instrumentation:
            if not isinstance(agent_usage, dict):
                findings.append(
                    finding(
                        "high",
                        "missing_agent_usage",
                        "payload.agent_usage is required for instrumented logs.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
            else:
                for field in ("agent_or_skill", "step", "usage_site"):
                    if field not in agent_usage:
                        findings.append(
                            finding(
                                "high",
                                "invalid_agent_usage",
                                f"payload.agent_usage.{field} is required.",
                                line=line,
                                event_index=(
                                    event_index
                                    if isinstance(event_index, int)
                                    else None
                                ),
                                step=step if isinstance(step, str) else None,
                            )
                        )
            if not isinstance(convergence_criteria, dict):
                findings.append(
                    finding(
                        "high",
                        "missing_convergence_criteria",
                        "payload.convergence_criteria is required for instrumented logs.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
            else:
                for field in ("criteria", "current_evidence"):
                    if field not in convergence_criteria:
                        findings.append(
                            finding(
                                "high",
                                "invalid_convergence_criteria",
                                f"payload.convergence_criteria.{field} is required.",
                                line=line,
                                event_index=(
                                    event_index
                                    if isinstance(event_index, int)
                                    else None
                                ),
                                step=step if isinstance(step, str) else None,
                            )
                        )

        skill_application = payload.get("skill_application")
        step_is_skill_application = (
            isinstance(step, str) and step in GENERIC_SKILL_APPLICATION_STEPS
        )
        if require_skill_application or step_is_skill_application:
            if not isinstance(skill_application, dict):
                findings.append(
                    finding(
                        "high",
                        "missing_skill_application",
                        "payload.skill_application is required for skill-application logs.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
                skill_application = {}
            for field in sorted(SKILL_APPLICATION_REQUIRED_FIELDS):
                value = skill_application.get(field)
                if field not in skill_application or (
                    field in SKILL_APPLICATION_NONEMPTY_FIELDS and value in (None, "")
                ):
                    findings.append(
                        finding(
                            "high",
                            "invalid_skill_application",
                            f"payload.skill_application.{field} is required.",
                            line=line,
                            event_index=(
                                event_index if isinstance(event_index, int) else None
                            ),
                            step=step if isinstance(step, str) else None,
                        )
                    )
            status = skill_application.get("status")
            if (
                status in {"error", "blocked"} or step == "skill_application_error"
            ) and not skill_application.get("next_action"):
                findings.append(
                    finding(
                        "high",
                        "missing_blocker_next_action",
                        "error or blocked skill applications must include next_action.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
            for field in ("inputs", "artifacts", "evidence", "decision", "risks"):
                if field in skill_application and not isinstance(
                    skill_application[field], dict
                ):
                    findings.append(
                        finding(
                            "high",
                            "invalid_skill_application_section",
                            f"payload.skill_application.{field} must be an object.",
                            line=line,
                            event_index=(
                                event_index if isinstance(event_index, int) else None
                            ),
                            step=step if isinstance(step, str) else None,
                        )
                    )

        if hook_id:
            if not isinstance(hook_id, str):
                findings.append(
                    finding(
                        "high",
                        "invalid_hook_id",
                        "payload.hook_id must be a string.",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
            elif known_hooks and hook_id not in known_hooks:
                findings.append(
                    finding(
                        "high",
                        "unknown_hook_id",
                        f"payload.hook_id is not registered: {hook_id}",
                        line=line,
                        event_index=(
                            event_index if isinstance(event_index, int) else None
                        ),
                        step=step if isinstance(step, str) else None,
                    )
                )
            elif isinstance(step, str) and hook_steps.get(hook_id):
                if step not in hook_steps[hook_id]:
                    if step not in GENERIC_SKILL_APPLICATION_STEPS:
                        findings.append(
                            finding(
                                "medium",
                                "undeclared_hook_step",
                                f"Step is not listed under hook {hook_id}.",
                                line=line,
                                event_index=(
                                    event_index
                                    if isinstance(event_index, int)
                                    else None
                                ),
                                step=step,
                            )
                        )

        if not isinstance(event.get("statement_hash"), (str, type(None))):
            findings.append(
                finding(
                    "low",
                    "invalid_statement_hash",
                    "statement_hash should be a string or null.",
                    line=line,
                    event_index=event_index if isinstance(event_index, int) else None,
                    step=step if isinstance(step, str) else None,
                )
            )

        if ordinal == len(entries) and not entries:
            break

    return findings


def summarize(findings: Sequence[Dict[str, Any]], event_count: int) -> Dict[str, Any]:
    """Document the responsibility of ``summarize``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``summarize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    blocking = counts.get("high", 0)
    return {
        "event_count": event_count,
        "finding_count": len(findings),
        "severity_counts": counts,
        "blocking_findings": blocking,
    }


def validate_reasoning_log(
    log_file: Path,
    *,
    hooks_file: Optional[Path],
    strict: bool = False,
    require_instrumentation: bool = False,
    require_skill_application: bool = False,
) -> Dict[str, Any]:
    """Document the responsibility of ``validate_reasoning_log``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hook_contract = parse_hook_contract(hooks_file)
    entries, parse_findings = load_entries(log_file)
    schema_findings = validate_entries(
        entries,
        known_hooks=hook_contract["known_hooks"],
        hook_steps=hook_contract["hook_steps"],
        required_payload_fields=hook_contract["required_payload_fields"],
        strict=strict,
        require_instrumentation=require_instrumentation,
        require_skill_application=require_skill_application,
    )
    findings = parse_findings + schema_findings
    summary = summarize(findings, len(entries))
    ok = summary["blocking_findings"] == 0
    return {
        "ok": ok,
        "strict": strict,
        "require_instrumentation": require_instrumentation,
        "require_skill_application": require_skill_application,
        "log_file": str(log_file),
        "hooks_file": None if hooks_file is None else str(hooks_file),
        "summary": summary,
        "findings": findings,
    }


def render_text(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary = report["summary"]
    lines = [
        f"ok: {report['ok']}",
        f"events: {summary['event_count']}",
        f"findings: {summary['finding_count']}",
        f"blocking: {summary['blocking_findings']}",
    ]
    for item in report["findings"][:50]:
        loc = f"line {item.get('line')}" if item.get("line") is not None else "log"
        step = f" step={item['step']}" if item.get("step") else ""
        lines.append(
            f"- {item['severity']} {item['code']} ({loc}{step}): {item['message']}"
        )
    if len(report["findings"]) > 50:
        lines.append(f"... {len(report['findings']) - 50} more findings")
    return "\n".join(lines)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Document the responsibility of ``parse_args``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, required=True)
    parser.add_argument(
        "--hooks-file", type=Path, default=Path("skills/SKILL_HOOKS.yaml")
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--require-instrumentation", action="store_true")
    parser.add_argument("--require-skill-application", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    args = parse_args(argv)
    report = validate_reasoning_log(
        args.log_file,
        hooks_file=args.hooks_file,
        strict=args.strict,
        require_instrumentation=args.require_instrumentation,
        require_skill_application=args.require_skill_application,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 3 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())

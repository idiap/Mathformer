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

"""Shared helpers for Mathformer reasoning-log JSONL events."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

_EVENT_COUNTERS: Dict[str, int] = {}
_FIRST_MONO_NS: Dict[str, int] = {}
_LAST_MONO_NS: Dict[str, int] = {}
_HOOK_CONTRACT_CACHE: Optional[Dict[str, Dict[str, str]]] = None


SKILL_APPLICATION_STEPS = (
    "skill_application_start",
    "skill_application_context_loaded",
    "skill_application_input_normalized",
    "skill_application_action_taken",
    "skill_application_evidence_recorded",
    "skill_application_gate_evaluated",
    "skill_application_complete",
    "skill_application_error",
)


def jsonable(value: Any) -> Any:
    """Convert common Python objects to JSON-serializable values."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return repr(value)


def statement_hash(statement: str, *, length: int = 12) -> str:
    """Document the responsibility of ``statement_hash``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``statement_hash`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()[:length]


def _default_hooks_file() -> Path:
    """Document the responsibility of ``_default_hooks_file``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_default_hooks_file`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return Path(__file__).resolve().parents[4] / "skills" / "SKILL_HOOKS.yaml"


def _load_hook_contract() -> Dict[str, Dict[str, str]]:
    """Load minimal hook metadata used for automatic usage instrumentation."""
    global _HOOK_CONTRACT_CACHE
    if _HOOK_CONTRACT_CACHE is not None:
        return _HOOK_CONTRACT_CACHE

    hooks_file = _default_hooks_file()
    hooks: Dict[str, Dict[str, str]] = {}
    if not hooks_file.exists():
        _HOOK_CONTRACT_CACHE = hooks
        return hooks

    current_hook: Optional[str] = None
    in_hooks = False
    for raw_line in hooks_file.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "hooks:":
            in_hooks = True
            current_hook = None
            continue
        if stripped in {"loop_contracts:", "direct_request_routing:"}:
            in_hooks = False
            current_hook = None
            continue
        if not in_hooks:
            continue
        if stripped.startswith("- id: "):
            current_hook = stripped.removeprefix("- id: ").strip()
            hooks[current_hook] = {}
            continue
        if current_hook is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key in {"phase", "trigger", "owner_skill", "gate"}:
            hooks[current_hook][key] = value.strip().strip('"')

    _HOOK_CONTRACT_CACHE = hooks
    return hooks


def _infer_convergence_evidence(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``_infer_convergence_evidence``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_infer_convergence_evidence`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    keys = (
        "ok",
        "status",
        "passed",
        "judgement",
        "target_met",
        "compatibility_target_met",
        "consistency_target_met",
        "final_correctness",
        "correctness",
        "blocking_findings",
        "blocking_finding_count",
        "finding_count",
        "score",
        "compatibility_score",
        "reference_free_confidence_score",
        "target_verified_ratio",
        "verified_ratio",
        "max_rounds",
        "round_index",
    )
    return {key: payload[key] for key in keys if key in payload}


def _object_section(value: Any) -> Dict[str, Any]:
    """Return a machine-processable object section for consumer log payloads."""
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value:
        return {"items": value}
    if value not in (None, "", [], ()):
        return {"value": value}
    return {}


def _compact_text(value: Any, *, limit: int) -> str:
    """Compact free text for consumer-facing log summaries."""
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _default_human_summary(skill: str, step: str, payload: Dict[str, Any]) -> str:
    """Build a concise human summary for generated skill-application metadata."""
    stage = payload.get("stage") or step
    status = payload.get("status") or _object_section(payload.get("decision")).get(
        "status"
    )
    if status:
        return _compact_text(f"{skill} reported {status} for {stage}.", limit=320)
    return _compact_text(f"{skill} recorded {stage}.", limit=320)


def instrument_reasoning_payload(
    *,
    step: str,
    payload: Dict[str, Any],
    statement_hash_value: Optional[str],
    file_prefix: Optional[str],
    dependency_label: Optional[str],
) -> Dict[str, Any]:
    """Attach where-used and convergence-criteria metadata to a payload."""
    enriched = dict(payload)
    hook_id = enriched.get("hook_id")
    hook_meta = (
        _load_hook_contract().get(hook_id, {}) if isinstance(hook_id, str) else {}
    )
    skill = enriched.get("skill")
    agent_usage = enriched.get("agent_usage")
    if not isinstance(agent_usage, dict):
        enriched["agent_usage"] = {
            "agent_or_skill": skill,
            "step": step,
            "hook_id": hook_id,
            "hook_phase": hook_meta.get("phase"),
            "hook_owner_skill": hook_meta.get("owner_skill"),
            "trigger": hook_meta.get("trigger"),
            "usage_site": {
                "file_prefix": file_prefix,
                "dependency_label": dependency_label,
                "statement_hash": statement_hash_value,
            },
        }

    if isinstance(skill, str) and not isinstance(
        enriched.get("skill_application"), dict
    ):
        inputs = {
            key: value
            for key, value in {
                "case_id": enriched.get("case_id"),
                "stage": enriched.get("stage"),
                "mode": enriched.get("mode"),
                "statement_hash": statement_hash_value,
                "file_prefix": file_prefix,
                "dependency_label": dependency_label,
            }.items()
            if value is not None
        }
        intent = enriched.get("intent") or hook_meta.get("trigger") or f"Record {step}."
        generated = build_skill_application_payload(
            skill=skill,
            hook_id=hook_id if isinstance(hook_id, str) else None,
            skill_call_id=(
                enriched.get("skill_call_id")
                if isinstance(enriched.get("skill_call_id"), str)
                else None
            ),
            run_id=(
                enriched.get("run_id")
                if isinstance(enriched.get("run_id"), str)
                else None
            ),
            intent=_compact_text(intent, limit=180),
            inputs=inputs,
            artifacts=_object_section(enriched.get("artifacts")),
            evidence=_object_section(enriched.get("evidence")),
            decision=_object_section(enriched.get("decision")),
            risks=_object_section(enriched.get("risks")),
            next_action=str(enriched.get("next_action") or ""),
            human_summary=_compact_text(
                enriched.get("human_summary")
                or _default_human_summary(skill, step, enriched),
                limit=320,
            ),
            status=str(
                enriched.get("status")
                or _object_section(enriched.get("decision")).get("status")
                or "complete"
            ),
        )
        enriched["skill_call_id"] = generated["skill_call_id"]
        enriched["skill_application"] = generated["skill_application"]

    criteria = enriched.get("convergence_criteria")
    if not isinstance(criteria, dict):
        hook_gate = hook_meta.get("gate")
        fallback = (
            "event-specific evidence decides convergence; inspect current_evidence"
        )
        enriched["convergence_criteria"] = {
            "source": "hook_contract" if hook_gate else "payload_inference",
            "criteria": hook_gate or fallback,
            "current_evidence": _infer_convergence_evidence(enriched),
        }
    return enriched


def make_skill_call_id(skill: str, *, prefix: str = "skill") -> str:
    """Return a short unique identifier for one skill invocation."""
    safe_skill = "".join(
        ch if ch.isalnum() else "-" for ch in skill.strip().lower()
    ).strip("-")
    safe_skill = safe_skill or "unknown-skill"
    return f"{prefix}-{safe_skill}-{uuid4().hex[:12]}"


def build_skill_application_payload(
    *,
    skill: str,
    hook_id: Optional[str] = None,
    skill_call_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    run_id: Optional[str] = None,
    intent: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    risks: Optional[Dict[str, Any]] = None,
    next_action: str = "",
    human_summary: str = "",
    status: str = "running",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the canonical self-explaining skill-application payload."""
    resolved_call_id = skill_call_id or make_skill_call_id(skill)
    payload: Dict[str, Any] = {
        "skill": skill,
        "hook_id": hook_id,
        "run_id": run_id,
        "skill_call_id": resolved_call_id,
        "parent_call_id": parent_call_id,
        "skill_application": {
            "schema_version": 1,
            "skill": skill,
            "hook_id": hook_id,
            "run_id": run_id,
            "skill_call_id": resolved_call_id,
            "parent_call_id": parent_call_id,
            "status": status,
            "intent": intent,
            "inputs": inputs or {},
            "artifacts": artifacts or {},
            "evidence": evidence or {},
            "decision": decision or {},
            "risks": risks or {},
            "next_action": next_action,
            "human_summary": human_summary,
        },
    }
    if extra:
        payload.update(extra)
    return payload


def append_skill_start(
    output_file: str | os.PathLike[str],
    *,
    skill: str,
    hook_id: Optional[str] = None,
    skill_call_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    run_id: Optional[str] = None,
    intent: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    risks: Optional[Dict[str, Any]] = None,
    human_summary: str = "",
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> str:
    """Append the start event for one self-explaining skill invocation."""
    resolved_call_id = skill_call_id or make_skill_call_id(skill)
    append_reasoning_log_entry(
        output_file,
        step="skill_application_start",
        payload=build_skill_application_payload(
            skill=skill,
            hook_id=hook_id,
            skill_call_id=resolved_call_id,
            parent_call_id=parent_call_id,
            run_id=run_id,
            intent=intent,
            inputs=inputs,
            artifacts=artifacts,
            risks=risks,
            human_summary=human_summary or f"{skill} started.",
            status="running",
        ),
        statement=statement,
        file_prefix=file_prefix,
        dependency_label=dependency_label,
    )
    return resolved_call_id


def append_skill_progress(
    output_file: str | os.PathLike[str],
    *,
    phase: str,
    skill: str,
    skill_call_id: str,
    hook_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    run_id: Optional[str] = None,
    intent: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    risks: Optional[Dict[str, Any]] = None,
    next_action: str = "",
    human_summary: str = "",
    status: str = "running",
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> None:
    """Append an intermediate event in the skill-application lifecycle."""
    normalized_phase = phase.strip().lower()
    if not normalized_phase.startswith("skill_application_"):
        normalized_phase = f"skill_application_{normalized_phase}"
    if normalized_phase not in SKILL_APPLICATION_STEPS:
        normalized_phase = "skill_application_action_taken"
    append_reasoning_log_entry(
        output_file,
        step=normalized_phase,
        payload=build_skill_application_payload(
            skill=skill,
            hook_id=hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=parent_call_id,
            run_id=run_id,
            intent=intent,
            inputs=inputs,
            artifacts=artifacts,
            evidence=evidence,
            decision=decision,
            risks=risks,
            next_action=next_action,
            human_summary=human_summary or f"{skill} recorded {normalized_phase}.",
            status=status,
        ),
        statement=statement,
        file_prefix=file_prefix,
        dependency_label=dependency_label,
    )


def append_skill_complete(
    output_file: str | os.PathLike[str],
    *,
    skill: str,
    skill_call_id: str,
    hook_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    run_id: Optional[str] = None,
    intent: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    decision: Optional[Dict[str, Any]] = None,
    risks: Optional[Dict[str, Any]] = None,
    next_action: str = "",
    human_summary: str = "",
    status: str = "complete",
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> None:
    """Append the successful terminal event for one skill invocation."""
    append_reasoning_log_entry(
        output_file,
        step="skill_application_complete",
        payload=build_skill_application_payload(
            skill=skill,
            hook_id=hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=parent_call_id,
            run_id=run_id,
            intent=intent,
            inputs=inputs,
            artifacts=artifacts,
            evidence=evidence,
            decision=decision,
            risks=risks,
            next_action=next_action,
            human_summary=human_summary or f"{skill} completed.",
            status=status,
        ),
        statement=statement,
        file_prefix=file_prefix,
        dependency_label=dependency_label,
    )


def append_skill_error(
    output_file: str | os.PathLike[str],
    *,
    skill: str,
    skill_call_id: str,
    error: str,
    hook_id: Optional[str] = None,
    parent_call_id: Optional[str] = None,
    run_id: Optional[str] = None,
    intent: str = "",
    inputs: Optional[Dict[str, Any]] = None,
    artifacts: Optional[Dict[str, Any]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    risks: Optional[Dict[str, Any]] = None,
    next_action: str = "",
    human_summary: str = "",
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> None:
    """Append the terminal error event for one skill invocation."""
    append_reasoning_log_entry(
        output_file,
        step="skill_application_error",
        payload=build_skill_application_payload(
            skill=skill,
            hook_id=hook_id,
            skill_call_id=skill_call_id,
            parent_call_id=parent_call_id,
            run_id=run_id,
            intent=intent,
            inputs=inputs,
            artifacts=artifacts,
            evidence=evidence or {"error": error},
            decision={"status": "error", "error": error},
            risks=risks or {"blocker": error},
            next_action=next_action,
            human_summary=human_summary or f"{skill} stopped: {error}",
            status="error",
        ),
        statement=statement,
        file_prefix=file_prefix,
        dependency_label=dependency_label,
    )


def _seed_log_state(path: Path) -> tuple[int, Optional[int], Optional[int]]:
    """Document the responsibility of ``_seed_log_state``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``_seed_log_state`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not path.exists():
        return 0, None, None

    last_index = 0
    first_mono: Optional[int] = None
    last_mono: Optional[int] = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue

        event_index = parsed.get("event_index")
        if isinstance(event_index, int):
            last_index = max(last_index, event_index)

        mono_ns = parsed.get("monotonic_ns")
        if isinstance(mono_ns, int):
            if first_mono is None:
                first_mono = mono_ns
            last_mono = mono_ns

    return last_index, first_mono, last_mono


def append_reasoning_log_entry(
    output_file: str | os.PathLike[str],
    *,
    step: str,
    payload: Dict[str, Any],
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> Path:
    """Append one canonical structured event to a reasoning log JSONL file."""
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    log_key = str(path.resolve())

    if log_key not in _EVENT_COUNTERS:
        seed_index, seed_first_mono, seed_last_mono = _seed_log_state(path)
        _EVENT_COUNTERS[log_key] = seed_index
        if seed_first_mono is not None:
            _FIRST_MONO_NS[log_key] = seed_first_mono
        if seed_last_mono is not None:
            _LAST_MONO_NS[log_key] = seed_last_mono
    else:
        seed_index, seed_first_mono, seed_last_mono = _seed_log_state(path)
        if seed_index > _EVENT_COUNTERS[log_key]:
            _EVENT_COUNTERS[log_key] = seed_index
            if seed_first_mono is not None:
                _FIRST_MONO_NS.setdefault(log_key, seed_first_mono)
            if seed_last_mono is not None:
                _LAST_MONO_NS[log_key] = seed_last_mono

    now_utc = datetime.now(timezone.utc)
    mono_ns = time.perf_counter_ns()
    _EVENT_COUNTERS[log_key] += 1

    first_mono_ns = _FIRST_MONO_NS.setdefault(log_key, mono_ns)
    last_mono_ns = _LAST_MONO_NS.get(log_key)
    elapsed_since_start = (mono_ns - first_mono_ns) / 1_000_000
    elapsed_since_prev = (
        None if last_mono_ns is None else (mono_ns - last_mono_ns) / 1_000_000
    )
    _LAST_MONO_NS[log_key] = mono_ns

    entry: Dict[str, Any] = {
        "event_index": _EVENT_COUNTERS[log_key],
        "timestamp_utc": now_utc.isoformat(),
        "timestamp_unix_ms": int(now_utc.timestamp() * 1000),
        "monotonic_ns": mono_ns,
        "elapsed_ms_since_log_start": round(elapsed_since_start, 3),
        "elapsed_ms_since_prev_event": (
            None if elapsed_since_prev is None else round(elapsed_since_prev, 3)
        ),
        "statement_hash": None if statement is None else statement_hash(statement),
        "file_prefix": file_prefix,
        "dependency_label": dependency_label,
        "step": step,
        "payload": jsonable(
            instrument_reasoning_payload(
                step=step,
                payload=payload,
                statement_hash_value=(
                    None if statement is None else statement_hash(statement)
                ),
                file_prefix=file_prefix,
                dependency_label=dependency_label,
            )
        ),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def make_reasoning_logger(
    output_file: str | os.PathLike[str] | None,
    *,
    statement: Optional[str] = None,
    file_prefix: Optional[str] = None,
    dependency_label: Optional[str] = None,
) -> Callable[[str, Dict[str, Any]], None]:
    """Document the responsibility of ``make_reasoning_logger``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """

    def trace_event(step: str, payload: Dict[str, Any]) -> None:
        """Document the responsibility of ``make_reasoning_logger.trace_event``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Build the local data structure or artifact used by the next workflow stage.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        if output_file is None:
            return
        append_reasoning_log_entry(
            output_file,
            step=step,
            payload=payload,
            statement=statement,
            file_prefix=file_prefix,
            dependency_label=dependency_label,
        )

    return trace_event


def reset_reasoning_log_state(output_file: str | os.PathLike[str]) -> None:
    """Document the responsibility of ``reset_reasoning_log_state``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``reset_reasoning_log_state`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    key = str(Path(output_file).resolve())
    _EVENT_COUNTERS.pop(key, None)
    _FIRST_MONO_NS.pop(key, None)
    _LAST_MONO_NS.pop(key, None)

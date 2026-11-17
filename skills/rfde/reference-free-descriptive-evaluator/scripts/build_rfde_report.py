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

"""Build Reference-Free Descriptive Evaluation reports for agentic runs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
REFERENCE_MONITOR_SCRIPTS = (
    REPO_ROOT / "skills" / "rfde" / "reference-free-critic-monitor" / "scripts"
)
for script_dir in (REASONING_LOG_SCRIPTS, REFERENCE_MONITOR_SCRIPTS):
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

try:
    from reasoning_log import append_reasoning_log_entry
except Exception:  # pragma: no cover - usable standalone
    append_reasoning_log_entry = None  # type: ignore[assignment]

try:
    from monitor_reference_free_critics import analyze_lean_text
except Exception:  # pragma: no cover - fallback below is enough for smoke tests
    analyze_lean_text = None  # type: ignore[assignment]


SKILL_NAME = "reference-free-descriptive-evaluator"
HOOK_ID = "evaluation.rfde_report"
SOURCE_ANCHOR_RE = re.compile(
    r"Source anchors?:\s*([A-Za-z0-9_:\-.,\s]+)", re.IGNORECASE
)
DECL_RE = re.compile(
    r"^\s*(?:private\s+|protected\s+|noncomputable\s+|unsafe\s+)*"
    r"(theorem|lemma|def|abbrev|class|structure|inductive|instance|axiom)\s+([^\s(:{]+)"
)
PLACEHOLDER_RE = re.compile(
    r"\b(sorry|admit|exact\?|axiom|mock|stub|placeholder)\b", re.IGNORECASE
)
UNCERTAINTY_RE = re.compile(
    r"\b(unknown|uncertain|assumption|assume|blocked|gap|waived|unresolved)\b",
    re.IGNORECASE,
)
SCORE_PATH_RE = re.compile(
    r"(ok|passed|target_met|score|coverage|ratio|confidence|grounding|"
    r"nonvacuity|realness|closure|fidelity|integrity|coherence|calibration|"
    r"compliance|evidence|consistency)",
    re.IGNORECASE,
)
RISK_PATH_RE = re.compile(
    r"(error|invalid|blocking|failure|regression|risk|orphan)", re.IGNORECASE
)
REQUIRED_TRAJECTORY_PHASES = {
    "intake",
    "preformalization",
    "drafting",
    "execution",
    "validation",
    "critique",
    "review",
    "consistency",
    "evaluation",
}
DETAILED_PHASE_BY_HOOK = {
    "intake.workflow_start": "intake",
    "physics.source.extract": "source_intake",
    "physics.informal.elicit": "informal_elicitation",
    "physics.informal.expand": "informal_expansion",
    "physics.informal.review": "preformalization_readiness",
    "physics.lean.workflow.plan": "lean_physics_planning",
    "physics.lean.type_system.build": "lean_physics_preformalization",
    "physics.lean.assumptions.encode": "lean_physics_preformalization",
    "draft.physics_lean_derivation": "drafting",
    "execute.physics_lean_interpret": "execution",
    "physics.lean.units.verify": "lean_physics_validation",
    "critique.physics_lean_semantics": "critique",
    "critique.physics_lean_assumptions": "critique",
    "critique.physics_lean_dimensions": "critique",
    "critique.physics_lean_generative_panel": "critique",
    "review.physics_final_hypotheses": "review",
    "review.mathematical_final_hypotheses": "review",
    "review.final_derivation_hypotheses": "review",
    "consistency.physics_lean_report": "consistency",
    "evaluation.rfde_report": "evaluation",
}
PHASE_FAMILIES = {
    "intake": "intake",
    "source_intake": "intake",
    "informal_elicitation": "preformalization",
    "informal_expansion": "preformalization",
    "preformalization": "preformalization",
    "preformalization_readiness": "preformalization",
    "lean_physics_planning": "preformalization",
    "lean_physics_preformalization": "preformalization",
    "mathlib_alignment": "preformalization",
    "grounding": "preformalization",
    "drafting": "drafting",
    "execution": "execution",
    "check": "validation",
    "lean_physics_validation": "validation",
    "testing": "validation",
    "critique": "critique",
    "review": "review",
    "consistency": "consistency",
    "postformalization": "consistency",
    "artifacts": "consistency",
    "evaluation": "evaluation",
    "reflection": "evaluation",
}
PROTECTED_METRIC_TERMS = (
    "anchor",
    "source",
    "semantic",
    "executability",
    "compile",
    "realness",
    "nonvacuity",
    "consistency",
    "proof",
)


def rel(path: Path) -> str:
    """Document the responsibility of ``rel``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``rel`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def utc_now() -> str:
    """Document the responsibility of ``utc_now``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``utc_now`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return datetime.now(timezone.utc).isoformat()


def clamp01(value: float) -> float:
    """Document the responsibility of ``clamp01``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``clamp01`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return round(max(0.0, min(1.0, value)), 4)


def score_from_100(value: Any, default: float = 0.0) -> float:
    """Document the responsibility of ``score_from_100``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``score_from_100`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, (int, float)):
        return clamp01(float(value) / 100.0)
    return default


def load_json(path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Document the responsibility of ``load_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if path is None:
        return None
    resolved = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
    if not resolved.exists():
        return None
    parsed = json.loads(resolved.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else None


def load_json_list(paths: Sequence[Path]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``load_json_list``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    values: List[Dict[str, Any]] = []
    for path in paths:
        loaded = load_json(path)
        if loaded is not None:
            loaded["_source_file"] = rel(
                (REPO_ROOT / path).resolve() if not path.is_absolute() else path
            )
            values.append(loaded)
    return values


def read_text(path: Path) -> str:
    """Document the responsibility of ``read_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    resolved = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
    return resolved.read_text(encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    """Document the responsibility of ``write_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append_event(
    reasoning_log: Optional[Path], step: str, payload: Dict[str, Any]
) -> None:
    """Document the responsibility of ``append_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``append_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if reasoning_log is None or append_reasoning_log_entry is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def flatten_numbers(value: Any, wanted: set[str]) -> Counter:
    """Document the responsibility of ``flatten_numbers``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``flatten_numbers`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    counts: Any = Counter()  # Numeric counters include fractional weights.
    if isinstance(value, dict):
        for key, item in value.items():
            if key in wanted and isinstance(item, (int, float)):
                counts[key] += item
            counts.update(flatten_numbers(item, wanted))
    elif isinstance(value, list):
        for item in value:
            counts.update(flatten_numbers(item, wanted))
    return counts


def iter_leaf_values(value: Any, prefix: str = "") -> Iterable[Tuple[str, Any]]:
    """Document the responsibility of ``iter_leaf_values``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``iter_leaf_values`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from iter_leaf_values(item, path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}.{index}" if prefix else str(index)
            yield from iter_leaf_values(item, path)
    else:
        yield prefix, value


def normalize_measure(path: str, value: Any) -> Optional[float]:
    """Document the responsibility of ``normalize_measure``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_measure`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lowered = path.lower()
    if isinstance(value, bool) and SCORE_PATH_RE.search(lowered):
        return 1.0 if value else 0.0
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    numeric = float(value)
    if RISK_PATH_RE.search(lowered):
        return clamp01(1.0 - min(1.0, max(0.0, numeric) / 10.0))
    if SCORE_PATH_RE.search(lowered):
        if numeric > 1.0 and numeric <= 100.0:
            return clamp01(numeric / 100.0)
        return clamp01(numeric)
    return None


def extract_event_measurements(
    payload: Dict[str, Any], *, limit: int = 80
) -> Dict[str, float]:
    """Document the responsibility of ``extract_event_measurements``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_event_measurements`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    measurements: Dict[str, float] = {}
    for path, value in iter_leaf_values(payload):
        normalized = normalize_measure(path, value)
        if normalized is None:
            continue
        clean_path = re.sub(r"[^A-Za-z0-9_.-]+", "_", path).strip("_")
        if clean_path:
            measurements[clean_path] = normalized
        if len(measurements) >= limit:
            break
    return measurements


def phase_from_event(event: Dict[str, Any]) -> str:
    """Document the responsibility of ``phase_from_event``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_from_event`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hook = str(event.get("hook_id") or "")
    step = str(event.get("step") or "").lower()
    if hook in DETAILED_PHASE_BY_HOOK:
        return DETAILED_PHASE_BY_HOOK[hook]
    if "." in hook:
        phase = hook.split(".", 1)[0]
    elif hook:
        phase = hook
    elif (
        "unit" in step or "dimension" in step or "validate" in step or "verify" in step
    ):
        phase = "lean_physics_validation"
    elif "compile" in step or "execute" in step:
        phase = "execution"
    elif "critique" in step or "critic" in step:
        phase = "critique"
    elif "consistency" in step:
        phase = "consistency"
    elif "draft" in step or "generate" in step:
        phase = "drafting"
    else:
        phase = "unknown"
    return {
        "draft": "drafting",
        "execute": "execution",
        "check": "execution",
        "artifact": "artifacts",
        "test": "testing",
    }.get(phase, phase)


def phase_family(phase: str) -> str:
    """Document the responsibility of ``phase_family``.

    Motivation:
        Make detailed autoformalization timelines comparable across mathematical and physics runs.

    Intent:
        Map specialized phases, such as Lean-physics preformalization or source intake, to the
        canonical phase families used for scoring, coverage, and transition interpretation.

    Inputs:
        A phase label emitted by ``phase_from_event`` or read from a trajectory action.

    Outputs:
        A canonical phase-family label, falling back to the original phase when no family is known.
    """
    return PHASE_FAMILIES.get(str(phase), str(phase))


def classify_action(event: Dict[str, Any]) -> str:
    """Document the responsibility of ``classify_action``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_action`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = " ".join(
        str(event.get(key) or "") for key in ("step", "hook_id", "skill")
    ).lower()
    phase = phase_from_event(event)
    family = phase_family(phase)
    if "rfde" in text or phase == "evaluation":
        return "evaluation"
    if "test" in text or family == "validation":
        return "testing"
    if "document" in text or "docs" in text or phase in {"library", "mathformerlib"}:
        return "documentation"
    if "reflect" in text or phase == "reflection":
        return "reflection"
    if family in {"intake", "preformalization"}:
        return "extraction"
    if (
        "generation" in text
        or "generate" in text
        or "draft" in text
        or phase == "drafting"
    ):
        return "generation"
    if (
        "refine" in text
        or "repair" in text
        or "denoise" in text
        or "minimiz" in text
        or "maximiz" in text
    ):
        return "repair"
    if (
        "critique" in text
        or "critic" in text
        or "judge" in text
        or "monitor" in text
        or family in {"critique", "review"}
    ):
        return "critique"
    if (
        "consistency" in text
        or "realness" in text
        or "nonvacuity" in text
        or "anchor_drift" in text
        or "verify" in text
        or family == "consistency"
        or phase == "audit"
    ):
        return "deterministic_gate"
    if (
        "compile" in text
        or "lean" in text
        or "execute" in text
        or family == "execution"
    ):
        return "execution_check"
    if (
        "extract" in text
        or "inventory" in text
        or "localize" in text
        or "organize" in text
    ):
        return "extraction"
    if "workflow_start" in text or phase == "intake":
        return "intake"
    if phase == "control":
        return "control"
    return "observation"


def classify_source_type(event: Dict[str, Any], action_kind: str) -> str:
    """Document the responsibility of ``classify_source_type``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_source_type`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    has_generation_evidence = any(
        key in payload
        for key in ("raw_response", "formal_code", "completion_tokens", "output_tokens")
    )
    if has_generation_evidence or action_kind == "generation":
        return "generative"
    if action_kind == "repair" and has_generation_evidence:
        return "mixed"
    return "deterministic"


def payload_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``payload_summary``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary: Dict[str, Any] = {}
    for key in (
        "id",
        "ok",
        "passed",
        "target_met",
        "status",
        "final_status",
        "duration_ms",
        "finding_count",
        "blocking_finding_count",
        "score_candidates",
        "agent_usage",
        "convergence_criteria",
        "summary",
        "scores",
        "risk_counts",
    ):
        if key in payload:
            summary[key] = payload[key]
    return summary


def load_reasoning_logs(
    paths: Sequence[Path],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Document the responsibility of ``load_reasoning_logs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    events: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    for path in paths:
        resolved = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
        if not resolved.exists():
            findings.append(
                {"severity": "high", "kind": "missing_reasoning_log", "path": str(path)}
            )
            continue
        for line_no, raw in enumerate(
            resolved.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                findings.append(
                    {
                        "severity": "high",
                        "kind": "invalid_reasoning_event",
                        "path": rel(resolved),
                        "line": line_no,
                        "message": exc.msg,
                    }
                )
                continue
            if isinstance(event, dict):
                event["_source_file"] = rel(resolved)
                events.append(event)
    return events, findings


def fallback_lean_stats(text: str, name: str) -> Dict[str, Any]:
    """Document the responsibility of ``fallback_lean_stats``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``fallback_lean_stats`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    declarations = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        match = DECL_RE.match(raw)
        if match is not None:
            declarations.append(
                {"kind": match.group(1), "name": match.group(2), "line": line_no}
            )
    kind_counts = Counter(item["kind"] for item in declarations)
    placeholder_count = len(PLACEHOLDER_RE.findall(text))
    semantic_comment_count = len(
        re.findall(
            r"Original source|Generated note|Generated equivalent|Source anchors", text
        )
    )
    return {
        "name": name,
        "line_count": len(text.splitlines()),
        "import_count": len(re.findall(r"^\s*import\s+", text, re.MULTILINE)),
        "broad_mathlib_import_count": len(
            re.findall(r"^\s*import\s+Mathlib\s*$", text, re.MULTILINE)
        ),
        "narrow_mathlib_import_count": len(
            re.findall(r"^\s*import\s+Mathlib\.", text, re.MULTILINE)
        ),
        "declaration_count": len(declarations),
        "declaration_kind_counts": dict(kind_counts),
        "theorem_like_count": kind_counts.get("theorem", 0)
        + kind_counts.get("lemma", 0),
        "axiom_count": kind_counts.get("axiom", 0),
        "placeholder_counts": {"placeholder_like": placeholder_count},
        "semantic_comment_count": semantic_comment_count,
        "original_source_comment_count": len(re.findall(r"Original source", text)),
        "semantic_comment_to_decl_ratio": semantic_comment_count
        / max(1, len(declarations)),
        "original_source_to_theorem_ratio": len(re.findall(r"Original source", text))
        / max(1, kind_counts.get("theorem", 0) + kind_counts.get("lemma", 0)),
        "mathlib_native_token_count": len(
            re.findall(
                r"\b(Set|Nat|Int|Real|Finset|Function|Surjective|Countable)\b", text
            )
        ),
        "trivial_statement_count": len(re.findall(r":\s*True\b", text)),
        "false_assumption_count": len(re.findall(r"\(\s*[^:]+:\s*False\s*\)", text)),
        "avg_theorem_signature_chars": 0.0,
    }


def lean_line_counts(text: str) -> Dict[str, int]:
    """Separate formal Lean lines from blank and source-comment lines."""
    formal_code_line_count = 0
    comment_line_count = 0
    blank_line_count = 0
    in_block_comment = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            blank_line_count += 1
            continue
        if in_block_comment:
            comment_line_count += 1
            if "-/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/--") or stripped.startswith("/-"):
            comment_line_count += 1
            if "-/" not in stripped:
                in_block_comment = True
            continue
        if stripped.startswith("--"):
            comment_line_count += 1
            continue
        formal_code_line_count += 1
    return {
        "formal_code_line_count": formal_code_line_count,
        "comment_line_count": comment_line_count,
        "blank_line_count": blank_line_count,
    }


def analyze_lean_files(
    paths: Sequence[Path],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Document the responsibility of ``analyze_lean_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``analyze_lean_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stats: List[Dict[str, Any]] = []
    claims: List[Dict[str, Any]] = []
    for path in paths:
        resolved = (REPO_ROOT / path).resolve() if not path.is_absolute() else path
        text = resolved.read_text(encoding="utf-8")
        item = (
            analyze_lean_text(text=text, name=rel(resolved))
            if analyze_lean_text is not None
            else fallback_lean_stats(text, rel(resolved))
        )
        imports = re.findall(r"^\s*import\s+([A-Za-z0-9_.'/-]+)", text, re.MULTILINE)
        item.update(lean_line_counts(text))
        item["imports"] = imports
        item["mathlib_imports"] = [
            name for name in imports if name == "Mathlib" or name.startswith("Mathlib.")
        ]
        item["previous_library_imports"] = [
            name
            for name in imports
            if name.startswith("Mathformer.") or name.startswith("MathformerLib.")
        ]
        item["external_library_imports"] = [
            name
            for name in imports
            if not (
                name == "Mathlib"
                or name.startswith("Mathlib.")
                or name.startswith("Mathformer.")
                or name.startswith("MathformerLib.")
            )
        ]
        item["path"] = rel(resolved)
        stats.append(item)
        claims.extend(extract_lean_claims(text, rel(resolved)))
    return stats, claims


def extract_lean_claims(text: str, source: str) -> List[Dict[str, Any]]:
    """Document the responsibility of ``extract_lean_claims``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_lean_claims`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    claims: List[Dict[str, Any]] = []
    pending_comment = ""
    in_comment = False
    comment_lines: List[str] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if in_comment:
            comment_lines.append(stripped)
            if "-/" in stripped:
                pending_comment = "\n".join(comment_lines)
                in_comment = False
                comment_lines = []
            continue
        if stripped.startswith("/--"):
            comment_lines = [stripped]
            if "-/" in stripped:
                pending_comment = "\n".join(comment_lines)
                comment_lines = []
            else:
                in_comment = True
            continue
        match = DECL_RE.match(raw)
        if match is None:
            continue
        kind, name = match.groups()
        support = [{"type": "lean_declaration", "source": source, "line": line_no}]
        anchor_match = SOURCE_ANCHOR_RE.search(pending_comment)
        if anchor_match is not None:
            support.append(
                {"type": "source_anchor", "anchors": anchor_match.group(1).strip()}
            )
        if "Original source" in pending_comment:
            support.append({"type": "source_comment"})
        claims.append(
            {
                "claim_id": f"claim_{len(claims)+1:04d}",
                "text": raw.strip(),
                "type": (
                    "formal_claim" if kind in {"theorem", "lemma"} else "formal_object"
                ),
                "support": support,
                "confidence": (
                    "verified_by_lean_context" if kind != "axiom" else "assumed"
                ),
                "importance": 0.9 if kind in {"theorem", "lemma"} else 0.6,
                "source": source,
                "line": line_no,
            }
        )
        pending_comment = ""
    return claims


def aggregate_lean_stats(stats: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Document the responsibility of ``aggregate_lean_stats``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``aggregate_lean_stats`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    total: Any = Counter()  # Aggregate includes nested placeholder metrics.
    placeholders = Counter()
    for item in stats:
        for key in (
            "line_count",
            "formal_code_line_count",
            "comment_line_count",
            "blank_line_count",
            "import_count",
            "broad_mathlib_import_count",
            "narrow_mathlib_import_count",
            "declaration_count",
            "theorem_like_count",
            "axiom_count",
            "semantic_comment_count",
            "original_source_comment_count",
            "mathlib_native_token_count",
            "trivial_statement_count",
            "false_assumption_count",
        ):
            total[key] += item.get(key, 0) or 0
        placeholders.update(item.get("placeholder_counts", {}))
    total["mathlib_import_count"] = sum(
        len(item.get("mathlib_imports", [])) for item in stats
    )
    total["previous_library_import_count"] = sum(
        len(item.get("previous_library_imports", [])) for item in stats
    )
    total["external_library_import_count"] = sum(
        len(item.get("external_library_imports", [])) for item in stats
    )
    total["placeholder_count"] = sum(placeholders.values())
    total["file_count"] = len(stats)
    total["placeholder_counts"] = dict(placeholders)
    return dict(total)


def summarize_reasoning_trace(
    events: Sequence[Dict[str, Any]], findings: Sequence[Dict[str, Any]]
) -> Dict[str, Any]:
    """Document the responsibility of ``summarize_reasoning_trace``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``summarize_reasoning_trace`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hook_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    step_counts: Counter[str] = Counter()
    durations_ms: List[float] = []
    token_counts: Counter[str] = Counter()
    generative_event_count = 0
    lean_event_count = 0
    trajectory: List[Dict[str, Any]] = []
    for event in sorted(events, key=lambda item: item.get("event_index", 0)):
        payload = (
            event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        )
        hook = payload.get("hook_id")
        skill = payload.get("skill")
        step = event.get("step")
        if isinstance(hook, str):
            hook_counts[hook] += 1
        if isinstance(skill, str):
            skill_counts[skill] += 1
        if isinstance(step, str):
            step_counts[step] += 1
            if (
                "lean" in step.lower()
                or "compile" in step.lower()
                or "critique" in step.lower()
            ):
                lean_event_count += 1
        elapsed = event.get("elapsed_ms_since_prev_event")
        if isinstance(elapsed, (int, float)) and elapsed >= 0:
            durations_ms.append(float(elapsed))
        token_counts.update(
            flatten_numbers(
                payload,
                {
                    "prompt_tokens",
                    "input_tokens",
                    "completion_tokens",
                    "output_tokens",
                    "total_tokens",
                },
            )
        )
        if any(
            key in payload
            for key in (
                "raw_response",
                "formal_code",
                "completion_tokens",
                "output_tokens",
            )
        ):
            generative_event_count += 1
        compact_event = {
            "event_index": event.get("event_index"),
            "step": step,
            "hook_id": hook,
            "skill": skill,
            "phase": phase_from_event({"step": step, "hook_id": hook, "skill": skill}),
            "elapsed_ms_since_prev_event": elapsed,
            "measurements": extract_event_measurements(payload),
            "payload_summary": payload_summary(payload),
            "evidence": (
                (payload.get("convergence_criteria") or {}).get("current_evidence")
                if isinstance(payload.get("convergence_criteria"), dict)
                else {}
            ),
        }
        compact_event["action_kind"] = classify_action(compact_event)
        compact_event["source_type"] = classify_source_type(
            {"payload": payload}, compact_event["action_kind"]
        )
        trajectory.append(compact_event)
    total_ms = sum(durations_ms)
    return {
        "event_count": len(events),
        "invalid_event_count": len(findings),
        "hook_counts": dict(hook_counts),
        "skill_counts": dict(skill_counts),
        "step_counts": dict(step_counts),
        "duration_ms_sum": round(total_ms, 3),
        "duration_ms_max_gap": round(max(durations_ms) if durations_ms else 0.0, 3),
        "token_counts": dict(token_counts),
        "generative_event_count": generative_event_count,
        "lean_event_count": lean_event_count,
        "trajectory": trajectory,
        "findings": list(findings),
    }


def collect_artifact_evidence(args: argparse.Namespace) -> Dict[str, Any]:
    """Document the responsibility of ``collect_artifact_evidence``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``collect_artifact_evidence`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    reasoning_events, reasoning_findings = load_reasoning_logs(args.reasoning_log_file)
    lean_stats, lean_claims = analyze_lean_files(args.lean_file)
    anchor_reports = load_json_list(args.anchor_report)
    line_packets = load_json_list(args.line_translation_packet)
    realness_reports = load_json_list(args.realness_report)
    consistency_reports = load_json_list(args.consistency_report)
    workflow_reports = load_json_list(args.workflow_report)
    history_files = load_json_list(args.history_file)
    reference_free_snapshots = load_json_list(args.reference_free_snapshot)
    object_run_manifests = load_json_list(args.object_run_manifest)
    batch_manifests = load_json_list(args.batch_manifest)
    return {
        "reasoning_trace": summarize_reasoning_trace(
            reasoning_events, reasoning_findings
        ),
        "lean_file_stats": lean_stats,
        "lean_claims": lean_claims,
        "lean_summary": aggregate_lean_stats(lean_stats),
        "anchor_reports": anchor_reports,
        "line_translation_packets": line_packets,
        "realness_reports": realness_reports,
        "consistency_reports": consistency_reports,
        "workflow_reports": workflow_reports,
        "history_files": history_files,
        "reference_free_snapshots": reference_free_snapshots,
        "object_run_manifests": object_run_manifests,
        "batch_manifests": batch_manifests,
    }


def report_ok_value(report: Dict[str, Any]) -> Optional[bool]:
    """Document the responsibility of ``report_ok_value``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``report_ok_value`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for key in ("ok", "passed", "consistency_target_met", "target_met"):
        if isinstance(report.get(key), bool):
            return bool(report[key])
    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in ("ok", "passed", "consistency_target_met", "target_met"):
            if isinstance(summary.get(key), bool):
                return bool(summary[key])
    return None


def anchor_summary(
    anchor_reports: Sequence[Dict[str, Any]], lean_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """Document the responsibility of ``anchor_summary``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``anchor_summary`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if anchor_reports:
        coverages = [
            report.get("summary", {}).get("anchor_coverage")
            for report in anchor_reports
            if isinstance(
                report.get("summary", {}).get("anchor_coverage"), (int, float)
            )
        ]
        orphan_counts = [
            report.get("summary", {}).get("orphan_anchor_count", 0)
            for report in anchor_reports
            if isinstance(report.get("summary"), dict)
        ]
        return {
            "coverage": clamp01(sum(coverages) / len(coverages)) if coverages else 0.0,
            "validity": 1.0 if sum(orphan_counts) == 0 else 0.0,
            "report_count": len(anchor_reports),
            "orphan_anchor_count": sum(orphan_counts),
        }
    comment_ratio = lean_summary.get("original_source_comment_count", 0) / max(
        1, lean_summary.get("theorem_like_count", 0)
    )
    return {
        "coverage": clamp01(comment_ratio),
        "validity": 1.0,
        "report_count": 0,
        "orphan_anchor_count": 0,
    }


def realness_score(
    realness_reports: Sequence[Dict[str, Any]],
    lean_summary: Dict[str, Any],
    snapshots: Sequence[Dict[str, Any]],
) -> float:
    """Document the responsibility of ``realness_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``realness_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    for report in realness_reports:
        ok = report_ok_value(report)
        if ok is False:
            return 0.0
    for report in snapshots:
        score = (
            report.get("reference_free_snapshot", {})
            .get("scores", {})
            .get("placeholder_freedom")
        )
        if isinstance(score, (int, float)):
            return score_from_100(score)
    placeholders = lean_summary.get("placeholder_count", 0)
    axioms = lean_summary.get("axiom_count", 0)
    return 1.0 if placeholders + axioms == 0 else 0.0


def compute_metrics(evidence: Dict[str, Any], task: str) -> Dict[str, Any]:
    """Document the responsibility of ``compute_metrics``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compute_metrics`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lean = evidence["lean_summary"]
    trace = evidence["reasoning_trace"]
    anchors = anchor_summary(evidence["anchor_reports"], lean)
    snapshots = evidence["reference_free_snapshots"]
    rf_scores = {}
    for snapshot in snapshots:
        rf_scores.update(snapshot.get("reference_free_snapshot", {}).get("scores", {}))
        rf_scores.update(snapshot.get("scores", {}))
    consistency_ok = [
        report_ok_value(report) for report in evidence["consistency_reports"]
    ]
    consistency_pass = (
        all(value is not False for value in consistency_ok) if consistency_ok else None
    )
    realness = realness_score(evidence["realness_reports"], lean, snapshots)
    theorem_count = lean.get("theorem_like_count", 0)
    trivial = lean.get("trivial_statement_count", 0) + lean.get(
        "false_assumption_count", 0
    )
    nonvacuity = score_from_100(
        rf_scores.get("logical_nonvacuity"),
        default=clamp01(1.0 - trivial / max(1, theorem_count)),
    )
    mathlib_grounding = score_from_100(
        rf_scores.get("mathlib_grounding"),
        default=clamp01(
            (
                lean.get("narrow_mathlib_import_count", 0)
                + min(lean.get("mathlib_native_token_count", 0), 20) / 20
            )
            / max(1, lean.get("import_count", 0) + 1)
        ),
    )
    semantic_comments = lean.get("semantic_comment_count", 0)
    declarations = lean.get("declaration_count", 0)
    workflow_artifacts = sum(
        1
        for key in (
            "reasoning_trace",
            "anchor_reports",
            "line_translation_packets",
            "realness_reports",
            "consistency_reports",
            "workflow_reports",
            "reference_free_snapshots",
        )
        if (
            evidence[key]["event_count"]
            if key == "reasoning_trace"
            else len(evidence[key])
        )
        > 0
    )
    workflow_evidence = clamp01(workflow_artifacts / 7)
    claim_support = supported_claim_mass(evidence["lean_claims"])
    obligation_closure = obligation_closure_score(build_obligation_ledger(evidence))
    event_count = trace["event_count"]
    tool_integrity = 1.0 if trace["invalid_event_count"] == 0 else 0.0
    cost = compute_cost(evidence)
    cost_discipline = clamp01(1.0 / (1.0 + cost["normalized_cost"] / 100.0))
    metrics = {
        "rfde_profile": {
            "instruction_fit": 0.9 if task else 0.75,
            "context_fidelity": clamp01(
                (
                    anchors["coverage"]
                    + min(1.0, semantic_comments / max(1, declarations))
                )
                / 2
            ),
            "evidence_grounding": claim_support,
            "tool_integrity": tool_integrity,
            "state_continuity": (
                1.0 if event_count == 0 or trace["duration_ms_max_gap"] >= 0 else 0.6
            ),
            "obligation_closure": obligation_closure,
            "reasoning_coherence": 1.0 if consistency_pass is not False else 0.35,
            "uncertainty_calibration": uncertainty_score(evidence),
            "nonvacuity": nonvacuity,
            "boundary_compliance": 1.0,
            "cost_discipline": cost_discipline,
            "workflow_evidence": workflow_evidence,
        },
        "mathformer_profile": {
            "lean_executability": (
                1.0
                if consistency_pass is True
                else (0.7 if lean.get("file_count", 0) else 0.0)
            ),
            "source_anchor_coverage": anchors["coverage"],
            "source_anchor_validity": anchors["validity"],
            "semantic_shape_preservation": score_from_100(
                rf_scores.get("semantic_anchor_coverage"),
                default=clamp01(semantic_comments / max(1, declarations)),
            ),
            "reverse_informal_consistency": (
                1.0
                if consistency_pass is True
                else (0.6 if evidence["consistency_reports"] else 0.4)
            ),
            "mathlib_grounding": mathlib_grounding,
            "nonvacuity": nonvacuity,
            "realness": realness,
            "dependency_closure": obligation_closure,
            "workflow_evidence": workflow_evidence,
        },
    }
    for group in metrics.values():
        for key, value in list(group.items()):
            group[key] = clamp01(float(value))
    weights = {key: 1 / len(metrics["rfde_profile"]) for key in metrics["rfde_profile"]}
    hard_gate_factor = (
        1.0 if all(compute_hard_gates(evidence, metrics).values()) else 0.0
    )
    metrics["aggregate"] = {
        "ungated_rfde_score": clamp01(
            sum(metrics["rfde_profile"][key] * weights[key] for key in weights)
        ),
        "gated_rfde_score": 0.0,
        "hard_gate_factor": hard_gate_factor,
    }
    metrics["aggregate"]["gated_rfde_score"] = clamp01(
        metrics["aggregate"]["ungated_rfde_score"] * hard_gate_factor
    )
    return metrics


def supported_claim_mass(claims: Sequence[Dict[str, Any]]) -> float:
    """Document the responsibility of ``supported_claim_mass``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``supported_claim_mass`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not claims:
        return 0.65
    total = sum(float(claim.get("importance", 0.5)) for claim in claims)
    supported = sum(
        float(claim.get("importance", 0.5))
        for claim in claims
        if claim.get("support")
        or claim.get("confidence") in {"assumed", "unknown", "blocked"}
    )
    return clamp01(supported / max(1e-9, total))


def build_obligation_ledger(evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_obligation_ledger``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    obligations: List[Dict[str, Any]] = []

    def add(
        kind: str,
        description: str,
        status: str,
        support: Optional[List[str]] = None,
        weight: float = 1.0,
    ) -> None:
        """Document the responsibility of ``build_obligation_ledger.add``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Build the local data structure or artifact used by the next workflow stage.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        obligations.append(
            {
                "obligation_id": f"obl_{len(obligations)+1:04d}",
                "kind": kind,
                "description": description,
                "status": status,
                "support": support or [],
                "weight": weight,
            }
        )

    if evidence["lean_summary"].get("file_count", 0):
        add("artifact", "Lean artifact files are present.", "closed", weight=1.0)
    else:
        add("artifact", "Lean artifact files should be present.", "open", weight=1.0)
    add(
        "realness",
        "Lean artifacts should avoid placeholders, target axioms, mocks, and scaffold-only completion.",
        (
            "closed"
            if evidence["lean_summary"].get("placeholder_count", 0)
            + evidence["lean_summary"].get("axiom_count", 0)
            == 0
            else "open"
        ),
        weight=1.0,
    )
    if evidence["anchor_reports"] or evidence["line_translation_packets"]:
        anchor = anchor_summary(evidence["anchor_reports"], evidence["lean_summary"])
        add(
            "source_anchor",
            "Source-backed declarations should preserve line-translation anchors.",
            (
                "closed"
                if anchor["coverage"] >= 0.85 and anchor["validity"] == 1.0
                else "open"
            ),
            weight=1.0,
        )
    else:
        add(
            "source_anchor",
            "Line-translation anchor evidence was not provided.",
            "waived",
            weight=0.4,
        )
    if evidence["consistency_reports"]:
        ok = all(
            report_ok_value(report) is not False
            for report in evidence["consistency_reports"]
        )
        add(
            "consistency",
            "Unified or layer consistency reports should pass.",
            "closed" if ok else "blocked",
            weight=1.0,
        )
    else:
        add("consistency", "Consistency report was not provided.", "waived", weight=0.5)
    if evidence["reasoning_trace"]["event_count"]:
        add("trace", "Reasoning trace should be auditable.", "closed", weight=0.8)
    else:
        add("trace", "Reasoning trace was not provided.", "waived", weight=0.4)
    return obligations


def obligation_closure_score(obligations: Sequence[Dict[str, Any]]) -> float:
    """Document the responsibility of ``obligation_closure_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``obligation_closure_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not obligations:
        return 0.0
    weights = {
        "closed": 1.0,
        "delegated": 0.75,
        "blocked": 0.55,
        "waived": 0.45,
        "open": 0.0,
    }
    numerator = sum(
        float(item.get("weight", 1.0)) * weights.get(str(item.get("status")), 0.0)
        for item in obligations
    )
    denominator = sum(float(item.get("weight", 1.0)) for item in obligations)
    return clamp01(numerator / max(1e-9, denominator))


def uncertainty_score(evidence: Dict[str, Any]) -> float:
    """Document the responsibility of ``uncertainty_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``uncertainty_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    texts: List[str] = []
    for report_list in ("workflow_reports", "consistency_reports", "realness_reports"):
        for report in evidence[report_list]:
            texts.append(json.dumps(report, ensure_ascii=False)[:5000])
    if not texts:
        return 0.75
    has_uncertainty = any(UNCERTAINTY_RE.search(text) for text in texts)
    has_open = any(
        item.get("status") in {"open", "blocked"}
        for item in build_obligation_ledger(evidence)
    )
    return 1.0 if has_uncertainty or not has_open else 0.55


def compute_hard_gates(
    evidence: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]:
    """Document the responsibility of ``compute_hard_gates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compute_hard_gates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    metrics = metrics or {"rfde_profile": {}, "mathformer_profile": {}}
    lean = evidence["lean_summary"]
    anchor = anchor_summary(evidence["anchor_reports"], lean)
    consistency_values = [
        report_ok_value(report) for report in evidence["consistency_reports"]
    ]
    return {
        "instruction": True,
        "fabrication": supported_claim_mass(evidence["lean_claims"]) >= 0.75,
        "tool_integrity": evidence["reasoning_trace"]["invalid_event_count"] == 0,
        "safety": True,
        "core_obligations": obligation_closure_score(build_obligation_ledger(evidence))
        >= 0.55,
        "trajectory": evidence["reasoning_trace"]["event_count"] > 0,
        "contradiction": all(value is not False for value in consistency_values),
        "compile": metrics.get("mathformer_profile", {}).get("lean_executability", 0.0)
        >= 0.65,
        "realness": (lean.get("placeholder_count", 0) + lean.get("axiom_count", 0))
        == 0,
        "anchor": anchor["coverage"] >= 0.85 and anchor["validity"] == 1.0,
        "nonvacuity": metrics.get("mathformer_profile", {}).get("nonvacuity", 0.0)
        >= 0.5,
        "consistency": all(value is not False for value in consistency_values),
    }


def compute_cost(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``compute_cost``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``compute_cost`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    trace = evidence["reasoning_trace"]
    token_counts = trace["token_counts"]
    prompt_tokens = token_counts.get("prompt_tokens", 0) + token_counts.get(
        "input_tokens", 0
    )
    completion_tokens = token_counts.get("completion_tokens", 0) + token_counts.get(
        "output_tokens", 0
    )
    total_tokens = (
        token_counts.get("total_tokens", 0) or prompt_tokens + completion_tokens
    )
    deterministic_seconds = round(trace["duration_ms_sum"] / 1000.0, 3)
    normalized_cost = (
        deterministic_seconds
        + trace["lean_event_count"] * 2
        + trace["generative_event_count"] * 5
        + total_tokens / 1000.0
    )
    return {
        "deterministic_seconds": deterministic_seconds,
        "tool_or_event_count": trace["event_count"],
        "lean_invocations_or_events": trace["lean_event_count"],
        "generative_event_count": trace["generative_event_count"],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "critical_path_seconds_observed": round(
            trace["duration_ms_max_gap"] / 1000.0, 3
        ),
        "normalized_cost": round(normalized_cost, 3),
    }


def metric_delta(before: Dict[str, float], after: Dict[str, float]) -> Dict[str, float]:
    """Document the responsibility of ``metric_delta``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``metric_delta`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    delta: Dict[str, float] = {}
    for key in sorted(set(before) & set(after)):
        change = round(after[key] - before[key], 4)
        if change != 0:
            delta[key] = change
    return delta


def transition_efficiency(
    delta: Dict[str, float], duration_ms: float, source_type: str
) -> float:
    """Document the responsibility of ``transition_efficiency``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``transition_efficiency`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    positive = sum(max(0.0, value) for value in delta.values())
    negative = sum(max(0.0, -value) for value in delta.values())
    source_penalty = 5.0 if source_type == "generative" else 1.0
    denominator = 1.0 + duration_ms / 1000.0 + source_penalty
    return round((positive - 1.5 * negative) / denominator, 6)


def phase_coverage_score(actions: Sequence[Dict[str, Any]]) -> float:
    """Document the responsibility of ``phase_coverage_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_coverage_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not actions:
        return 0.0
    phases = {phase_family(str(action.get("phase"))) for action in actions}
    return clamp01(
        len(phases & REQUIRED_TRAJECTORY_PHASES) / len(REQUIRED_TRAJECTORY_PHASES)
    )


def measurement_density(actions: Sequence[Dict[str, Any]]) -> float:
    """Document the responsibility of ``measurement_density``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``measurement_density`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not actions:
        return 0.0
    measured = sum(1 for action in actions if action.get("measurements"))
    return clamp01(measured / len(actions))


def metric_family_delta(delta: Dict[str, float], terms: Sequence[str]) -> float:
    """Document the responsibility of ``metric_family_delta``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``metric_family_delta`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    total = 0.0
    lowered_terms = tuple(term.lower() for term in terms)
    for key, value in delta.items():
        lowered = key.lower()
        if any(term in lowered for term in lowered_terms):
            total += float(value)
    return round(max(-1.0, min(1.0, total)), 4)


def protected_metric_regressions(delta: Dict[str, float]) -> Dict[str, float]:
    """Document the responsibility of ``protected_metric_regressions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``protected_metric_regressions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    regressions: Dict[str, float] = {}
    for key, value in delta.items():
        if value >= 0:
            continue
        lowered = key.lower()
        if any(term in lowered for term in PROTECTED_METRIC_TERMS):
            regressions[key] = value
    return regressions


def phase_transition_kind(from_phase: str, to_phase: str, action_kind: str) -> str:
    """Document the responsibility of ``phase_transition_kind``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_transition_kind`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    from_family = phase_family(from_phase)
    to_family = phase_family(to_phase)
    if to_family == from_family and to_phase != from_phase:
        return "within_phase_refinement"
    if to_family == "preformalization":
        return "preformalization_transition"
    if to_family == "drafting" or action_kind == "generation":
        return "commitment_transition"
    if to_family == "execution" or action_kind == "execution_check":
        return "execution_transition"
    if to_family == "validation" or action_kind == "testing":
        return "validation_transition"
    if to_family == "review":
        return "review_transition"
    if to_family == "critique" or action_kind == "critique":
        return "failure_localization_transition"
    if action_kind == "repair" or to_phase in {"refinement", "repair"}:
        return "repair_transition"
    if to_phase in {"mathlib", "mathlib_alignment", "grounding"}:
        return "grounding_transition"
    if to_family == "consistency":
        return "consistency_transition"
    if (
        to_phase in {"postformalization", "artifacts"}
        or action_kind == "deterministic_gate"
    ):
        return "verification_transition"
    if to_family == "evaluation" or action_kind == "evaluation":
        return "evaluation_transition"
    if to_phase == "reflection" or action_kind == "reflection":
        return "reflection_transition"
    if to_phase == "testing" or action_kind == "testing":
        return "testing_transition"
    return "regime_shift"


def phase_transition_confidence(
    transition: Dict[str, Any],
    action: Dict[str, Any],
    previous_action: Optional[Dict[str, Any]],
    regressions: Dict[str, float],
) -> float:
    """Document the responsibility of ``phase_transition_confidence``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_transition_confidence`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    score = 0.35
    if action.get("measurements"):
        score += 0.15
    if previous_action is not None and previous_action.get("measurements"):
        score += 0.05
    if int(transition.get("new_measure_count") or 0) > 0:
        score += 0.1
    if float(transition.get("duration_ms") or 0.0) > 0:
        score += 0.1
    if transition.get("accepted_by_local_evidence") is True:
        score += 0.15
    if regressions:
        score -= 0.25
    if action.get("source_type") == "generative" and not action.get("measurements"):
        score -= 0.05
    return clamp01(score)


def phase_transition_irreversibility(
    kind: str, action: Dict[str, Any], regressions: Dict[str, float]
) -> float:
    """Document the responsibility of ``phase_transition_irreversibility``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_transition_irreversibility`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    base = {
        "commitment_transition": 0.72,
        "preformalization_transition": 0.58,
        "execution_transition": 0.64,
        "validation_transition": 0.68,
        "failure_localization_transition": 0.44,
        "repair_transition": 0.6,
        "grounding_transition": 0.66,
        "review_transition": 0.62,
        "consistency_transition": 0.7,
        "verification_transition": 0.72,
        "evaluation_transition": 0.76,
        "reflection_transition": 0.8,
        "testing_transition": 0.52,
        "within_phase_refinement": 0.46,
    }.get(kind, 0.5)
    if action.get("source_type") == "generative":
        base += 0.06
    if regressions:
        base += 0.12
    return clamp01(base)


def order_parameter_delta(
    transition: Dict[str, Any], action: Dict[str, Any], kind: str
) -> Dict[str, Any]:
    """Document the responsibility of ``order_parameter_delta``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``order_parameter_delta`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    delta = dict(transition.get("metric_delta") or {})
    obligation_closure_delta = metric_family_delta(delta, ("obligation", "closure"))
    return {
        "obligation_entropy": round(-obligation_closure_delta, 4),
        "formal_commitment": (
            1.0 if kind in {"commitment_transition", "execution_transition"} else 0.0
        ),
        "executability": metric_family_delta(
            delta, ("executability", "compile", "lean")
        ),
        "semantic_constraint": metric_family_delta(
            delta, ("semantic", "source", "anchor", "fidelity")
        ),
        "grounding_density": metric_family_delta(delta, ("grounding", "mathlib")),
        "repair_pressure": clamp01(
            float(transition.get("regression_movement") or 0.0)
            + (0.25 if action.get("action_kind") in {"repair", "critique"} else 0.0)
        ),
        "uncertainty_explicitness": metric_family_delta(
            delta, ("uncertainty", "blocked", "risk", "gap")
        ),
        "cost_gradient_seconds": round(
            float(transition.get("duration_ms") or 0.0) / 1000.0, 4
        ),
        "observed_metric_delta": delta,
    }


def detect_phase_transitions(
    actions: Sequence[Dict[str, Any]],
    transitions: Sequence[Dict[str, Any]],
    states: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``detect_phase_transitions``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``detect_phase_transitions`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not actions:
        return []
    action_by_id = {str(action.get("action_id")): action for action in actions}
    state_by_id = {str(state.get("state_id")): state for state in states}
    previous_action_by_id: Dict[str, Optional[Dict[str, Any]]] = {}
    previous: Optional[Dict[str, Any]] = None
    for action in actions:
        previous_action_by_id[str(action.get("action_id"))] = previous
        previous = action

    phase_transitions: List[Dict[str, Any]] = []
    for transition in transitions:
        from_state = state_by_id.get(str(transition.get("from_state")), {})
        to_state = state_by_id.get(str(transition.get("to_state")), {})
        from_phase = str(from_state.get("phase") or "unknown")
        to_phase = str(to_state.get("phase") or transition.get("phase") or "unknown")
        if from_phase in {"initial", "unknown"} or from_phase == to_phase:
            continue
        action = action_by_id.get(str(transition.get("action_id")), {})
        previous_action = previous_action_by_id.get(str(action.get("action_id")))
        kind = phase_transition_kind(
            from_phase, to_phase, str(action.get("action_kind") or "observation")
        )
        regressions = protected_metric_regressions(
            dict(transition.get("metric_delta") or {})
        )
        confidence = phase_transition_confidence(
            transition, action, previous_action, regressions
        )
        irreversibility = phase_transition_irreversibility(kind, action, regressions)
        healthy = (
            confidence >= 0.55
            and not regressions
            and transition.get("accepted_by_local_evidence") is True
        )
        phase_transitions.append(
            {
                "phase_transition_id": f"pt_{len(phase_transitions)+1:04d}",
                "from_phase": from_phase,
                "to_phase": to_phase,
                "kind": kind,
                "trigger_event_index": action.get("event_index"),
                "trigger_step": action.get("step"),
                "hook_id": action.get("hook_id"),
                "action_id": action.get("action_id"),
                "from_state": transition.get("from_state"),
                "to_state": transition.get("to_state"),
                "trigger_cumulative_ms": transition.get("end_cumulative_ms"),
                "evidence_before": {
                    "event_index": (
                        previous_action.get("event_index") if previous_action else None
                    ),
                    "phase": (
                        previous_action.get("phase") if previous_action else from_phase
                    ),
                    "measurement_count": (
                        len(previous_action.get("measurements", {}))
                        if previous_action
                        else 0
                    ),
                },
                "evidence_after": {
                    "event_index": action.get("event_index"),
                    "phase": to_phase,
                    "measurement_count": len(action.get("measurements", {})),
                    "accepted_by_local_evidence": transition.get(
                        "accepted_by_local_evidence"
                    ),
                },
                "order_parameter_delta": order_parameter_delta(
                    transition, action, kind
                ),
                "positive_movement": transition.get("positive_movement"),
                "regression_movement": transition.get("regression_movement"),
                "protected_metric_regressions": regressions,
                "transition_confidence": confidence,
                "irreversibility_pressure": irreversibility,
                "healthy": healthy,
                "interpretation": (
                    f"Phase changed from {from_phase} to {to_phase} through a {kind.replace('_', ' ')}."
                ),
            }
        )
    return phase_transitions


def phase_transition_observability_score(
    actions: Sequence[Dict[str, Any]], phase_transitions: Sequence[Dict[str, Any]]
) -> float:
    """Document the responsibility of ``phase_transition_observability_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_transition_observability_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not actions:
        return 0.0
    observed_phases = [str(action.get("phase") or "unknown") for action in actions]
    expected = max(1, len(set(observed_phases)) - 1)
    if len(set(observed_phases)) <= 1:
        return 0.0 if len(actions) >= 3 else 0.35
    coverage = min(1.0, len(phase_transitions) / expected)
    average_confidence = sum(
        float(item.get("transition_confidence") or 0.0) for item in phase_transitions
    ) / max(1, len(phase_transitions))
    return clamp01(
        0.4 * coverage + 0.35 * average_confidence + 0.25 * measurement_density(actions)
    )


def build_phase_segments(
    actions: Sequence[Dict[str, Any]], transitions: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_phase_segments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not actions:
        return []
    segments: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    by_action_transition = {
        transition["action_id"]: transition for transition in transitions
    }
    for action in actions:
        phase = str(action.get("phase") or "unknown")
        if current is None or current["phase"] != phase:
            if current is not None:
                segments.append(current)
            current = {
                "segment_id": f"seg_{len(segments)+1:03d}",
                "phase": phase,
                "start_event_index": action.get("event_index"),
                "end_event_index": action.get("event_index"),
                "start_cumulative_ms": action.get("start_cumulative_ms", 0.0),
                "end_cumulative_ms": action.get("end_cumulative_ms", 0.0),
                "event_count": 0,
                "duration_ms": 0.0,
                "action_kind_counts": defaultdict(int),
                "source_type_counts": defaultdict(int),
                "positive_movement": 0.0,
                "regression_movement": 0.0,
                "efficiency": 0.0,
            }
        current["end_event_index"] = action.get("event_index")
        current["end_cumulative_ms"] = action.get(
            "end_cumulative_ms", current["end_cumulative_ms"]
        )
        current["event_count"] += 1
        current["duration_ms"] += float(action.get("duration_ms") or 0.0)
        current["action_kind_counts"][
            str(action.get("action_kind") or "observation")
        ] += 1
        current["source_type_counts"][
            str(action.get("source_type") or "deterministic")
        ] += 1
        transition = by_action_transition.get(str(action.get("action_id")))
        if transition is not None:
            current["positive_movement"] += float(
                transition.get("positive_movement") or 0.0
            )
            current["regression_movement"] += float(
                transition.get("regression_movement") or 0.0
            )
            current["efficiency"] += float(
                transition.get("cost_normalized_progress") or 0.0
            )
    if current is not None:
        segments.append(current)
    for segment in segments:
        segment["duration_ms"] = round(segment["duration_ms"], 3)
        segment["start_cumulative_ms"] = round(
            float(segment.get("start_cumulative_ms") or 0.0), 3
        )
        segment["end_cumulative_ms"] = round(
            float(segment.get("end_cumulative_ms") or 0.0), 3
        )
        segment["action_kind_counts"] = dict(segment["action_kind_counts"])
        segment["source_type_counts"] = dict(segment["source_type_counts"])
        segment["positive_movement"] = round(segment["positive_movement"], 4)
        segment["regression_movement"] = round(segment["regression_movement"], 4)
        segment["efficiency"] = round(segment["efficiency"], 6)
    return segments


def raw_action_evidence(action: Dict[str, Any]) -> Dict[str, Any]:
    """Document the responsibility of ``raw_action_evidence``.

    Motivation:
        Keep cycle statistics tied to the original event evidence rather than only normalized RFDE scores.

    Intent:
        Recover the current-evidence packet carried by an action so dashboard tables can report
        count-like quantities such as Lean lines, theorem counts, probes, and support facts.

    Inputs:
        A trajectory action produced from a reasoning-log event.

    Outputs:
        A shallow evidence dictionary, or an empty dictionary when no raw evidence was attached.
    """
    evidence = action.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    payload = (
        action.get("payload_summary", {})
        if isinstance(action.get("payload_summary"), dict)
        else {}
    )
    criteria = (
        payload.get("convergence_criteria", {})
        if isinstance(payload.get("convergence_criteria"), dict)
        else {}
    )
    current = (
        criteria.get("current_evidence", {})
        if isinstance(criteria.get("current_evidence"), dict)
        else {}
    )
    return current if isinstance(current, dict) else {}


def raw_metric_by_suffix(evidence: Dict[str, Any], suffixes: Sequence[str]) -> Any:
    """Document the responsibility of ``raw_metric_by_suffix``.

    Motivation:
        Let cycle tables use stable semantic names while accepting small schema variations.

    Intent:
        Find the first raw evidence value whose path equals or ends with one of the requested suffixes.

    Inputs:
        A raw evidence mapping and candidate suffixes such as ``lean_lines`` or ``theorem_count``.

    Outputs:
        The matching value, or ``None`` when no compatible field exists.
    """
    lowered_suffixes = tuple(str(suffix).lower() for suffix in suffixes)
    for path, value in iter_leaf_values(evidence):
        lowered = path.lower()
        if any(
            lowered == suffix or lowered.endswith("." + suffix)
            for suffix in lowered_suffixes
        ):
            return value
    return None


def count_value(value: Any) -> Optional[int]:
    """Document the responsibility of ``count_value``.

    Motivation:
        Separate count-like evidence from normalized scoring metrics.

    Intent:
        Convert raw numeric count fields to integer counts while ignoring booleans and missing values.

    Inputs:
        A raw evidence value.

    Outputs:
        A non-negative integer count, or ``None`` when the value is not count-like.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(0, int(round(float(value))))


def score_value(value: Any) -> Optional[float]:
    """Document the responsibility of ``score_value``.

    Motivation:
        Show score evolution on a common zero-to-one scale even when logs report percentages.

    Intent:
        Normalize raw score-like values for cycle statistics and SVG plots.

    Inputs:
        A raw evidence score or boolean.

    Outputs:
        A normalized score, or ``None`` when the value cannot be interpreted numerically.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if not isinstance(value, (int, float)):
        return None
    return normalized_score(value, default=0.0)


def grounded_fact_increment(evidence: Dict[str, Any]) -> int:
    """Document the responsibility of ``grounded_fact_increment``.

    Motivation:
        Make the dashboard reveal how the locally grounded evidence surface grows across loops.

    Intent:
        Count raw evidence fields that behave like grounded facts or support units, excluding
        meta-scores, pass flags, and risk counters.

    Inputs:
        A raw current-evidence packet from a reasoning-log event.

    Outputs:
        A conservative count proxy for newly observed grounded facts in that cycle event.
    """
    count = 0
    count_suffixes = (
        "source_units",
        "expanded_steps",
        "typed_quantities_identified",
        "probe_count",
    )
    fact_terms = (
        "support",
        "source",
        "comment",
        "unit",
        "dimension",
        "semantic",
        "assumption",
        "nonvacuity",
        "gate",
        "bridge",
        "map",
        "available",
        "carrier",
        "field",
    )
    skip_terms = (
        "ok",
        "score",
        "coverage",
        "readiness",
        "blocking",
        "finding",
        "status",
        "risk",
        "sorry",
        "axiom",
        "silent_strengthening",
    )
    for path, value in iter_leaf_values(evidence):
        lowered = path.lower()
        if any(term in lowered for term in skip_terms):
            continue
        if any(
            lowered == suffix or lowered.endswith("." + suffix)
            for suffix in count_suffixes
        ):
            numeric = count_value(value)
            if numeric is not None:
                count += numeric
            continue
        if any(term in lowered for term in fact_terms):
            if isinstance(value, bool) and value:
                count += 1
            elif (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and float(value) > 0
            ):
                count += max(1, int(round(float(value))))
            elif isinstance(value, str) and value.strip():
                count += 1
    return count


def build_cycle_statistics(
    actions: Sequence[Dict[str, Any]],
    transitions: Sequence[Dict[str, Any]],
    phase_segments: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``build_cycle_statistics``.

    Motivation:
        Make reference-free evolution inspectable as concrete, per-cycle statistics.

    Intent:
        Summarize each observed phase segment as a refinement cycle, tracking cumulative grounded
        facts, formal statements, Lean lines, score movement, blockers, and transition pressure.

    Inputs:
        The trajectory actions, transitions, and phase segments built from a reasoning log.

    Outputs:
        A list of cycle-statistic rows suitable for JSON reports, Markdown tables, and HTML dashboards.
    """
    if not actions or not phase_segments:
        return []
    actions_by_event = {
        int(action.get("event_index") or 0): action for action in actions
    }
    transitions_by_action = {
        str(transition.get("action_id")): transition for transition in transitions
    }
    latest: Dict[str, Any] = {
        "grounded_fact_count": 0,
        "statement_count": 0,
        "lean_line_count": 0,
        "theorem_count": 0,
        "axiom_count": 0,
        "sorry_count": 0,
        "score": None,
        "best_score": 0.0,
        "coverage": None,
        "blocking_findings": None,
    }
    rows: List[Dict[str, Any]] = []
    for index, segment in enumerate(phase_segments, start=1):
        start_event = int(segment.get("start_event_index") or 0)
        end_event = int(segment.get("end_event_index") or start_event)
        segment_actions = [
            actions_by_event[event_index]
            for event_index in range(start_event, end_event + 1)
            if event_index in actions_by_event
        ]
        before = dict(latest)
        new_grounded_facts = 0
        passed_actions = 0
        scored_actions = 0
        segment_scores: List[float] = []
        segment_coverage: List[float] = []
        positive_movement = 0.0
        regression_movement = 0.0
        for action in segment_actions:
            evidence = raw_action_evidence(action)
            new_grounded_facts += grounded_fact_increment(evidence)
            latest["grounded_fact_count"] = int(
                latest.get("grounded_fact_count") or 0
            ) + grounded_fact_increment(evidence)
            theorem_count = count_value(
                raw_metric_by_suffix(evidence, ("theorem_count",))
            )
            axiom_count = count_value(raw_metric_by_suffix(evidence, ("axiom_count",)))
            declaration_count = count_value(
                raw_metric_by_suffix(evidence, ("declaration_count", "statement_count"))
            )
            lean_lines = count_value(
                raw_metric_by_suffix(evidence, ("lean_lines", "formal_code_line_count"))
            )
            sorry_count = count_value(raw_metric_by_suffix(evidence, ("sorry_count",)))
            if theorem_count is not None:
                latest["theorem_count"] = theorem_count
            if axiom_count is not None:
                latest["axiom_count"] = axiom_count
            if declaration_count is not None:
                latest["statement_count"] = max(
                    int(latest.get("statement_count") or 0), declaration_count
                )
            if theorem_count is not None or axiom_count is not None:
                latest["statement_count"] = max(
                    int(latest.get("statement_count") or 0),
                    int(latest.get("theorem_count") or 0)
                    + int(latest.get("axiom_count") or 0),
                )
            if lean_lines is not None:
                latest["lean_line_count"] = lean_lines
            if sorry_count is not None:
                latest["sorry_count"] = sorry_count
            score = score_value(
                raw_metric_by_suffix(
                    evidence,
                    ("score", "readiness_score", "reference_free_confidence_score"),
                )
            )
            if score is not None:
                latest["score"] = score
                latest["best_score"] = max(
                    float(latest.get("best_score") or 0.0), float(score)
                )
                segment_scores.append(score)
                scored_actions += 1
            coverage = score_value(
                raw_metric_by_suffix(
                    evidence, ("coverage", "anchor_coverage", "source_anchor_coverage")
                )
            )
            if coverage is not None:
                latest["coverage"] = coverage
                segment_coverage.append(coverage)
            blockers = count_value(
                raw_metric_by_suffix(
                    evidence, ("blocking_findings", "blocking_finding_count")
                )
            )
            if blockers is not None:
                latest["blocking_findings"] = blockers
            passed = action_pass_value(action)
            if passed is True:
                passed_actions += 1
            transition = transitions_by_action.get(str(action.get("action_id")))
            if transition is not None:
                positive_movement += float(transition.get("positive_movement") or 0.0)
                regression_movement += float(
                    transition.get("regression_movement") or 0.0
                )
        score_after = latest.get("score")
        score_before = before.get("score")
        row = {
            "cycle_id": f"cycle_{index:03d}",
            "segment_id": segment.get("segment_id"),
            "phase": segment.get("phase"),
            "phase_family": phase_family(str(segment.get("phase") or "unknown")),
            "event_range": f"{start_event}-{end_event}",
            "action_count": len(segment_actions),
            "duration_ms": segment.get("duration_ms", 0.0),
            "new_grounded_facts": new_grounded_facts,
            "grounded_fact_count": latest.get("grounded_fact_count", 0),
            "statement_count": latest.get("statement_count", 0),
            "statement_delta": int(latest.get("statement_count") or 0)
            - int(before.get("statement_count") or 0),
            "lean_line_count": latest.get("lean_line_count", 0),
            "lean_line_delta": int(latest.get("lean_line_count") or 0)
            - int(before.get("lean_line_count") or 0),
            "theorem_count": latest.get("theorem_count", 0),
            "axiom_count": latest.get("axiom_count", 0),
            "sorry_count": latest.get("sorry_count", 0),
            "score": (
                round(float(score_after), 4)
                if isinstance(score_after, (int, float))
                else None
            ),
            "best_score": round(float(latest.get("best_score") or 0.0), 4),
            "score_delta": (
                round(float(score_after) - float(score_before), 4)
                if isinstance(score_after, (int, float))
                and isinstance(score_before, (int, float))
                else None
            ),
            "coverage": (
                round(float(latest["coverage"]), 4)
                if isinstance(latest.get("coverage"), (int, float))
                else None
            ),
            "blocking_findings": latest.get("blocking_findings"),
            "passed_actions": passed_actions,
            "pass_rate": round(passed_actions / max(1, len(segment_actions)), 4),
            "scored_actions": scored_actions,
            "positive_movement": round(positive_movement, 4),
            "regression_movement": round(regression_movement, 4),
            "efficiency": segment.get("efficiency", 0.0),
            "interpretation": (
                "formal artifact growth"
                if int(latest.get("lean_line_count") or 0)
                > int(before.get("lean_line_count") or 0)
                else (
                    "new grounded evidence"
                    if new_grounded_facts > 0
                    else "metric stabilization"
                )
            ),
        }
        rows.append(row)
    return rows


def detect_loop_candidates(actions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``detect_loop_candidates``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``detect_loop_candidates`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    loops: List[Dict[str, Any]] = []
    hook_positions: Dict[str, List[int]] = defaultdict(list)
    for index, action in enumerate(actions):
        hook = str(action.get("hook_id") or "")
        if hook:
            hook_positions[hook].append(index)
    for hook, positions in sorted(hook_positions.items()):
        if len(positions) < 2:
            continue
        loops.append(
            {
                "loop_id": f"loop_{len(loops)+1:03d}",
                "kind": "repeated_hook",
                "hook_id": hook,
                "occurrence_count": len(positions),
                "start_event_index": actions[positions[0]].get("event_index"),
                "end_event_index": actions[positions[-1]].get("event_index"),
                "interpretation": "The same hook recurs and should be inspected as a refinement or monitoring loop.",
            }
        )
    for index in range(max(0, len(actions) - 2)):
        window = actions[index : index + 3]
        kinds = [str(action.get("action_kind")) for action in window]
        if (
            kinds[0] in {"critique", "deterministic_gate", "execution_check"}
            and kinds[1] in {"repair", "generation"}
            and kinds[2]
            in {
                "deterministic_gate",
                "execution_check",
                "critique",
            }
        ):
            loops.append(
                {
                    "loop_id": f"loop_{len(loops)+1:03d}",
                    "kind": "critic_repair_gate",
                    "action_kinds": kinds,
                    "start_event_index": window[0].get("event_index"),
                    "end_event_index": window[-1].get("event_index"),
                    "interpretation": "A check or critique is followed by generation/repair and then a new check.",
                }
            )
    return loops


def detect_oscillation(transitions: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Document the responsibility of ``detect_oscillation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``detect_oscillation`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    signs_by_metric: Dict[str, List[int]] = defaultdict(list)
    for transition in transitions:
        for key, value in transition.get("metric_delta", {}).items():
            if value > 0:
                signs_by_metric[key].append(1)
            elif value < 0:
                signs_by_metric[key].append(-1)
    oscillations: List[Dict[str, Any]] = []
    for key, signs in signs_by_metric.items():
        if len(signs) < 2:
            continue
        flips = sum(1 for left, right in zip(signs, signs[1:]) if left != right)
        if flips:
            oscillations.append(
                {"metric": key, "sign_changes": flips, "observations": len(signs)}
            )
    return oscillations


def build_trajectory_model(
    evidence: Dict[str, Any],
    metrics: Dict[str, Any],
    hard_gates: Dict[str, bool],
    cost: Dict[str, Any],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_trajectory_model``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    trace = evidence["reasoning_trace"]
    raw_events = trace.get("trajectory", [])
    states: List[Dict[str, Any]] = [
        {
            "state_id": "s0000",
            "after_event_index": None,
            "phase": "initial",
            "cumulative_ms": 0.0,
            "observed_metrics": {},
            "hard_gate_snapshot": {},
        }
    ]
    actions: List[Dict[str, Any]] = []
    transitions: List[Dict[str, Any]] = []
    current_metrics: Dict[str, float] = {}
    cumulative_ms = 0.0
    for index, event in enumerate(raw_events, start=1):
        elapsed = event.get("elapsed_ms_since_prev_event")
        duration_ms = (
            float(elapsed)
            if isinstance(elapsed, (int, float)) and elapsed >= 0
            else 0.0
        )
        start_ms = cumulative_ms
        cumulative_ms += duration_ms
        measurements = dict(event.get("measurements") or {})
        phase = str(event.get("phase") or phase_from_event(event))
        action_kind = str(event.get("action_kind") or classify_action(event))
        source_type = str(
            event.get("source_type") or classify_source_type(event, action_kind)
        )
        action = {
            "action_id": f"a{index:04d}",
            "event_index": event.get("event_index"),
            "step": event.get("step"),
            "hook_id": event.get("hook_id"),
            "skill": event.get("skill"),
            "phase": phase,
            "action_kind": action_kind,
            "source_type": source_type,
            "duration_ms": round(duration_ms, 3),
            "start_cumulative_ms": round(start_ms, 3),
            "end_cumulative_ms": round(cumulative_ms, 3),
            "measurements": measurements,
            "payload_summary": event.get("payload_summary", {}),
            "evidence": event.get("evidence", {}),
        }
        before_metrics = dict(current_metrics)
        current_metrics.update(measurements)
        delta = metric_delta(before_metrics, current_metrics)
        positive_movement = sum(max(0.0, value) for value in delta.values())
        regression_movement = sum(max(0.0, -value) for value in delta.values())
        state = {
            "state_id": f"s{index:04d}",
            "after_event_index": event.get("event_index"),
            "phase": phase,
            "cumulative_ms": round(cumulative_ms, 3),
            "observed_metrics": (
                dict(sorted(current_metrics.items()))
                if len(current_metrics) <= 40
                else dict(sorted(current_metrics.items())[:40])
            ),
            "hard_gate_snapshot": hard_gates if index == len(raw_events) else {},
        }
        transition = {
            "transition_id": f"tr{index:04d}",
            "from_state": states[-1]["state_id"],
            "to_state": state["state_id"],
            "action_id": action["action_id"],
            "phase": phase,
            "action_kind": action_kind,
            "source_type": source_type,
            "duration_ms": round(duration_ms, 3),
            "start_cumulative_ms": round(start_ms, 3),
            "end_cumulative_ms": round(cumulative_ms, 3),
            "metric_delta": delta,
            "new_measure_count": len(set(current_metrics) - set(before_metrics)),
            "positive_movement": round(positive_movement, 4),
            "regression_movement": round(regression_movement, 4),
            "cost_normalized_progress": transition_efficiency(
                delta, duration_ms, source_type
            ),
            "accepted_by_local_evidence": action.get("payload_summary", {}).get("ok")
            is not False
            and action.get("payload_summary", {}).get("passed") is not False,
        }
        actions.append(action)
        transitions.append(transition)
        states.append(state)

    phase_segments = build_phase_segments(actions, transitions)
    phase_transitions = detect_phase_transitions(actions, transitions, states)
    cycle_statistics = build_cycle_statistics(actions, transitions, phase_segments)
    loops = detect_loop_candidates(actions)
    oscillations = detect_oscillation(transitions)
    total_duration = sum(float(action.get("duration_ms") or 0.0) for action in actions)
    phase_duration: Any = Counter()  # Durations are floating-point seconds.
    source_type_counts: Counter[str] = Counter()
    for action in actions:
        phase_duration[str(action.get("phase") or "unknown")] += float(
            action.get("duration_ms") or 0.0
        )
        source_type_counts[str(action.get("source_type") or "deterministic")] += 1
    dominant_phase, dominant_phase_ms = ("none", 0.0)
    if phase_duration:
        dominant_phase, dominant_phase_ms = phase_duration.most_common(1)[0]
    transition_delta_density = clamp01(
        sum(1 for transition in transitions if transition.get("metric_delta"))
        / max(1, len(transitions))
    )
    phase_transition_observability = phase_transition_observability_score(
        actions, phase_transitions
    )
    observability = clamp01(
        0.2 * min(1.0, len(actions) / 8.0)
        + 0.2 * phase_coverage_score(actions)
        + 0.2 * measurement_density(actions)
        + 0.2 * (1.0 if total_duration > 0 else 0.0)
        + 0.2 * phase_transition_observability
    )
    net_progress = sum(
        float(transition.get("positive_movement") or 0.0) for transition in transitions
    ) - 1.5 * sum(
        float(transition.get("regression_movement") or 0.0)
        for transition in transitions
    )
    cost_normalized_progress = round(
        net_progress / (1.0 + float(cost.get("normalized_cost") or 0.0)), 6
    )
    hard_gate_ratio = sum(1 for value in hard_gates.values() if value) / max(
        1, len(hard_gates)
    )
    convergence_score = clamp01(
        0.4 * hard_gate_ratio
        + 0.22 * metrics["aggregate"]["ungated_rfde_score"]
        + 0.18 * observability
        + 0.12 * phase_transition_observability
        + 0.08 * (1.0 if not oscillations else 0.5)
    )
    dynamics: List[Dict[str, Any]] = []
    observed_phase_coverage = phase_coverage_score(actions)
    if observed_phase_coverage < 0.45:
        dynamics.append(
            {
                "predicate": "phase_coverage_gap",
                "severity": "medium",
                "evidence": {
                    "phase_coverage": observed_phase_coverage,
                    "observed_phases": sorted(
                        {str(action.get("phase") or "unknown") for action in actions}
                    ),
                    "required_phases": sorted(REQUIRED_TRAJECTORY_PHASES),
                },
                "interpretation": "The trace does not expose enough distinct workflow phases to model the full autoformalization trajectory.",
            }
        )
    if len(phase_segments) == 1 and len(actions) >= 3:
        dynamics.append(
            {
                "predicate": "single_phase_trace",
                "severity": "medium",
                "evidence": {
                    "phase": phase_segments[0]["phase"],
                    "action_count": len(actions),
                },
                "interpretation": "All observed actions belong to one phase; attach the full workflow reasoning log to model cross-phase dynamics.",
            }
        )
    if len(actions) >= 3 and not phase_transitions:
        dynamics.append(
            {
                "predicate": "phase_transition_absent",
                "severity": "medium",
                "evidence": {
                    "action_count": len(actions),
                    "observed_phases": sorted(
                        {str(action.get("phase") or "unknown") for action in actions}
                    ),
                },
                "interpretation": "No phase transition was observed; the report cannot localize regime shifts or phase-boundary causes.",
            }
        )
    if phase_transitions:
        average_transition_confidence = sum(
            float(item.get("transition_confidence") or 0.0)
            for item in phase_transitions
        ) / max(1, len(phase_transitions))
        unhealthy = [item for item in phase_transitions if not item.get("healthy")]
        if average_transition_confidence < 0.55:
            dynamics.append(
                {
                    "predicate": "low_confidence_phase_transitions",
                    "severity": "medium",
                    "evidence": {
                        "average_transition_confidence": round(
                            average_transition_confidence, 4
                        )
                    },
                    "interpretation": "Phase changes are visible, but their evidence is too weak for strong trajectory claims.",
                }
            )
        if unhealthy:
            dynamics.append(
                {
                    "predicate": "unhealthy_phase_transition",
                    "severity": "medium",
                    "evidence": {
                        "transition_ids": [
                            str(item.get("phase_transition_id"))
                            for item in unhealthy[:8]
                        ],
                        "count": len(unhealthy),
                    },
                    "interpretation": "At least one phase change has low confidence, failed local evidence, or protected-metric regression.",
                }
            )
    if len(actions) >= 3 and phase_transition_observability < 0.45:
        dynamics.append(
            {
                "predicate": "phase_transition_underinstrumented",
                "severity": "medium",
                "evidence": {
                    "phase_transition_observability": phase_transition_observability
                },
                "interpretation": "The trace does not expose enough evidence at phase boundaries to model trajectory regimes.",
            }
        )
    if observability < 0.55:
        dynamics.append(
            {
                "predicate": "trajectory_underinstrumented",
                "severity": "medium",
                "evidence": {
                    "trajectory_observability": observability,
                    "event_count": len(actions),
                },
                "interpretation": "The run has too little phase, measurement, or timing evidence for strong trajectory claims.",
            }
        )
    if (
        len(actions) >= 5
        and transition_delta_density < 0.15
        and float(cost.get("normalized_cost") or 0.0) > 20
    ):
        dynamics.append(
            {
                "predicate": "plateau_candidate",
                "severity": "medium",
                "evidence": {
                    "transition_delta_density": transition_delta_density,
                    "normalized_cost": cost.get("normalized_cost"),
                },
                "interpretation": "Cost accumulates while few event-level measurements move.",
            }
        )
    if oscillations:
        dynamics.append(
            {
                "predicate": "oscillation_candidate",
                "severity": "medium",
                "evidence": {"oscillating_metrics": oscillations[:8]},
                "interpretation": "Some observed metrics alternate improvement and regression.",
            }
        )
    repair_loop_count = sum(1 for loop in loops if loop["kind"] == "critic_repair_gate")
    if repair_loop_count:
        dynamics.append(
            {
                "predicate": "explicit_repair_loop",
                "severity": "info",
                "evidence": {"repair_loop_count": repair_loop_count},
                "interpretation": "The trace contains an explicit check/repair/check trajectory.",
            }
        )
    if all(hard_gates.values()):
        dynamics.append(
            {
                "predicate": "terminal_gate_convergence",
                "severity": "info",
                "evidence": {"hard_gate_ratio": 1.0},
                "interpretation": "The terminal state satisfies all RFDE hard gates.",
            }
        )
    if not dynamics:
        dynamics.append(
            {
                "predicate": "stable_but_sparse_trajectory",
                "severity": "info",
                "evidence": {"event_count": len(actions)},
                "interpretation": "No adverse dynamics were detected in the available trajectory.",
            }
        )
    model = {
        "schema_version": 2,
        "priority": "primary",
        "summary": {
            "state_count": len(states),
            "action_count": len(actions),
            "transition_count": len(transitions),
            "phase_segment_count": len(phase_segments),
            "cycle_count": len(cycle_statistics),
            "phase_transition_count": len(phase_transitions),
            "healthy_phase_transition_count": sum(
                1 for item in phase_transitions if item.get("healthy")
            ),
            "loop_candidate_count": len(loops),
            "trajectory_observability": observability,
            "phase_coverage": phase_coverage_score(actions),
            "phase_transition_observability": phase_transition_observability,
            "phase_transition_average_confidence": round(
                sum(
                    float(item.get("transition_confidence") or 0.0)
                    for item in phase_transitions
                )
                / max(1, len(phase_transitions)),
                4,
            ),
            "measurement_density": measurement_density(actions),
            "transition_delta_density": transition_delta_density,
            "convergence_score": convergence_score,
            "cost_normalized_progress": cost_normalized_progress,
            "dominant_phase": dominant_phase,
            "dominant_phase_seconds": round(float(dominant_phase_ms) / 1000.0, 3),
            "terminal_grounded_fact_count": (
                cycle_statistics[-1].get("grounded_fact_count", 0)
                if cycle_statistics
                else 0
            ),
            "terminal_statement_count": (
                cycle_statistics[-1].get("statement_count", 0)
                if cycle_statistics
                else 0
            ),
        },
        "states": states,
        "actions": actions,
        "transitions": transitions,
        "phase_segments": phase_segments,
        "cycle_statistics": cycle_statistics,
        "phase_transitions": phase_transitions,
        "loop_candidates": loops,
        "dynamics": dynamics,
        "convergence_condition": {
            "status": (
                "satisfied"
                if all(hard_gates.values()) and convergence_score >= 0.7
                else "weak"
            ),
            "criteria": {
                "hard_gates_pass": all(hard_gates.values()),
                "observability_at_least_0_55": observability >= 0.55,
                "no_oscillation_detected": not oscillations,
                "terminal_score_at_least_0_78": metrics["aggregate"][
                    "ungated_rfde_score"
                ]
                >= 0.78,
            },
            "terminal_state": states[-1]["state_id"],
        },
        "temporal_cost_model": {
            "observed_wall_seconds": round(total_duration / 1000.0, 3),
            "critical_path_seconds_observed": cost.get(
                "critical_path_seconds_observed", 0
            ),
            "phase_seconds": {
                phase: round(value / 1000.0, 3)
                for phase, value in sorted(phase_duration.items())
            },
            "source_type_counts": dict(source_type_counts),
            "dominant_phase_cost_share": clamp01(
                float(dominant_phase_ms) / max(1.0, total_duration)
            ),
            "normalized_cost": cost.get("normalized_cost"),
        },
    }
    return model


def attach_trajectory_metrics(
    metrics: Dict[str, Any],
    trajectory_model: Dict[str, Any],
    hard_gates: Dict[str, bool],
) -> None:
    """Document the responsibility of ``attach_trajectory_metrics``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``attach_trajectory_metrics`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    summary = trajectory_model.get("summary", {})
    metrics["trajectory_profile"] = {
        "trajectory_observability": clamp01(
            float(summary.get("trajectory_observability") or 0.0)
        ),
        "phase_coverage": clamp01(float(summary.get("phase_coverage") or 0.0)),
        "phase_transition_observability": clamp01(
            float(summary.get("phase_transition_observability") or 0.0)
        ),
        "phase_transition_confidence": clamp01(
            float(summary.get("phase_transition_average_confidence") or 0.0)
        ),
        "measurement_density": clamp01(
            float(summary.get("measurement_density") or 0.0)
        ),
        "transition_delta_density": clamp01(
            float(summary.get("transition_delta_density") or 0.0)
        ),
        "convergence_score": clamp01(float(summary.get("convergence_score") or 0.0)),
        "cost_normalized_progress": clamp01(
            0.5 + float(summary.get("cost_normalized_progress") or 0.0)
        ),
    }
    metrics["rfde_profile"]["trajectory_observability"] = metrics["trajectory_profile"][
        "trajectory_observability"
    ]
    metrics["rfde_profile"]["trajectory_convergence"] = metrics["trajectory_profile"][
        "convergence_score"
    ]
    metrics["rfde_profile"]["phase_transition_observability"] = metrics[
        "trajectory_profile"
    ]["phase_transition_observability"]
    metrics["rfde_profile"]["trajectory_cost_alignment"] = metrics[
        "trajectory_profile"
    ]["cost_normalized_progress"]
    hard_gate_factor = 1.0 if hard_gates and all(hard_gates.values()) else 0.0
    weights = {key: 1 / len(metrics["rfde_profile"]) for key in metrics["rfde_profile"]}
    metrics["aggregate"] = {
        "ungated_rfde_score": clamp01(
            sum(metrics["rfde_profile"][key] * weights[key] for key in weights)
        ),
        "gated_rfde_score": 0.0,
        "hard_gate_factor": hard_gate_factor,
    }
    metrics["aggregate"]["gated_rfde_score"] = clamp01(
        metrics["aggregate"]["ungated_rfde_score"] * hard_gate_factor
    )


def detect_diagnostics(
    evidence: Dict[str, Any],
    metrics: Dict[str, Any],
    cost: Dict[str, Any],
    trajectory_model: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Document the responsibility of ``detect_diagnostics``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``detect_diagnostics`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    diagnostics: List[Dict[str, Any]] = []
    rfde = metrics["rfde_profile"]
    mathformer = metrics["mathformer_profile"]

    def add(
        kind: str, severity: str, message: str, evidence_payload: Dict[str, Any]
    ) -> None:
        """Document the responsibility of ``detect_diagnostics.add``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Provide the local operation named ``detect_diagnostics.add`` while preserving the surrounding module contract.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        diagnostics.append(
            {
                "kind": kind,
                "severity": severity,
                "message": message,
                "evidence": evidence_payload,
            }
        )

    if mathformer["mathlib_grounding"] < 0.55:
        add(
            "mathlib_grounding_gap",
            "medium",
            "Mathlib grounding is a weak surface.",
            {"score": mathformer["mathlib_grounding"]},
        )
    if mathformer["source_anchor_coverage"] < 0.85:
        add(
            "source_anchor_drift_risk",
            "high",
            "Source-anchor coverage is below the acceptance threshold.",
            {"score": mathformer["source_anchor_coverage"]},
        )
    if mathformer["realness"] < 1.0:
        add(
            "realness_blocker",
            "high",
            "Placeholders, axioms, or mock markers remain.",
            {"score": mathformer["realness"]},
        )
    if rfde["workflow_evidence"] < 0.5:
        add(
            "weak_workflow_evidence",
            "medium",
            "Few audit artifacts were provided to RFDE.",
            {"score": rfde["workflow_evidence"]},
        )
    if (
        rfde["obligation_closure"] >= 0.8
        and mathformer["source_anchor_coverage"] >= 0.85
    ):
        add(
            "obligation_closure",
            "info",
            "Obligation and source-anchor surfaces are mostly closed.",
            {"obligation_closure": rfde["obligation_closure"]},
        )
    if cost["normalized_cost"] > 100 and rfde["cost_discipline"] < 0.5:
        add(
            "costly_cycling_risk",
            "medium",
            "Observed cost is high relative to available evidence.",
            cost,
        )
    if trajectory_model is not None:
        trajectory_summary = trajectory_model.get("summary", {})
        if float(trajectory_summary.get("trajectory_observability") or 0.0) < 0.55:
            add(
                "trajectory_underinstrumented",
                "medium",
                "The report can model states and transitions, but the run should log more phase, timing, or metric evidence.",
                trajectory_summary,
            )
        for dynamic in trajectory_model.get("dynamics", []):
            if dynamic.get("severity") in {"high", "medium"}:
                add(
                    str(dynamic.get("predicate")),
                    str(dynamic.get("severity")),
                    str(dynamic.get("interpretation")),
                    dict(dynamic.get("evidence") or {}),
                )
    if not diagnostics:
        add(
            "stable_reference_free_profile",
            "info",
            "No high-risk RFDE diagnostic was triggered.",
            {},
        )
    return diagnostics


def build_timeseries(
    evidence: Dict[str, Any],
    metrics: Dict[str, Any],
    cost: Dict[str, Any],
    trajectory_model: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Document the responsibility of ``build_timeseries``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    points: List[Dict[str, Any]] = []
    cumulative_ms = 0.0
    for item in evidence["reasoning_trace"]["trajectory"]:
        elapsed = item.get("elapsed_ms_since_prev_event")
        if isinstance(elapsed, (int, float)) and elapsed >= 0:
            cumulative_ms += float(elapsed)
        points.append(
            {
                "event_index": item.get("event_index"),
                "step": item.get("step"),
                "hook_id": item.get("hook_id"),
                "skill": item.get("skill"),
                "elapsed_ms_cumulative": round(cumulative_ms, 3),
            }
        )
    points.append(
        {
            "event_index": "final",
            "step": "rfde_final_metrics",
            "hook_id": HOOK_ID,
            "skill": SKILL_NAME,
            "elapsed_ms_cumulative": round(cumulative_ms, 3),
            "rfde_profile": metrics["rfde_profile"],
            "mathformer_profile": metrics["mathformer_profile"],
            "cost": cost,
            "trajectory_profile": metrics.get("trajectory_profile", {}),
        }
    )
    result: Dict[str, Any] = {"schema_version": 2, "points": points}
    if trajectory_model is not None:
        result["state_timeseries"] = [
            {
                "state_id": state.get("state_id"),
                "after_event_index": state.get("after_event_index"),
                "phase": state.get("phase"),
                "cumulative_ms": state.get("cumulative_ms"),
                "observed_metric_count": len(state.get("observed_metrics", {})),
            }
            for state in trajectory_model.get("states", [])
        ]
        result["transition_timeseries"] = [
            {
                "transition_id": transition.get("transition_id"),
                "from_state": transition.get("from_state"),
                "to_state": transition.get("to_state"),
                "phase": transition.get("phase"),
                "duration_ms": transition.get("duration_ms"),
                "positive_movement": transition.get("positive_movement"),
                "regression_movement": transition.get("regression_movement"),
                "cost_normalized_progress": transition.get("cost_normalized_progress"),
            }
            for transition in trajectory_model.get("transitions", [])
        ]
        result["phase_transition_timeseries"] = [
            {
                "phase_transition_id": item.get("phase_transition_id"),
                "from_phase": item.get("from_phase"),
                "to_phase": item.get("to_phase"),
                "kind": item.get("kind"),
                "trigger_event_index": item.get("trigger_event_index"),
                "trigger_cumulative_ms": item.get("trigger_cumulative_ms"),
                "transition_confidence": item.get("transition_confidence"),
                "irreversibility_pressure": item.get("irreversibility_pressure"),
                "healthy": item.get("healthy"),
            }
            for item in trajectory_model.get("phase_transitions", [])
        ]
        result["cycle_statistics"] = trajectory_model.get("cycle_statistics", [])
        result["trajectory_summary"] = trajectory_model.get("summary", {})
    return result


def raw_number(value: Any, default: float = 0.0) -> float:
    """Document the responsibility of ``raw_number``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``raw_number`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return default


def normalized_score(value: Any, default: float = 0.0) -> float:
    """Document the responsibility of ``normalized_score``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalized_score`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if not isinstance(value, (int, float)):
        return default
    numeric = float(value)
    if 1.0 < numeric <= 100.0:
        return clamp01(numeric / 100.0)
    return clamp01(numeric)


def action_pass_value(action: Dict[str, Any]) -> Optional[bool]:
    """Document the responsibility of ``action_pass_value``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``action_pass_value`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    payload = (
        action.get("payload_summary", {})
        if isinstance(action.get("payload_summary"), dict)
        else {}
    )
    summary = (
        payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    )
    criteria = (
        payload.get("convergence_criteria", {})
        if isinstance(payload.get("convergence_criteria"), dict)
        else {}
    )
    evidence = (
        criteria.get("current_evidence", {})
        if isinstance(criteria.get("current_evidence"), dict)
        else {}
    )
    for item in (payload.get("ok"), summary.get("ok"), evidence.get("ok")):
        if isinstance(item, bool):
            return item
    if isinstance(payload.get("blocking_finding_count"), int):
        return int(payload.get("blocking_finding_count") or 0) == 0
    if isinstance(summary.get("blocking_finding_count"), int):
        return int(summary.get("blocking_finding_count") or 0) == 0
    return None


def action_count_value(action: Dict[str, Any], key: str) -> int:
    """Document the responsibility of ``action_count_value``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``action_count_value`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    payload = (
        action.get("payload_summary", {})
        if isinstance(action.get("payload_summary"), dict)
        else {}
    )
    summary = (
        payload.get("summary", {}) if isinstance(payload.get("summary"), dict) else {}
    )
    if isinstance(payload.get(key), int):
        return int(payload.get(key) or 0)
    if isinstance(summary.get(key), int):
        return int(summary.get(key) or 0)
    criteria = (
        payload.get("convergence_criteria", {})
        if isinstance(payload.get("convergence_criteria"), dict)
        else {}
    )
    evidence = (
        criteria.get("current_evidence", {})
        if isinstance(criteria.get("current_evidence"), dict)
        else {}
    )
    if isinstance(evidence.get(key), int):
        return int(evidence.get(key) or 0)
    return 0


def build_parallel_plot_surfaces(
    evidence: Dict[str, Any],
    metrics: Dict[str, Any],
    trajectory_model: Dict[str, Any],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_parallel_plot_surfaces``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lean = dict(evidence.get("lean_summary", {}))
    anchors = anchor_summary(evidence.get("anchor_reports", []), lean)
    imports: List[str] = []
    mathlib_imports: List[str] = []
    previous_library_imports: List[str] = []
    external_library_imports: List[str] = []
    for item in evidence.get("lean_file_stats", []):
        imports.extend(str(name) for name in item.get("imports", []))
        mathlib_imports.extend(str(name) for name in item.get("mathlib_imports", []))
        previous_library_imports.extend(
            str(name) for name in item.get("previous_library_imports", [])
        )
        external_library_imports.extend(
            str(name) for name in item.get("external_library_imports", [])
        )
    unique_mathlib_imports = sorted(set(mathlib_imports))
    unique_previous_imports = sorted(set(previous_library_imports))
    unique_external_imports = sorted(set(external_library_imports))
    previous_library_concept_count = len(unique_previous_imports)
    mathlib_concept_count = int(lean.get("mathlib_native_token_count") or 0) + len(
        unique_mathlib_imports
    )
    event_points: List[Dict[str, Any]] = []
    for action in trajectory_model.get("actions", []):
        payload = (
            action.get("payload_summary", {})
            if isinstance(action.get("payload_summary"), dict)
            else {}
        )
        summary = (
            payload.get("summary", {})
            if isinstance(payload.get("summary"), dict)
            else {}
        )
        score_candidates = (
            payload.get("score_candidates")
            if isinstance(payload.get("score_candidates"), list)
            else []
        )
        compatibility_score = summary.get(
            "min_compatibility_score", summary.get("compatibility_score")
        )
        reference_free_score = summary.get("reference_free_confidence_score")
        event_points.append(
            {
                "event_index": action.get("event_index"),
                "cumulative_ms": action.get("end_cumulative_ms"),
                "phase": action.get("phase"),
                "step": action.get("step"),
                "hook_id": action.get("hook_id"),
                "layer_id": payload.get("id"),
                "gate_pass": action_pass_value(action),
                "finding_count": action_count_value(action, "finding_count"),
                "blocking_finding_count": action_count_value(
                    action, "blocking_finding_count"
                ),
                "formal_code_line_count": int(
                    lean.get("formal_code_line_count") or lean.get("line_count") or 0
                ),
                "total_line_count": int(lean.get("line_count") or 0),
                "declaration_count": int(lean.get("declaration_count") or 0),
                "theorem_like_count": int(lean.get("theorem_like_count") or 0),
                "source_anchor_coverage": anchors["coverage"],
                "mathlib_grounding_score": metrics.get("mathformer_profile", {}).get(
                    "mathlib_grounding", 0.0
                ),
                "compatibility_score": normalized_score(
                    compatibility_score,
                    default=metrics.get("mathformer_profile", {}).get(
                        "mathlib_grounding", 0.0
                    ),
                ),
                "reference_free_confidence_score": normalized_score(
                    reference_free_score, default=0.0
                ),
                "score_candidate": (
                    normalized_score(score_candidates[0], default=0.0)
                    if score_candidates
                    else 0.0
                ),
                "mathlib_native_token_count": int(
                    lean.get("mathlib_native_token_count") or 0
                ),
                "previous_library_concept_count": previous_library_concept_count,
                "mathlib_concept_count": mathlib_concept_count,
                "narrow_mathlib_import_count": int(
                    lean.get("narrow_mathlib_import_count") or 0
                ),
                "broad_mathlib_import_count": int(
                    lean.get("broad_mathlib_import_count") or 0
                ),
            }
        )
    gate_layers: List[Dict[str, Any]] = []
    for report_index, report in enumerate(
        evidence.get("consistency_reports", []), start=1
    ):
        for layer in report.get("layers", []):
            if not isinstance(layer, dict):
                continue
            gate_layers.append(
                {
                    "report_index": report_index,
                    "layer_id": layer.get("id"),
                    "ok": layer.get("ok"),
                    "finding_count": layer.get("finding_count", 0),
                    "blocking_finding_count": layer.get("blocking_finding_count", 0),
                    "score_candidates": layer.get("score_candidates", []),
                    "summary": layer.get("summary", {}),
                }
            )
    return {
        "schema_version": 1,
        "formal_code": {
            "line_count": int(lean.get("line_count") or 0),
            "formal_code_line_count": int(
                lean.get("formal_code_line_count") or lean.get("line_count") or 0
            ),
            "comment_line_count": int(lean.get("comment_line_count") or 0),
            "blank_line_count": int(lean.get("blank_line_count") or 0),
            "declaration_count": int(lean.get("declaration_count") or 0),
            "theorem_like_count": int(lean.get("theorem_like_count") or 0),
            "semantic_comment_count": int(lean.get("semantic_comment_count") or 0),
        },
        "library_grounding": {
            "mathlib_grounding_score": metrics.get("mathformer_profile", {}).get(
                "mathlib_grounding", 0.0
            ),
            "mathlib_native_token_count": int(
                lean.get("mathlib_native_token_count") or 0
            ),
            "narrow_mathlib_import_count": int(
                lean.get("narrow_mathlib_import_count") or 0
            ),
            "broad_mathlib_import_count": int(
                lean.get("broad_mathlib_import_count") or 0
            ),
            "mathlib_imports": unique_mathlib_imports,
            "previous_library_imports": unique_previous_imports,
            "external_library_imports": unique_external_imports,
            "mathlib_concept_count": mathlib_concept_count,
            "previous_library_concept_count": previous_library_concept_count,
        },
        "anchor_surface": {
            "coverage": anchors["coverage"],
            "validity": anchors["validity"],
            "report_count": anchors["report_count"],
            "orphan_anchor_count": anchors["orphan_anchor_count"],
        },
        "gate_layers": gate_layers,
        "event_points": event_points,
    }


def build_trajectory_interpretation(
    *,
    evidence: Dict[str, Any],
    metrics: Dict[str, Any],
    hard_gates: Dict[str, bool],
    trajectory_model: Dict[str, Any],
    parallel_plot_surfaces: Dict[str, Any],
) -> Dict[str, Any]:
    """Document the responsibility of ``build_trajectory_interpretation``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    actions = trajectory_model.get("actions", [])
    anchor_checks: List[Dict[str, Any]] = []
    for action in actions:
        if action.get("step") != "source_anchor_drift_guard_complete":
            continue
        measurements = (
            action.get("measurements", {})
            if isinstance(action.get("measurements"), dict)
            else {}
        )
        coverage = measurements.get("anchor_coverage")
        minimum = measurements.get("min_anchor_coverage")
        coverage_value = float(coverage) if isinstance(coverage, (int, float)) else 0.0
        anchor_checks.append(
            {
                "event_index": action.get("event_index"),
                "coverage": coverage,
                "minimum": minimum,
                "result": "pass" if coverage_value >= 0.85 else "diagnostic",
                "interpretation": (
                    "Curated mathematical-object anchors were checked."
                    if coverage_value >= 0.85
                    else "Raw or broad source anchors were checked; useful as drift signal, but not sufficient for final source-coverage acceptance."
                ),
            }
        )

    consistency_runs: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    for action in actions:
        step = action.get("step")
        payload = (
            action.get("payload_summary", {})
            if isinstance(action.get("payload_summary"), dict)
            else {}
        )
        if step == "lean_consistency_report_start":
            current = {
                "start_event_index": action.get("event_index"),
                "end_event_index": None,
                "layers": [],
                "failed_layers": [],
                "finding_count": 0,
                "blocking_finding_count": 0,
            }
            continue
        if current is None:
            continue
        if step == "lean_consistency_report_layer_complete":
            layer_id = payload.get("id") or "unknown_layer"
            layer = {
                "layer_id": layer_id,
                "ok": payload.get("ok"),
                "finding_count": action_count_value(action, "finding_count"),
                "blocking_finding_count": action_count_value(
                    action, "blocking_finding_count"
                ),
            }
            current["layers"].append(layer)
            if payload.get("ok") is False:
                current["failed_layers"].append(layer)
        elif step == "lean_consistency_report_complete":
            current["end_event_index"] = action.get("event_index")
            current["finding_count"] = action_count_value(action, "finding_count")
            current["blocking_finding_count"] = action_count_value(
                action, "blocking_finding_count"
            )
            current["result"] = (
                "pass"
                if current["blocking_finding_count"] == 0
                and not current["failed_layers"]
                else "repair_needed"
            )
            consistency_runs.append(current)
            current = None

    episode_candidates: List[Dict[str, Any]] = []
    for anchor in anchor_checks:
        coverage_value = float(anchor.get("coverage") or 0.0)
        episode_candidates.append(
            {
                "sort_event": anchor.get("event_index") or 0,
                "name": (
                    "Curated mathematical-source anchor check"
                    if coverage_value >= 0.85
                    else "Broad source-anchor diagnostic"
                ),
                "events": str(anchor.get("event_index")),
                "result": anchor.get("result"),
                "headline_metric": f"anchor coverage {coverage_value:.4f}",
                "interpretation": anchor.get("interpretation"),
            }
        )
    for index, run in enumerate(consistency_runs, start=1):
        failed = [str(layer.get("layer_id")) for layer in run.get("failed_layers", [])]
        candidate = {
            "sort_event": run.get("start_event_index") or 0,
            "name": f"Consistency pass {index}",
            "events": f"{run.get('start_event_index')}-{run.get('end_event_index')}",
            "result": run.get("result"),
            "headline_metric": f"{run.get('blocking_finding_count', 0)} blocking / {run.get('finding_count', 0)} total findings",
            "failed_layers": failed,
            "interpretation": (
                "All required consistency layers passed."
                if run.get("result") == "pass"
                else "The artifact was executable enough to inspect, but critics identified repair targets: "
                + (", ".join(failed) if failed else "blocking findings")
                + "."
            ),
        }
        if index == 1 and run.get("result") != "pass":
            candidate["repair_hint"] = (
                "The subsequent pass improved source/signature wording and mathlib-grounding evidence."
            )
        episode_candidates.append(candidate)
    for action in actions:
        if action.get("step") != "physics_lean_consistency_report_complete":
            continue
        measurements = (
            action.get("measurements", {})
            if isinstance(action.get("measurements"), dict)
            else {}
        )
        episode_candidates.append(
            {
                "sort_event": action.get("event_index") or 0,
                "name": "Physics Lean consistency consolidation",
                "events": str(action.get("event_index")),
                "result": "reported",
                "headline_metric": (
                    f"{len(measurements)} reported measurements"
                    if measurements
                    else "execution, unit, critic, and final-review artifacts linked"
                ),
                "interpretation": (
                    "The run joined the Lean candidate with execution interpretation, unit checks, dimension criticism, "
                    "assumption criticism, physical-semantics criticism, and final mathematical/physics reviews."
                ),
            }
        )

    episodes: List[Dict[str, Any]] = []
    for index, candidate in enumerate(
        sorted(episode_candidates, key=lambda item: int(item.get("sort_event") or 0)),
        start=1,
    ):
        episode = {
            key: value for key, value in candidate.items() if key != "sort_event"
        }
        episode["episode_id"] = f"ep_{index:03d}"
        episodes.append(episode)

    failed_criteria = [name for name, passed in hard_gates.items() if not passed]
    terminal_status = "complete" if not failed_criteria else "draft"
    trajectory_summary = (
        trajectory_model.get("summary", {})
        if isinstance(trajectory_model.get("summary"), dict)
        else {}
    )
    phase_segments = (
        trajectory_model.get("phase_segments", [])
        if isinstance(trajectory_model.get("phase_segments"), list)
        else []
    )
    phase_transitions = (
        trajectory_model.get("phase_transitions", [])
        if isinstance(trajectory_model.get("phase_transitions"), list)
        else []
    )
    cycle_statistics = (
        trajectory_model.get("cycle_statistics", [])
        if isinstance(trajectory_model.get("cycle_statistics"), list)
        else []
    )
    phase_sequence: List[str] = []
    family_sequence: List[str] = []
    for segment in phase_segments:
        if not isinstance(segment, dict):
            continue
        phase = str(segment.get("phase") or "unknown")
        if phase_sequence and phase_sequence[-1] == phase:
            continue
        phase_sequence.append(phase)
        family = phase_family(phase)
        if not family_sequence or family_sequence[-1] != family:
            family_sequence.append(family)
    phase_story_limit = 16
    family_story_limit = 16
    phase_story = " -> ".join(
        label.replace("_", " ") for label in phase_sequence[:phase_story_limit]
    )
    family_story = " -> ".join(
        label.replace("_", " ") for label in family_sequence[:family_story_limit]
    )
    if len(phase_sequence) > phase_story_limit:
        phase_story += " -> ..."
    if len(family_sequence) > family_story_limit:
        family_story += " -> ..."
    healthy_transitions = int(
        trajectory_summary.get("healthy_phase_transition_count")
        or sum(1 for transition in phase_transitions if transition.get("healthy"))
    )
    total_phase_transitions = int(
        trajectory_summary.get("phase_transition_count") or len(phase_transitions)
    )
    failed_criteria_text = (
        ", ".join(item.replace("_", " ") for item in failed_criteria) or "none"
    )
    diagnostics = []
    trajectory_dynamics = trajectory_model.get("dynamics", [])
    for dynamic in trajectory_dynamics:
        predicate = str(dynamic.get("predicate"))
        if predicate == "phase_coverage_gap":
            diagnostics.append(
                {
                    "name": predicate,
                    "meaning": "The log begins after extraction/drafting, so trajectory plots are strongest for postformalization, consistency, and artifact validation criteria.",
                    "impact": "This is an instrumentation limitation, not a Lean correctness failure.",
                }
            )
        elif predicate == "oscillation_candidate":
            diagnostics.append(
                {
                    "name": predicate,
                    "meaning": "Intermediate critics failed and then passed, so some metric signs alternate during repair.",
                    "impact": "Expected for a refinement loop; inspect terminal validation criteria and final blocking counts.",
                }
            )
    if metrics.get("rfde_profile", {}).get("cost_discipline", 1.0) < 0.5:
        diagnostics.append(
            {
                "name": "cost_discipline",
                "meaning": "Observed elapsed time includes manual repair gaps and repeated validation passes.",
                "impact": "Read cost plots as workflow overhead, not as model-token cost.",
            }
        )

    code = parallel_plot_surfaces.get("formal_code", {})
    grounding = parallel_plot_surfaces.get("library_grounding", {})
    anchor = parallel_plot_surfaces.get("anchor_surface", {})
    final_snapshot = {
        "formal_code_line_count": code.get("formal_code_line_count", 0),
        "total_line_count": code.get("line_count", 0),
        "declaration_count": code.get("declaration_count", 0),
        "theorem_like_count": code.get("theorem_like_count", 0),
        "mathlib_grounding_score": grounding.get("mathlib_grounding_score", 0.0),
        "mathlib_import_count": len(grounding.get("mathlib_imports", [])),
        "previous_library_import_count": len(
            grounding.get("previous_library_imports", [])
        ),
        "source_anchor_coverage": anchor.get("coverage", 0.0),
        "blocking_findings_terminal": (
            consistency_runs[-1].get("blocking_finding_count", 0)
            if consistency_runs
            else 0
        ),
        "grounded_fact_count": (
            cycle_statistics[-1].get("grounded_fact_count", 0)
            if cycle_statistics
            else 0
        ),
    }
    plain_language_summary = [
        (
            f"The trace exposes {trajectory_summary.get('state_count', 0)} states, "
            f"{trajectory_summary.get('action_count', 0)} actions, and {total_phase_transitions} phase transitions."
        ),
        (
            f"The detailed phase path is {phase_story}."
            if phase_story
            else "The detailed phase path is not available because the reasoning log did not expose phase-bearing events."
        ),
        (
            f"At the family level, the run moves through {family_story}."
            if family_story
            else "At the family level, the run does not expose enough phase evidence for a transition story."
        ),
        (
            f"{healthy_transitions} of {total_phase_transitions} observed phase transitions are healthy under local evidence."
            if total_phase_transitions
            else "No explicit phase transitions were observed."
        ),
    ]
    if any(
        action.get("step") == "physics_lean_consistency_report_complete"
        for action in actions
    ):
        plain_language_summary.append(
            "The physics Lean consistency consolidation is the main tightening point: it brings together the Lean artifact, execution interpretation, unit checks, critic reports, and final reviews."
        )
    if cycle_statistics:
        terminal_cycle = cycle_statistics[-1]
        plain_language_summary.append(
            "The cycle table tracks the growth curve explicitly: "
            f"{terminal_cycle.get('grounded_fact_count', 0)} grounded evidence facts, "
            f"{terminal_cycle.get('statement_count', 0)} formal statements, and "
            f"{terminal_cycle.get('lean_line_count', 0)} Lean lines by the terminal cycle."
        )
    if failed_criteria:
        plain_language_summary.append(
            f"RFDE keeps the terminal status at draft because these evidence surfaces are still missing or below threshold: {failed_criteria_text}."
        )
    else:
        plain_language_summary.append(
            "All RFDE terminal hard gates pass for this rendered run."
        )
    how_to_read = [
        "Read the phase timeline first: it shows where the run changed epistemic mode, such as from informal expansion to Lean preformalization or from execution to validation.",
        "Use the episode table to find the concrete artifact bundles that explain each tightening step.",
        "In the parallel plots, red validation cells or red blocking bars are evidence pressure; the terminal hard gates explain what still blocks acceptance.",
        "Flat formal-code and grounding lines mean the current log did not capture per-edit Lean snapshots; the report still records the final artifact footprint.",
        "Phase-transition markers show workflow changes, not mathematical theorem dependencies.",
    ]
    return {
        "schema_version": 1,
        "terminal_status": terminal_status,
        "headline": (
            "Terminal validation criteria pass after observed autoformalization tightening."
            if terminal_status == "complete"
            else (
                "The trajectory shows coherent autoformalization tightening, but RFDE remains draft until missing evidence surfaces are attached."
                if set(failed_criteria).issubset({"realness", "anchor"})
                else "Terminal validation criteria do not all pass; inspect failed criteria and open obligations."
            )
        ),
        "plain_language_summary": plain_language_summary,
        "episodes": episodes,
        "how_to_read": how_to_read,
        "warnings_explained": diagnostics,
        "final_snapshot": final_snapshot,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_markdown``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    trajectory_model = report.get("trajectory_model", {})
    trajectory_summary = trajectory_model.get("summary", {})
    lines = [
        f"# RFDE Report: `{report['run_id']}`",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Final status: `{report['final_status']}`",
        f"- Ungated score: `{report['metrics']['aggregate']['ungated_rfde_score']}`",
        f"- Gated score: `{report['metrics']['aggregate']['gated_rfde_score']}`",
        "",
    ]
    interpretation = report.get("trajectory_interpretation", {})
    if interpretation:
        lines.extend(["## How To Read This Run", ""])
        lines.append(str(interpretation.get("headline", "")))
        lines.extend(["", "### Plain-English Story", ""])
        for item in interpretation.get("plain_language_summary", []):
            lines.append(f"- {item}")
        lines.extend(["", "### Episode Overview", ""])
        for episode in interpretation.get("episodes", []):
            failed_layers = (
                ", ".join(f"`{layer}`" for layer in episode.get("failed_layers", []))
                or "none"
            )
            lines.append(
                f"- `{episode.get('episode_id')}` {episode.get('name')} "
                f"(events `{episode.get('events')}`): `{episode.get('result')}`, "
                f"{episode.get('headline_metric')}; failed layers: {failed_layers}. "
                f"{episode.get('interpretation')}"
            )
        lines.extend(["", "### Plot Reading Notes", ""])
        for item in interpretation.get("how_to_read", []):
            lines.append(f"- {item}")
        lines.extend(["", "### Warnings Explained", ""])
        for item in interpretation.get("warnings_explained", []):
            lines.append(
                f"- `{item.get('name')}`: {item.get('meaning')} Impact: {item.get('impact')}"
            )
        lines.append("")
    lines.extend(
        [
            "## Trajectory Model",
            "",
            f"- States: `{trajectory_summary.get('state_count', 0)}`",
            f"- Actions: `{trajectory_summary.get('action_count', 0)}`",
            f"- Transitions: `{trajectory_summary.get('transition_count', 0)}`",
            f"- Phase segments: `{trajectory_summary.get('phase_segment_count', 0)}`",
            f"- Phase transitions: `{trajectory_summary.get('phase_transition_count', 0)}`",
            f"- Loop candidates: `{trajectory_summary.get('loop_candidate_count', 0)}`",
            f"- Trajectory observability: `{trajectory_summary.get('trajectory_observability', 0)}`",
            f"- Phase-transition observability: `{trajectory_summary.get('phase_transition_observability', 0)}`",
            f"- Convergence score: `{trajectory_summary.get('convergence_score', 0)}`",
            f"- Cost-normalized progress: `{trajectory_summary.get('cost_normalized_progress', 0)}`",
            f"- Dominant phase: `{trajectory_summary.get('dominant_phase', 'none')}`",
            "",
            "### Dynamics",
            "",
        ]
    )
    for dynamic in trajectory_model.get("dynamics", []):
        lines.append(
            f"- `{dynamic['severity']}` `{dynamic['predicate']}`: {dynamic['interpretation']}"
        )
    lines.extend(["", "### Phase Segments", ""])
    for segment in trajectory_model.get("phase_segments", []):
        lines.append(
            f"- `{segment['phase']}` events `{segment['start_event_index']}`-`{segment['end_event_index']}`: "
            f"`{segment['event_count']}` actions, `{round(segment['duration_ms'] / 1000.0, 3)}` sec, "
            f"efficiency `{segment['efficiency']}`"
        )
    lines.extend(["", "### Cycle Statistics", ""])
    cycle_statistics = trajectory_model.get("cycle_statistics", [])
    if cycle_statistics:
        lines.append(
            "| Cycle | Phase | Events | New Facts | Facts Total | Statements | Lean Lines | Theorems | Score | Best | Delta | Coverage | Blockers | Pass Rate |"
        )
        lines.append(
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
        )
        for cycle in cycle_statistics:
            score = cycle.get("score")
            delta = cycle.get("score_delta")
            coverage = cycle.get("coverage")
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{cycle.get('cycle_id')}`",
                        f"`{cycle.get('phase')}`",
                        f"`{cycle.get('event_range')}`",
                        str(cycle.get("new_grounded_facts")),
                        str(cycle.get("grounded_fact_count")),
                        str(cycle.get("statement_count")),
                        str(cycle.get("lean_line_count")),
                        str(cycle.get("theorem_count")),
                        (
                            f"{float(score):.3f}"
                            if isinstance(score, (int, float))
                            else "n/a"
                        ),
                        (
                            f"{float(cycle.get('best_score')):.3f}"
                            if isinstance(cycle.get("best_score"), (int, float))
                            else "n/a"
                        ),
                        (
                            f"{float(delta):+.3f}"
                            if isinstance(delta, (int, float))
                            else "n/a"
                        ),
                        (
                            f"{float(coverage):.3f}"
                            if isinstance(coverage, (int, float))
                            else "n/a"
                        ),
                        str(cycle.get("blocking_findings")),
                        str(cycle.get("pass_rate")),
                    ]
                )
                + " |"
            )
    else:
        lines.append("- No cycle statistics were available.")
    lines.extend(["", "### Phase Transitions", ""])
    phase_transitions = trajectory_model.get("phase_transitions", [])
    if phase_transitions:
        for item in phase_transitions[:12]:
            lines.append(
                f"- `{item['phase_transition_id']}` `{item['from_phase']}` -> `{item['to_phase']}` "
                f"at event `{item['trigger_event_index']}`: `{item['kind']}`, "
                f"confidence `{item['transition_confidence']}`, irreversibility `{item['irreversibility_pressure']}`, "
                f"healthy `{item['healthy']}`"
            )
    else:
        lines.append(
            "- No phase transitions were observed in the available reasoning trace."
        )
    lines.extend(["", "### Loop Candidates", ""])
    loops = trajectory_model.get("loop_candidates", [])
    if loops:
        for loop in loops[:12]:
            lines.append(
                f"- `{loop['kind']}` events `{loop['start_event_index']}`-`{loop['end_event_index']}`: "
                f"{loop['interpretation']}"
            )
    else:
        lines.append(
            "- No repeated-hook or critic-repair-validation loop candidates were observed."
        )
    lines.extend(
        [
            "",
            "## Validation Criteria",
            "",
        ]
    )
    for key, value in report["hard_gates"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## RFDE Profile", ""])
    for key, value in report["metrics"]["rfde_profile"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Trajectory Profile", ""])
    for key, value in report["metrics"].get("trajectory_profile", {}).items():
        lines.append(f"- `{key}`: `{value}`")
    surfaces = report.get("parallel_plot_surfaces", {})
    code_surface = surfaces.get("formal_code", {})
    grounding_surface = surfaces.get("library_grounding", {})
    anchor_surface = surfaces.get("anchor_surface", {})
    lines.extend(["", "## Parallel Plot Surfaces", ""])
    lines.append(
        f"- Formal code lines: `{code_surface.get('formal_code_line_count', 0)}`"
    )
    lines.append(f"- Total Lean lines: `{code_surface.get('line_count', 0)}`")
    lines.append(f"- Declarations: `{code_surface.get('declaration_count', 0)}`")
    lines.append(
        f"- Theorem-like declarations: `{code_surface.get('theorem_like_count', 0)}`"
    )
    lines.append(
        f"- Mathlib grounding score: `{grounding_surface.get('mathlib_grounding_score', 0)}`"
    )
    lines.append(
        f"- Mathlib-native token count: `{grounding_surface.get('mathlib_native_token_count', 0)}`"
    )
    lines.append(
        f"- Previous-library imports: `{len(grounding_surface.get('previous_library_imports', []))}`"
    )
    lines.append(f"- Source-anchor coverage: `{anchor_surface.get('coverage', 0)}`")
    lines.extend(["", "## Mathformer Profile", ""])
    for key, value in report["metrics"]["mathformer_profile"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Diagnostics", ""])
    for diag in report["diagnostics"]:
        lines.append(f"- `{diag['severity']}` `{diag['kind']}`: {diag['message']}")
    lines.extend(["", "## Claim Ledger Summary", ""])
    lines.append(f"- Claims: `{len(report['claim_ledger'])}`")
    lines.append(
        f"- Supported claim mass: `{report['claim_ledger_summary']['supported_claim_mass']}`"
    )
    lines.extend(["", "## Obligation Ledger", ""])
    for item in report["obligation_ledger"]:
        lines.append(f"- `{item['status']}` `{item['kind']}`: {item['description']}")
    lines.extend(["", "## Cost", ""])
    for key, value in report["cost"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def bar_html(label: str, value: float) -> str:
    """Document the responsibility of ``bar_html``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``bar_html`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    pct = int(round(clamp01(value) * 100))
    return (
        f'<div class="metric"><div class="metric-label"><span>{html.escape(label)}</span>'
        f'<strong>{pct}%</strong></div><div class="bar"><span style="width:{pct}%"></span></div></div>'
    )


PHASE_COLORS = {
    "intake": "#2563eb",
    "source_intake": "#1d4ed8",
    "preformalization": "#0f766e",
    "informal_elicitation": "#0d9488",
    "informal_expansion": "#14b8a6",
    "preformalization_readiness": "#0f766e",
    "lean_physics_planning": "#047857",
    "lean_physics_preformalization": "#059669",
    "drafting": "#b45309",
    "execution": "#7c3aed",
    "check": "#7c3aed",
    "lean_physics_validation": "#6d28d9",
    "critique": "#be123c",
    "review": "#9f1239",
    "consistency": "#15803d",
    "postformalization": "#0891b2",
    "evaluation": "#4f46e5",
    "reflection": "#9333ea",
    "testing": "#374151",
    "library": "#047857",
    "artifacts": "#64748b",
    "unknown": "#71717a",
}


def phase_color(phase: str) -> str:
    """Document the responsibility of ``phase_color``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``phase_color`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return PHASE_COLORS.get(str(phase), "#71717a")


def scale_time(
    ms: Any, total_ms: float, *, left: float = 70.0, width: float = 1010.0
) -> float:
    """Document the responsibility of ``scale_time``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``scale_time`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    value = float(ms or 0.0)
    if total_ms <= 0:
        return left
    return left + width * max(0.0, min(1.0, value / total_ms))


def action_label(action: Dict[str, Any]) -> str:
    """Document the responsibility of ``action_label``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``action_label`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parts = [
        str(action.get("event_index")),
        str(action.get("phase")),
        str(action.get("action_kind")),
        str(action.get("step")),
    ]
    return " | ".join(part for part in parts if part and part != "None")


def render_trajectory_time_svg(
    trajectory_model: Dict[str, Any], *, width: int = 1180, height: int = 520
) -> str:
    """Document the responsibility of ``render_trajectory_time_svg``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    actions = trajectory_model.get("actions", [])
    transitions = trajectory_model.get("transitions", [])
    states = trajectory_model.get("states", [])
    segments = trajectory_model.get("phase_segments", [])
    phase_transitions = trajectory_model.get("phase_transitions", [])
    loops = trajectory_model.get("loop_candidates", [])
    total_ms = max(
        [float(action.get("end_cumulative_ms") or 0.0) for action in actions]
        + [float(state.get("cumulative_ms") or 0.0) for state in states]
        + [1.0]
    )
    left, timeline_width = 88.0, float(width - 160)
    plot_top, plot_height = 82.0, 328.0
    plot_bottom = plot_top + plot_height
    baseline_y = plot_top + 96.0
    duration_base_y = plot_top + 244.0
    metric_base_y = plot_top + 294.0
    label_stride = max(1, len(actions) // 18)
    svg_parts = [
        f'<svg class="trajectory-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Trajectory over time">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="34" y="34" class="svg-title">RFDE trajectory through time</text>',
        '<text x="34" y="58" class="svg-small">phase bands, validation markers, loop arcs, action nodes, duration bars, and observed metrics share one time axis</text>',
        f'<rect x="{left}" y="{plot_top}" width="{timeline_width}" height="{plot_height}" rx="8" fill="#F8FAFC" stroke="#CBD5E1"/>',
    ]
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = left + timeline_width * frac
        y = plot_top + plot_height * frac
        svg_parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + timeline_width}" y2="{y:.2f}" stroke="#E2E8F0"/>'
        )
        svg_parts.append(
            f'<line x1="{x:.2f}" y1="{plot_top}" x2="{x:.2f}" y2="{plot_bottom}" stroke="#E2E8F0"/>'
        )
    svg_parts.append(
        f'<line x1="{left}" y1="{baseline_y}" x2="{left + timeline_width}" y2="{baseline_y}" stroke="#CBD5E1" stroke-width="1.2"/>'
    )
    for segment in segments:
        start_x = scale_time(
            segment.get("start_cumulative_ms"),
            total_ms,
            left=left,
            width=timeline_width,
        )
        end_x = scale_time(
            segment.get("end_cumulative_ms"), total_ms, left=left, width=timeline_width
        )
        rect_width = max(2.0, end_x - start_x)
        color = phase_color(str(segment.get("phase")))
        svg_parts.append(
            f'<rect x="{start_x:.2f}" y="{plot_top:.2f}" width="{rect_width:.2f}" height="{plot_height:.2f}" fill="{color}" opacity="0.08"/>'
        )
        if rect_width > 54:
            svg_parts.append(
                f'<text x="{start_x + 8:.2f}" y="{plot_top + 22:.2f}" class="svg-small" fill="{color}">{html.escape(str(segment.get("phase")))}</text>'
            )
    for item in phase_transitions[:24]:
        x = scale_time(
            item.get("trigger_cumulative_ms"), total_ms, left=left, width=timeline_width
        )
        color = "#334155" if item.get("healthy") else "#DC2626"
        label = str(item.get("phase_transition_id") or "pt")
        svg_parts.append(
            f'<g><title>{html.escape(str(item.get("interpretation") or label))}</title>'
            f'<line x1="{x:.2f}" y1="{plot_top:.2f}" x2="{x:.2f}" y2="{plot_bottom:.2f}" stroke="{color}" stroke-width="1.1" stroke-dasharray="5 5" opacity="0.72"/>'
            f'<text x="{x + 4:.2f}" y="{plot_top - 9:.2f}" class="svg-tick" fill="{color}">{html.escape(label)}</text></g>'
        )
    for loop_index, loop in enumerate(loops[:10]):
        start_event = loop.get("start_event_index")
        end_event = loop.get("end_event_index")
        start_action = next(
            (action for action in actions if action.get("event_index") == start_event),
            None,
        )
        end_action = next(
            (action for action in actions if action.get("event_index") == end_event),
            None,
        )
        if start_action is None or end_action is None:
            continue
        x1 = scale_time(
            start_action.get("end_cumulative_ms"),
            total_ms,
            left=left,
            width=timeline_width,
        )
        x2 = scale_time(
            end_action.get("end_cumulative_ms"),
            total_ms,
            left=left,
            width=timeline_width,
        )
        if abs(x2 - x1) < 8:
            continue
        arc_height = 38 + 7 * (loop_index % 4)
        svg_parts.append(
            f'<path d="M {x1:.2f} {baseline_y - 14:.2f} C {x1:.2f} {baseline_y - arc_height:.2f}, {x2:.2f} {baseline_y - arc_height:.2f}, {x2:.2f} {baseline_y - 14:.2f}" fill="none" stroke="#7C3AED" stroke-width="1.35" opacity="0.62"/>'
        )
    for transition in transitions:
        x = scale_time(
            transition.get("end_cumulative_ms"),
            total_ms,
            left=left,
            width=timeline_width,
        )
        positive = float(transition.get("positive_movement") or 0.0)
        regression = float(transition.get("regression_movement") or 0.0)
        duration = float(transition.get("duration_ms") or 0.0)
        bar_height = min(92.0, max(4.0, duration / max(1.0, total_ms) * 250.0))
        bar_color = (
            "#047857"
            if positive > regression
            else ("#DC2626" if regression > 0 else "#94A3B8")
        )
        svg_parts.append(
            f'<rect x="{x - 2.5:.2f}" y="{duration_base_y - bar_height:.2f}" width="5" height="{bar_height:.2f}" rx="2.5" fill="{bar_color}" opacity="0.76"/>'
        )
    max_metric_count = max(
        [len(state.get("observed_metrics", {})) for state in states] + [1]
    )
    metric_points = []
    for state in states:
        x = scale_time(
            state.get("cumulative_ms"), total_ms, left=left, width=timeline_width
        )
        y = metric_base_y - 72.0 * len(state.get("observed_metrics", {})) / max(
            1, max_metric_count
        )
        metric_points.append(f"{x:.2f},{y:.2f}")
    if len(metric_points) >= 2:
        svg_parts.append(
            f'<polyline points="{" ".join(metric_points)}" fill="none" stroke="#2563EB" stroke-width="2.6" opacity="0.92"/>'
        )
    for action_index, action in enumerate(actions):
        x = scale_time(
            action.get("end_cumulative_ms"), total_ms, left=left, width=timeline_width
        )
        color = phase_color(str(action.get("phase")))
        radius = 6 if action.get("measurements") else 4
        svg_parts.append(
            f"<g><title>{html.escape(action_label(action))}</title>"
            f'<circle cx="{x:.2f}" cy="{baseline_y}" r="{radius}" fill="{color}" stroke="#ffffff" stroke-width="1.5"/>'
        )
        if action_index % label_stride == 0 or action_index == len(actions) - 1:
            svg_parts.append(
                f'<text x="{x:.2f}" y="{baseline_y + 24:.2f}" text-anchor="middle" class="svg-tick">{html.escape(str(action.get("event_index")))}</text>'
            )
        svg_parts.append("</g>")
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = left + timeline_width * frac
        seconds = total_ms * frac / 1000.0
        svg_parts.append(
            f'<line x1="{x:.2f}" y1="{plot_bottom + 12:.2f}" x2="{x:.2f}" y2="{plot_bottom + 21:.2f}" stroke="#94A3B8"/>'
        )
        svg_parts.append(
            f'<text x="{x:.2f}" y="{plot_bottom + 42:.2f}" text-anchor="middle" class="svg-tick">{seconds:.1f}s</text>'
        )
    svg_parts.extend(
        [
            f'<text x="34" y="{baseline_y + 4:.2f}" class="svg-label">actions</text>',
            f'<text x="34" y="{duration_base_y + 4:.2f}" class="svg-label">duration</text>',
            f'<text x="34" y="{metric_base_y + 4:.2f}" class="svg-label">metrics</text>',
            f'<text x="{left}" y="{plot_bottom + 64:.2f}" class="svg-small">blue = observed metric surface; green/red bars = improvement or regression pressure; purple arcs = repeated refinement loops.</text>',
            "</svg>",
        ]
    )
    return "\n".join(svg_parts)


def render_signal_polyline(
    points: Sequence[Dict[str, Any]],
    *,
    key: str,
    total_ms: float,
    max_value: float,
    left: float,
    width: float,
    y_top: float,
    row_height: float,
    color: str,
) -> str:
    """Document the responsibility of ``render_signal_polyline``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    coords = []
    for point in points:
        value = raw_number(point.get(key), default=0.0)
        x = scale_time(point.get("cumulative_ms"), total_ms, left=left, width=width)
        y = (
            y_top
            + row_height
            - 18.0
            - (row_height - 34.0) * min(1.0, value / max(1.0, max_value))
        )
        coords.append(f"{x:.2f},{y:.2f}")
    if len(coords) < 2:
        return ""
    circles = []
    sample_stride = max(1, (len(points) + 17) // 18)
    for point in points[::sample_stride]:
        value = raw_number(point.get(key), default=0.0)
        x = scale_time(point.get("cumulative_ms"), total_ms, left=left, width=width)
        y = (
            y_top
            + row_height
            - 18.0
            - (row_height - 34.0) * min(1.0, value / max(1.0, max_value))
        )
        title = f"{point.get('event_index')} {key}: {value:g}"
        circles.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="{color}"><title>{html.escape(title)}</title></circle>'
        )
    return (
        f'<polyline points="{" ".join(coords)}" fill="none" stroke="{color}" stroke-width="2.2" opacity="0.92"/>'
        + "".join(circles)
    )


def render_signal_bar_track(
    points: Sequence[Dict[str, Any]],
    *,
    key: str,
    total_ms: float,
    max_value: float,
    left: float,
    width: float,
    y_top: float,
    row_height: float,
    color: str,
) -> str:
    """Document the responsibility of ``render_signal_bar_track``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    bars = []
    bar_width = max(3.0, min(10.0, width / max(1, len(points)) * 0.55))
    for point in points:
        value = raw_number(point.get(key), default=0.0)
        x = scale_time(point.get("cumulative_ms"), total_ms, left=left, width=width)
        h = (row_height - 28.0) * min(1.0, value / max(1.0, max_value))
        y = y_top + row_height - 16.0 - h
        title = f"{point.get('event_index')} {key}: {value:g}"
        opacity = "0.22" if value <= 0 else "0.82"
        bars.append(
            f'<rect x="{x - bar_width/2:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{max(2.0, h):.2f}" '
            f'rx="1.5" fill="{color}" opacity="{opacity}"><title>{html.escape(title)}</title></rect>'
        )
    return "".join(bars)


def render_gate_raster(
    points: Sequence[Dict[str, Any]],
    *,
    total_ms: float,
    left: float,
    width: float,
    y_top: float,
    row_height: float,
) -> str:
    """Document the responsibility of ``render_gate_raster``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    cells = []
    cell_width = max(4.0, min(12.0, width / max(1, len(points)) * 0.7))
    for point in points:
        gate = point.get("gate_pass")
        color = (
            "#047857" if gate is True else ("#DC2626" if gate is False else "#94A3B8")
        )
        x = scale_time(point.get("cumulative_ms"), total_ms, left=left, width=width)
        layer = point.get("layer_id") or point.get("step") or "event"
        title = f"{point.get('event_index')} {layer}: {'pass' if gate is True else 'fail' if gate is False else 'unknown'}"
        cells.append(
            f'<rect x="{x - cell_width/2:.2f}" y="{y_top + 30:.2f}" width="{cell_width:.2f}" height="{row_height - 44:.2f}" '
            f'rx="3" fill="{color}" opacity="0.86"><title>{html.escape(title)}</title></rect>'
        )
    return "".join(cells)


def render_parallel_signal_plots(report: Dict[str, Any], *, width: int = 1180) -> str:
    """Document the responsibility of ``render_parallel_signal_plots``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surfaces = report.get("parallel_plot_surfaces", {})
    points = surfaces.get("event_points", [])
    if not points:
        return '<p class="muted">No event-level plot surfaces were available.</p>'
    total_ms = max(
        [float(point.get("cumulative_ms") or 0.0) for point in points] + [1.0]
    )
    left = 190.0
    plot_width = float(width - 260)
    row_height = 88.0
    top = 78.0
    tracks = [
        {
            "label": "Formal code lines",
            "kind": "line",
            "key": "formal_code_line_count",
            "color": "#2563eb",
            "max": max(
                [raw_number(p.get("formal_code_line_count")) for p in points] + [1.0]
            ),
            "note": "non-comment Lean lines",
        },
        {
            "label": "Library grounding",
            "kind": "line",
            "key": "mathlib_grounding_score",
            "color": "#047857",
            "max": 1.0,
            "note": "mathlib/previous library score",
        },
        {
            "label": "Validation pass/fail",
            "kind": "gate",
            "key": "gate_pass",
            "color": "#047857",
            "max": 1.0,
            "note": "green pass, red fail, gray unknown",
        },
        {
            "label": "Findings",
            "kind": "bar",
            "key": "finding_count",
            "color": "#b45309",
            "max": max([raw_number(p.get("finding_count")) for p in points] + [1.0]),
            "note": "critic finding count",
        },
        {
            "label": "Blocking findings",
            "kind": "bar",
            "key": "blocking_finding_count",
            "color": "#DC2626",
            "max": max(
                [raw_number(p.get("blocking_finding_count")) for p in points] + [1.0]
            ),
            "note": "criterion-blocking findings",
        },
        {
            "label": "Anchor coverage",
            "kind": "line",
            "key": "source_anchor_coverage",
            "color": "#7C3AED",
            "max": 1.0,
            "note": "required source anchors covered",
        },
    ]
    height = int(top + row_height * len(tracks) + 68)
    parts = [
        f'<svg class="parallel-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Parallel autoformalization evidence tracks">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="34" y="34" class="svg-title">Parallel evidence tracks</text>',
        '<text x="34" y="58" class="svg-small">code growth, grounding, validation, critic pressure, and anchor coverage on the same temporal axis</text>',
    ]
    for index, track in enumerate(tracks):
        y = top + index * row_height
        panel_y = y + 8.0
        panel_height = row_height - 20.0
        parts.append(
            f'<rect x="{left}" y="{panel_y:.2f}" width="{plot_width}" height="{panel_height:.2f}" rx="8" fill="#F8FAFC" stroke="#CBD5E1"/>'
        )
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            x = left + plot_width * frac
            parts.append(
                f'<line x1="{x:.2f}" y1="{panel_y:.2f}" x2="{x:.2f}" y2="{panel_y + panel_height:.2f}" stroke="#E2E8F0"/>'
            )
        parts.append(
            f'<line x1="{left}" y1="{y + row_height - 20:.2f}" x2="{left + plot_width}" y2="{y + row_height - 20:.2f}" stroke="#CBD5E1"/>'
        )
        parts.append(
            f'<text x="34" y="{y + 30:.2f}" class="svg-label">{html.escape(track["label"])}</text>'
        )
        parts.append(
            f'<text x="34" y="{y + 50:.2f}" class="svg-tick">{html.escape(track["note"])}</text>'
        )
        parts.append(
            f'<text x="{left - 10:.2f}" y="{y + 26:.2f}" text-anchor="end" class="svg-tick">{html.escape(str(round(float(track["max"]), 3)))}</text>'
        )
        if track["kind"] == "gate":
            parts.append(
                render_gate_raster(
                    points,
                    total_ms=total_ms,
                    left=left,
                    width=plot_width,
                    y_top=y,
                    row_height=row_height,
                )
            )
        elif track["kind"] == "bar":
            parts.append(
                render_signal_bar_track(
                    points,
                    key=str(track["key"]),
                    total_ms=total_ms,
                    max_value=float(track["max"]),
                    left=left,
                    width=plot_width,
                    y_top=y,
                    row_height=row_height,
                    color=str(track["color"]),
                )
            )
        else:
            parts.append(
                render_signal_polyline(
                    points,
                    key=str(track["key"]),
                    total_ms=total_ms,
                    max_value=float(track["max"]),
                    left=left,
                    width=plot_width,
                    y_top=y,
                    row_height=row_height,
                    color=str(track["color"]),
                )
            )
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        x = left + plot_width * frac
        seconds = total_ms * frac / 1000.0
        parts.append(
            f'<line x1="{x:.2f}" y1="{height - 46}" x2="{x:.2f}" y2="{height - 36}" stroke="#94A3B8"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{height - 16}" text-anchor="middle" class="svg-tick">{seconds:.1f}s</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def render_parallel_signal_summary(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_parallel_signal_summary``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    surfaces = report.get("parallel_plot_surfaces", {})
    code = surfaces.get("formal_code", {})
    grounding = surfaces.get("library_grounding", {})
    anchor = surfaces.get("anchor_surface", {})
    imports = grounding.get("mathlib_imports", [])
    previous = grounding.get("previous_library_imports", [])
    cards = [
        ("formal code lines", code.get("formal_code_line_count", 0)),
        ("total lines", code.get("line_count", 0)),
        ("declarations", code.get("declaration_count", 0)),
        ("theorem-like", code.get("theorem_like_count", 0)),
        ("mathlib imports", grounding.get("narrow_mathlib_import_count", 0)),
        ("mathlib tokens", grounding.get("mathlib_native_token_count", 0)),
        ("previous-library imports", len(previous)),
        ("anchor coverage", round(float(anchor.get("coverage") or 0.0), 4)),
    ]
    card_html = "\n".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in cards
    )
    import_rows = [
        "<tr><th>Mathlib modules</th><td>"
        + (
            ", ".join(f"<code>{html.escape(str(name))}</code>" for name in imports)
            or '<span class="muted">none</span>'
        )
        + "</td></tr>",
        "<tr><th>Previous Mathformer modules</th><td>"
        + (
            ", ".join(f"<code>{html.escape(str(name))}</code>" for name in previous)
            or '<span class="muted">none imported directly</span>'
        )
        + "</td></tr>",
    ]
    return f'<div class="grid3">{card_html}</div><table class="signal-summary"><tbody>{"".join(import_rows)}</tbody></table>'


def result_class(result: Any) -> str:
    """Document the responsibility of ``result_class``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``result_class`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = str(result or "observe").replace("_", "-")
    if text in {"pass", "complete", "closed"}:
        return "pass"
    if text in {"repair-needed", "blocked", "fail"}:
        return "fail"
    return "observe"


def presentation_text(value: Any) -> str:
    """Document the responsibility of ``presentation_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``presentation_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = str(value)
    replacements = [
        ("Hard Gates", "Validation Criteria"),
        ("hard gates", "validation criteria"),
        ("Terminal gates", "Terminal validation criteria"),
        ("terminal gates", "terminal validation criteria"),
        ("failed gates", "failed criteria"),
        ("gate cells", "validation cells"),
        ("gate state", "validation state"),
        ("artifact gates", "artifact validation criteria"),
        ("RFDE gates", "RFDE validation criteria"),
        ("Gated score", "Validated score"),
        ("gated score", "validated score"),
        ("Gated:", "Validated:"),
        ("Ungated:", "Raw RFDE:"),
        ("ungated", "raw"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def render_trajectory_interpretation_html(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_trajectory_interpretation_html``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    interpretation = report.get("trajectory_interpretation", {})
    if not interpretation:
        return ""
    summary_items = "".join(
        f"<li>{html.escape(presentation_text(item))}</li>"
        for item in interpretation.get("plain_language_summary", [])
    )
    how_to_read = "".join(
        f"<li>{html.escape(presentation_text(item))}</li>"
        for item in interpretation.get("how_to_read", [])
    )
    episode_rows = []
    for episode in interpretation.get("episodes", []):
        result = str(episode.get("result") or "observe")
        failed_layers = episode.get("failed_layers") or []
        failed_text = ", ".join(
            f"<code>{html.escape(str(layer))}</code>" for layer in failed_layers
        )
        if not failed_text:
            failed_text = '<span class="muted">none</span>'
        extra = episode.get("repair_hint")
        if extra:
            extra_html = (
                f'<div class="muted">{html.escape(presentation_text(extra))}</div>'
            )
        else:
            extra_html = ""
        episode_rows.append(
            "<tr>"
            f"<td>{html.escape(str(episode.get('episode_id')))}</td>"
            f"<td>{html.escape(str(episode.get('name')))}</td>"
            f"<td>{html.escape(str(episode.get('events')))}</td>"
            f'<td><span class="result-badge {result_class(result)}">{html.escape(result.replace("_", " "))}</span></td>'
            f"<td>{html.escape(str(episode.get('headline_metric')))}</td>"
            f"<td>{failed_text}</td>"
            f"<td>{html.escape(presentation_text(episode.get('interpretation')))}{extra_html}</td>"
            "</tr>"
        )
    if not episode_rows:
        episode_rows.append(
            '<tr><td colspan="7">No interpreted episodes were available.</td></tr>'
        )
    warning_rows = []
    for warning in interpretation.get("warnings_explained", []):
        warning_rows.append(
            "<tr>"
            f"<td><code>{html.escape(str(warning.get('name')))}</code></td>"
            f"<td>{html.escape(presentation_text(warning.get('meaning')))}</td>"
            f"<td>{html.escape(presentation_text(warning.get('impact')))}</td>"
            "</tr>"
        )
    if not warning_rows:
        warning_rows.append(
            '<tr><td colspan="3">No interpretation warnings require explanation.</td></tr>'
        )
    snapshot = interpretation.get("final_snapshot", {})
    snapshot_cards = "\n".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in [
            ("formal code lines", snapshot.get("formal_code_line_count", 0)),
            ("declarations", snapshot.get("declaration_count", 0)),
            ("theorem-like", snapshot.get("theorem_like_count", 0)),
            ("anchor coverage", snapshot.get("source_anchor_coverage", 0)),
            ("mathlib imports", snapshot.get("mathlib_import_count", 0)),
            ("grounded facts", snapshot.get("grounded_fact_count", 0)),
            ("terminal blockers", snapshot.get("blocking_findings_terminal", 0)),
        ]
    )
    return f"""
    <section class="panel story-panel">
      <h2>How To Read This Run</h2>
      <p class="lead">{html.escape(presentation_text(interpretation.get('headline', '')))}</p>
      <div class="grid">
        <div>
          <h3>Plain-English Story</h3>
          <ul class="story-list">{summary_items}</ul>
        </div>
        <div>
          <h3>Reading The Plots</h3>
          <ul class="story-list">{how_to_read}</ul>
        </div>
      </div>
      <h3>Final Snapshot</h3>
      <div class="grid3">{snapshot_cards}</div>
      <h3>Episode Overview</h3>
      <table><thead><tr><th>ID</th><th>Episode</th><th>Events</th><th>Result</th><th>Metric</th><th>Failed layers</th><th>Interpretation</th></tr></thead><tbody>{''.join(episode_rows)}</tbody></table>
      <h3>Warnings Explained</h3>
      <table><thead><tr><th>Warning</th><th>Meaning</th><th>Impact</th></tr></thead><tbody>{''.join(warning_rows)}</tbody></table>
    </section>
"""


def heat_color(value: float, *, positive: bool = True) -> str:
    """Document the responsibility of ``heat_color``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``heat_color`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    clamped = max(0.0, min(1.0, abs(value)))
    if clamped == 0:
        return "#F1F5F9"
    if positive:
        return f"rgba(37, 99, 235, {0.16 + 0.70 * clamped:.3f})"
    return f"rgba(220, 38, 38, {0.16 + 0.70 * clamped:.3f})"


def render_transition_heatmap(
    trajectory_model: Dict[str, Any], *, limit: int = 80
) -> str:
    """Document the responsibility of ``render_transition_heatmap``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    transitions = trajectory_model.get("transitions", [])[:limit]
    if not transitions:
        return (
            '<p class="muted">No transitions are available for heatmap rendering.</p>'
        )
    max_duration = max(
        [float(item.get("duration_ms") or 0.0) for item in transitions] + [1.0]
    )
    max_progress = max(
        [
            abs(float(item.get("cost_normalized_progress") or 0.0))
            for item in transitions
        ]
        + [1.0]
    )
    rows = [
        ("duration", lambda t: float(t.get("duration_ms") or 0.0) / max_duration, True),
        ("positive movement", lambda t: float(t.get("positive_movement") or 0.0), True),
        (
            "regression movement",
            lambda t: float(t.get("regression_movement") or 0.0),
            False,
        ),
        (
            "efficiency",
            lambda t: float(t.get("cost_normalized_progress") or 0.0) / max_progress,
            True,
        ),
        (
            "new measures",
            lambda t: min(1.0, float(t.get("new_measure_count") or 0.0) / 8.0),
            True,
        ),
    ]
    header_cells = "".join(
        f"<th>{html.escape(str(t.get('transition_id')))}</th>" for t in transitions
    )
    body_rows = []
    for label, getter, positive in rows:
        cells = []
        for transition in transitions:
            value = getter(transition)
            cells.append(
                f'<td style="background:{heat_color(value, positive=positive)}" title="{html.escape(label)}: {value:.4f}"></td>'
            )
        body_rows.append(f"<tr><th>{html.escape(label)}</th>{''.join(cells)}</tr>")
    return (
        '<div class="heatmap-wrap"><table class="heatmap"><thead><tr><th>surface</th>'
        f"{header_cells}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"
    )


def render_phase_timeline(trajectory_model: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_phase_timeline``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    segments = trajectory_model.get("phase_segments", [])
    total_ms = sum(float(segment.get("duration_ms") or 0.0) for segment in segments)
    if not segments:
        return '<p class="muted">No phase segments were observed.</p>'
    items = []
    for segment in segments:
        width = max(
            8.0, 100.0 * float(segment.get("duration_ms") or 0.0) / max(1.0, total_ms)
        )
        label = f"{segment.get('phase')} ({segment.get('event_count')} actions)"
        items.append(
            f'<div class="phase-slice" style="flex-basis:{width:.2f}%">'
            f"<strong>{html.escape(str(segment.get('phase')))}</strong>"
            f"<span>{html.escape(label)}</span></div>"
        )
    return f'<div class="phase-timeline">{"".join(items)}</div>'


def render_phase_transition_rows(
    trajectory_model: Dict[str, Any], *, limit: int = 24
) -> str:
    """Document the responsibility of ``render_phase_transition_rows``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows = []
    for item in trajectory_model.get("phase_transitions", [])[:limit]:
        regressions = item.get("protected_metric_regressions") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('phase_transition_id')))}</td>"
            f"<td>{html.escape(str(item.get('from_phase')))} -> {html.escape(str(item.get('to_phase')))}</td>"
            f"<td>{html.escape(str(item.get('kind')))}</td>"
            f"<td>{html.escape(str(item.get('trigger_event_index')))}</td>"
            f"<td>{html.escape(str(item.get('transition_confidence')))}</td>"
            f"<td>{html.escape(str(item.get('irreversibility_pressure')))}</td>"
            f"<td>{html.escape(str(item.get('healthy')))}</td>"
            f"<td>{html.escape(json.dumps(regressions, ensure_ascii=False, sort_keys=True))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8">No phase transitions were observed.</td></tr>')
    return "\n".join(rows)


def render_trajectory_transition_rows(
    trajectory_model: Dict[str, Any], *, limit: int = 18
) -> str:
    """Document the responsibility of ``render_trajectory_transition_rows``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rows = []
    for transition in trajectory_model.get("transitions", [])[:limit]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(transition.get('transition_id')))}</td>"
            f"<td>{html.escape(str(transition.get('phase')))}</td>"
            f"<td>{html.escape(str(transition.get('action_kind')))}</td>"
            f"<td>{html.escape(str(transition.get('source_type')))}</td>"
            f"<td>{html.escape(str(transition.get('duration_ms')))}</td>"
            f"<td>{html.escape(str(transition.get('positive_movement')))}</td>"
            f"<td>{html.escape(str(transition.get('regression_movement')))}</td>"
            f"<td>{html.escape(str(transition.get('cost_normalized_progress')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8">No transitions were observed.</td></tr>')
    return "\n".join(rows)


def render_cycle_statistics_rows(
    trajectory_model: Dict[str, Any], *, limit: int = 80
) -> str:
    """Document the responsibility of ``render_cycle_statistics_rows``.

    Motivation:
        Make the reference-free dashboard auditable as a sequence of measurable refinement cycles.

    Intent:
        Render cycle rows showing how grounded facts, formal statements, Lean lines, scores, and
        blockers evolve across phase segments.

    Inputs:
        A trajectory model with ``cycle_statistics``.

    Outputs:
        HTML table rows, with a fallback row when no cycle statistics are available.
    """
    rows = []
    for cycle in trajectory_model.get("cycle_statistics", [])[:limit]:
        score = cycle.get("score")
        score_text = f"{float(score):.3f}" if isinstance(score, (int, float)) else "n/a"
        best_score = cycle.get("best_score")
        best_score_text = (
            f"{float(best_score):.3f}"
            if isinstance(best_score, (int, float))
            else "n/a"
        )
        score_delta = cycle.get("score_delta")
        score_delta_text = (
            f"{float(score_delta):+.3f}"
            if isinstance(score_delta, (int, float))
            else "n/a"
        )
        coverage = cycle.get("coverage")
        coverage_text = (
            f"{float(coverage):.3f}" if isinstance(coverage, (int, float)) else "n/a"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(cycle.get('cycle_id')))}</td>"
            f"<td>{html.escape(str(cycle.get('phase')))}</td>"
            f"<td>{html.escape(str(cycle.get('event_range')))}</td>"
            f"<td>{html.escape(str(cycle.get('action_count')))}</td>"
            f"<td>{html.escape(str(cycle.get('new_grounded_facts')))}</td>"
            f"<td>{html.escape(str(cycle.get('grounded_fact_count')))}</td>"
            f"<td>{html.escape(str(cycle.get('statement_count')))}</td>"
            f"<td>{html.escape(str(cycle.get('lean_line_count')))}</td>"
            f"<td>{html.escape(str(cycle.get('theorem_count')))}</td>"
            f"<td>{html.escape(score_text)}</td>"
            f"<td>{html.escape(best_score_text)}</td>"
            f"<td>{html.escape(score_delta_text)}</td>"
            f"<td>{html.escape(coverage_text)}</td>"
            f"<td>{html.escape(str(cycle.get('blocking_findings')))}</td>"
            f"<td>{html.escape(str(cycle.get('pass_rate')))}</td>"
            f"<td>{html.escape(str(cycle.get('interpretation')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append(
            '<tr><td colspan="16">No cycle statistics were available.</td></tr>'
        )
    return "\n".join(rows)


def render_cycle_evolution_svg(
    trajectory_model: Dict[str, Any], *, width: int = 1180, height: int = 420
) -> str:
    """Document the responsibility of ``render_cycle_evolution_svg``.

    Motivation:
        Show phase transitions as visible growth curves rather than only final scalar scores.

    Intent:
        Plot cumulative grounded facts, formal statements, Lean lines, and validation score across
        cycle statistics using a shared cycle axis.

    Inputs:
        A trajectory model with ``cycle_statistics``.

    Outputs:
        An inline SVG visualization, or explanatory fallback HTML when no cycle data exists.
    """
    cycles = trajectory_model.get("cycle_statistics", [])
    if not cycles:
        return '<p class="muted">No cycle statistics were available for growth plotting.</p>'
    left = 90.0
    right = 34.0
    top = 58.0
    bottom = 76.0
    plot_width = float(width) - left - right
    plot_height = float(height) - top - bottom
    max_grounded = max(
        [raw_number(cycle.get("grounded_fact_count")) for cycle in cycles] + [1.0]
    )
    max_statements = max(
        [raw_number(cycle.get("statement_count")) for cycle in cycles] + [1.0]
    )
    max_lines = max(
        [raw_number(cycle.get("lean_line_count")) for cycle in cycles] + [1.0]
    )
    tracks = [
        ("grounded facts", "grounded_fact_count", max_grounded, "#047857"),
        ("formal statements", "statement_count", max_statements, "#2563eb"),
        ("Lean lines", "lean_line_count", max_lines, "#7c3aed"),
        ("best score", "best_score", 1.0, "#b45309"),
    ]

    def point(index: int, value: float, max_value: float) -> Tuple[float, float]:
        x = left + (plot_width * index / max(1, len(cycles) - 1))
        y = (
            top
            + plot_height
            - (plot_height * max(0.0, min(1.0, value / max(1.0, max_value))))
        )
        return x, y

    parts = [
        f'<svg class="cycle-svg" viewBox="0 0 {width} {height}" role="img" aria-label="Cycle statistics growth curves">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<text x="34" y="32" class="svg-title">Cycle growth and phase transitions</text>',
        '<text x="34" y="52" class="svg-small">cumulative grounded evidence, formal statements, Lean lines, and score across refinement cycles</text>',
        f'<rect x="{left}" y="{top}" width="{plot_width}" height="{plot_height}" fill="#F8FAFC" stroke="#CBD5E1" rx="8"/>',
    ]
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + plot_height * frac
        parts.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + plot_width}" y2="{y:.2f}" stroke="#E2E8F0"/>'
        )
    for index, cycle in enumerate(cycles):
        x = left + (plot_width * index / max(1, len(cycles) - 1))
        parts.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#E2E8F0"/>'
        )
        parts.append(
            f'<text x="{x:.2f}" y="{height - 36}" text-anchor="middle" class="svg-tick">{html.escape(str(cycle.get("cycle_id", ""))[-3:])}</text>'
        )
        phase = str(cycle.get("phase") or "")
        parts.append(
            f'<text x="{x:.2f}" y="{height - 20}" text-anchor="middle" class="svg-tick">{html.escape(phase.replace("_", " ")[:15])}</text>'
        )
    legend_x = left
    for offset, (label, _key, _max_value, color) in enumerate(tracks):
        x = legend_x + offset * 210
        parts.append(f'<circle cx="{x}" cy="{height - 58}" r="5" fill="{color}"/>')
        parts.append(
            f'<text x="{x + 10}" y="{height - 54}" class="svg-small">{html.escape(label)}</text>'
        )
    for label, key, max_value, color in tracks:
        points = []
        for index, cycle in enumerate(cycles):
            value = raw_number(cycle.get(key))
            x, y = point(index, value, max_value)
            points.append((x, y, value))
        if len(points) == 1:
            x, y, value = points[0]
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}"><title>{html.escape(label)}: {value:.4f}</title></circle>'
            )
            continue
        polyline = " ".join(f"{x:.2f},{y:.2f}" for x, y, _value in points)
        parts.append(
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2.4"/>'
        )
        for x, y, value in points:
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}"><title>{html.escape(label)}: {value:.4f}</title></circle>'
            )
    parts.append(
        f'<text x="{left - 12}" y="{top + 6}" text-anchor="end" class="svg-tick">max</text>'
    )
    parts.append(
        f'<text x="{left - 12}" y="{top + plot_height}" text-anchor="end" class="svg-tick">0</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def render_html(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_html``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    rfde_bars = "\n".join(
        bar_html(key.replace("_", " "), value)
        for key, value in report["metrics"]["rfde_profile"].items()
    )
    math_bars = "\n".join(
        bar_html(key.replace("_", " "), value)
        for key, value in report["metrics"]["mathformer_profile"].items()
    )
    trajectory_bars = "\n".join(
        bar_html(key.replace("_", " "), value)
        for key, value in report["metrics"].get("trajectory_profile", {}).items()
    )
    trajectory_model = report.get("trajectory_model", {})
    trajectory_summary = trajectory_model.get("summary", {})
    trajectory_cards = "\n".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in [
            ("states", trajectory_summary.get("state_count", 0)),
            ("actions", trajectory_summary.get("action_count", 0)),
            ("transitions", trajectory_summary.get("transition_count", 0)),
            ("phase transitions", trajectory_summary.get("phase_transition_count", 0)),
            (
                "PT observability",
                trajectory_summary.get("phase_transition_observability", 0),
            ),
            ("loops", trajectory_summary.get("loop_candidate_count", 0)),
            ("dominant phase", trajectory_summary.get("dominant_phase", "none")),
            (
                "cost-normalized progress",
                trajectory_summary.get("cost_normalized_progress", 0),
            ),
        ]
    )
    dynamics_rows = "\n".join(
        f"<tr><td>{html.escape(d['severity'])}</td><td>{html.escape(d['predicate'])}</td><td>{html.escape(d['interpretation'])}</td></tr>"
        for d in trajectory_model.get("dynamics", [])
    )
    gate_cards = "\n".join(
        f'<div class="gate {"pass" if value else "fail"}"><span>{html.escape(key)}</span><strong>{value}</strong></div>'
        for key, value in report["hard_gates"].items()
    )
    diag_rows = "\n".join(
        f"<tr><td>{html.escape(d['severity'])}</td><td>{html.escape(d['kind'])}</td><td>{html.escape(d['message'])}</td></tr>"
        for d in report["diagnostics"]
    )
    obligation_rows = "\n".join(
        f"<tr><td>{html.escape(o['status'])}</td><td>{html.escape(o['kind'])}</td><td>{html.escape(o['description'])}</td></tr>"
        for o in report["obligation_ledger"]
    )
    return render_dashboard_document(
        report,
        title="RFDE Dashboard",
        body=f"""
    {render_trajectory_interpretation_html(report)}
    <section class="panel">
      <h2>Trajectory Model</h2>
      <div class="grid3">{trajectory_cards}</div>
      {render_phase_timeline(trajectory_model)}
    </section>
    <section class="panel">
      <h2>Trajectory Through Time</h2>
      {render_trajectory_time_svg(trajectory_model)}
    </section>
    <section class="panel">
      <h2>Cycle Statistics</h2>
      <p class="muted">Each row is a refinement cycle derived from an observed phase segment. Counts are reference-free evidence proxies drawn from the run log and final artifacts.</p>
      {render_cycle_evolution_svg(trajectory_model)}
      <table class="cycle-table"><thead><tr><th>Cycle</th><th>Phase</th><th>Events</th><th>Actions</th><th>New facts</th><th>Facts total</th><th>Statements</th><th>Lean lines</th><th>Theorems</th><th>Score</th><th>Best</th><th>Delta</th><th>Coverage</th><th>Blockers</th><th>Pass rate</th><th>Interpretation</th></tr></thead><tbody>{render_cycle_statistics_rows(trajectory_model)}</tbody></table>
    </section>
    <section class="panel">
      <h2>Parallel Evidence Tracks</h2>
      {render_parallel_signal_summary(report)}
      {render_parallel_signal_plots(report)}
    </section>
    <section class="grid">
      <div class="panel"><h2>Trajectory Profile</h2>{trajectory_bars}</div>
      <div class="panel">
        <h2>Dynamics Predicates</h2>
        <table><thead><tr><th>Severity</th><th>Predicate</th><th>Interpretation</th></tr></thead><tbody>{dynamics_rows}</tbody></table>
      </div>
    </section>
    <section class="panel">
      <h2>Transition Heatmap</h2>
      {render_transition_heatmap(trajectory_model)}
    </section>
    <section class="panel">
      <h2>Phase Transitions</h2>
      <table><thead><tr><th>ID</th><th>Phase Shift</th><th>Kind</th><th>Event</th><th>Confidence</th><th>Irreversibility</th><th>Healthy</th><th>Protected Regressions</th></tr></thead><tbody>{render_phase_transition_rows(trajectory_model)}</tbody></table>
    </section>
    <section class="panel">
      <h2>Transitions</h2>
      <table><thead><tr><th>ID</th><th>Phase</th><th>Action</th><th>Source</th><th>ms</th><th>+</th><th>-</th><th>Efficiency</th></tr></thead><tbody>{render_trajectory_transition_rows(trajectory_model)}</tbody></table>
    </section>
    <section class="panel">
      <h2>Validation Criteria</h2>
      <div class="gates">{gate_cards}</div>
    </section>
    <section class="grid">
      <div class="panel"><h2>RFDE Profile</h2>{rfde_bars}</div>
      <div class="panel"><h2>Mathformer Profile</h2>{math_bars}</div>
    </section>
    <section class="panel">
      <h2>Diagnostics</h2>
      <table><thead><tr><th>Severity</th><th>Kind</th><th>Message</th></tr></thead><tbody>{diag_rows}</tbody></table>
    </section>
    <section class="panel">
      <h2>Obligation Ledger</h2>
      <table><thead><tr><th>Status</th><th>Kind</th><th>Description</th></tr></thead><tbody>{obligation_rows}</tbody></table>
    </section>
    <section class="panel">
      <h2>Cost</h2>
      <pre>{html.escape(json.dumps(report['cost'], indent=2, sort_keys=True))}</pre>
    </section>
""",
    )


def render_dashboard_document(report: Dict[str, Any], *, title: str, body: str) -> str:
    """Document the responsibility of ``render_dashboard_document``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} - {html.escape(report['run_id'])}</title>
  <style>
    body {{ margin: 0; background: #ffffff; color: #0f172a; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.5; }}
    header, main {{ width: min(1180px, calc(100vw - 32px)); margin: 0 auto; }}
    header {{ padding: 30px 0 18px; border-bottom: 1px solid #CBD5E1; }}
    h1 {{ margin: 0; font-size: clamp(1.75rem, 3vw, 2.35rem); letter-spacing: 0; color: #0f172a; }}
    h2 {{ color: #0f172a; letter-spacing: 0; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .pill {{ border: 1px solid #CBD5E1; background: #F8FAFC; border-radius: 999px; padding: 5px 10px; color: #475569; font-size: 0.88rem; }}
    main {{ padding: 24px 0 48px; }}
    section {{ margin: 0 0 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .grid3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .panel {{ background: #fff; border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px; min-width: 0; }}
    .lead {{ font-size: 1.05rem; margin-top: 0; color: #334155; }}
    h3 {{ margin: 18px 0 8px; font-size: 1rem; }}
    .story-list {{ margin: 8px 0 0; padding-left: 20px; }}
    .story-list li {{ margin: 6px 0; }}
    .result-badge {{ display: inline-block; border-radius: 999px; padding: 3px 8px; font-size: 0.82rem; border: 1px solid #CBD5E1; background: #F8FAFC; }}
    .result-badge.pass {{ color: #047857; border-color: #86efac; background: #F0FDF4; }}
    .result-badge.fail {{ color: #DC2626; border-color: #FCA5A5; background: #FEF2F2; }}
    .result-badge.observe {{ color: #475569; border-color: #CBD5E1; background: #F8FAFC; }}
    .stat {{ border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px; background: #F8FAFC; }}
    .stat span {{ display: block; color: #64748B; font-size: 0.82rem; }}
    .stat strong {{ display: block; font-size: 1.1rem; color: #0f172a; overflow-wrap: anywhere; }}
    .metric {{ margin: 10px 0; }}
    .metric-label {{ display: flex; justify-content: space-between; gap: 10px; font-size: 0.9rem; }}
    .bar {{ height: 9px; background: #E2E8F0; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; background: #2563EB; }}
    .gates {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }}
    .gate {{ border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px; background: #F8FAFC; }}
    .gate.pass strong {{ color: #047857; }}
    .gate.fail strong {{ color: #DC2626; }}
    .gate span {{ display: block; color: #64748B; font-size: 0.84rem; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #CBD5E1; border-radius: 8px; overflow: hidden; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid #E2E8F0; text-align: left; vertical-align: top; }}
    th {{ background: #F8FAFC; color: #334155; }}
    .muted {{ color: #64748B; }}
    .phase-timeline {{ display: flex; gap: 4px; min-height: 64px; align-items: stretch; margin: 12px 0; }}
    .phase-slice {{ background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 8px; min-width: 90px; overflow: hidden; }}
    .phase-slice strong, .phase-slice span {{ display: block; overflow-wrap: anywhere; }}
    .phase-slice span {{ color: #64748B; font-size: 0.8rem; }}
    .trajectory-svg {{ width: 100%; height: auto; display: block; border: 1px solid #CBD5E1; border-radius: 8px; background: #fff; }}
    .parallel-svg {{ width: 100%; height: auto; display: block; border: 1px solid #CBD5E1; border-radius: 8px; background: #fff; margin-top: 14px; }}
    .cycle-svg {{ width: 100%; height: auto; display: block; border: 1px solid #CBD5E1; border-radius: 8px; background: #fff; margin: 12px 0 14px; }}
    .svg-title {{ font-size: 20px; font-weight: 700; fill: #0f172a; }}
    .svg-label {{ font-size: 12px; font-weight: 650; fill: #334155; }}
    .svg-small {{ font-size: 11px; fill: #64748B; }}
    .svg-tick {{ font-size: 10px; fill: #64748B; }}
    .heatmap-wrap {{ overflow-x: auto; border: 1px solid #CBD5E1; border-radius: 8px; }}
    table.heatmap {{ min-width: 720px; border: 0; }}
    table.heatmap th, table.heatmap td {{ width: 30px; height: 24px; padding: 0; text-align: center; }}
    table.heatmap tbody th {{ width: 150px; padding: 5px 8px; text-align: left; background: #F8FAFC; }}
    table.heatmap thead th {{ font-size: 0.68rem; transform: none; white-space: nowrap; padding: 4px; }}
    table.signal-summary {{ margin-top: 14px; }}
    table.signal-summary th {{ width: 220px; }}
    table.cycle-table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    table.cycle-table th, table.cycle-table td {{ font-size: 0.86rem; }}
    code {{ background: #F1F5F9; padding: 1px 4px; border-radius: 4px; color: #334155; }}
    @media (max-width: 820px) {{ .grid, .grid3 {{ grid-template-columns: 1fr; }} .phase-timeline {{ flex-direction: column; }} header, main {{ width: min(100vw - 22px, 1180px); }} }}
  </style>
</head>
<body>
  <header>
    <h1>{html.escape(title)}</h1>
    <div class="summary">
      <span class="pill">Run: {html.escape(report['run_id'])}</span>
      <span class="pill">Status: {html.escape(report['final_status'])}</span>
      <span class="pill">Raw RFDE: {report['metrics']['aggregate']['ungated_rfde_score']}</span>
      <span class="pill">Validated RFDE: {report['metrics']['aggregate']['gated_rfde_score']}</span>
    </div>
  </header>
  <main>
{body}
  </main>
</body>
</html>
"""


def render_trajectory_timeline_html(report: Dict[str, Any]) -> str:
    """Document the responsibility of ``render_trajectory_timeline_html``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    trajectory_model = report.get("trajectory_model", {})
    summary = trajectory_model.get("summary", {})
    dynamics_rows = "\n".join(
        f"<tr><td>{html.escape(d['severity'])}</td><td>{html.escape(d['predicate'])}</td><td>{html.escape(d['interpretation'])}</td></tr>"
        for d in trajectory_model.get("dynamics", [])
    )
    phase_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(segment.get('segment_id')))}</td>"
        f"<td>{html.escape(str(segment.get('phase')))}</td>"
        f"<td>{html.escape(str(segment.get('start_cumulative_ms')))}</td>"
        f"<td>{html.escape(str(segment.get('end_cumulative_ms')))}</td>"
        f"<td>{html.escape(str(segment.get('event_count')))}</td>"
        f"<td>{html.escape(str(segment.get('efficiency')))}</td>"
        "</tr>"
        for segment in trajectory_model.get("phase_segments", [])
    )
    loop_rows = (
        "\n".join(
            "<tr>"
            f"<td>{html.escape(str(loop.get('loop_id')))}</td>"
            f"<td>{html.escape(str(loop.get('kind')))}</td>"
            f"<td>{html.escape(str(loop.get('start_event_index')))}</td>"
            f"<td>{html.escape(str(loop.get('end_event_index')))}</td>"
            f"<td>{html.escape(str(loop.get('interpretation')))}</td>"
            "</tr>"
            for loop in trajectory_model.get("loop_candidates", [])
        )
        or '<tr><td colspan="5">No loop candidates were observed.</td></tr>'
    )
    cards = "\n".join(
        f'<div class="stat"><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>'
        for label, value in [
            ("state count", summary.get("state_count")),
            ("action count", summary.get("action_count")),
            ("transition count", summary.get("transition_count")),
            ("phase transitions", summary.get("phase_transition_count")),
            ("phase coverage", summary.get("phase_coverage")),
            (
                "phase transition observability",
                summary.get("phase_transition_observability"),
            ),
            ("measurement density", summary.get("measurement_density")),
            ("delta density", summary.get("transition_delta_density")),
            ("convergence score", summary.get("convergence_score")),
            ("dominant phase seconds", summary.get("dominant_phase_seconds")),
            ("cost-normalized progress", summary.get("cost_normalized_progress")),
        ]
    )
    return render_dashboard_document(
        report,
        title="RFDE Trajectory Through Time",
        body=f"""
    {render_trajectory_interpretation_html(report)}
    <section class="panel">
      <h2>Temporal View</h2>
      <div class="grid3">{cards}</div>
      {render_trajectory_time_svg(trajectory_model)}
    </section>
    <section class="panel">
      <h2>Cycle Statistics</h2>
      <p class="muted">Cycle rows expose the growth of statements, grounded evidence, validation score, and blockers across phase changes.</p>
      {render_cycle_evolution_svg(trajectory_model)}
      <table class="cycle-table"><thead><tr><th>Cycle</th><th>Phase</th><th>Events</th><th>Actions</th><th>New facts</th><th>Facts total</th><th>Statements</th><th>Lean lines</th><th>Theorems</th><th>Score</th><th>Best</th><th>Delta</th><th>Coverage</th><th>Blockers</th><th>Pass rate</th><th>Interpretation</th></tr></thead><tbody>{render_cycle_statistics_rows(trajectory_model, limit=120)}</tbody></table>
    </section>
    <section class="panel">
      <h2>Parallel Evidence Tracks</h2>
      {render_parallel_signal_summary(report)}
      {render_parallel_signal_plots(report)}
    </section>
    <section class="panel">
      <h2>Transition Heatmap</h2>
      {render_transition_heatmap(trajectory_model)}
    </section>
    <section class="grid">
      <div class="panel">
        <h2>Dynamics</h2>
        <table><thead><tr><th>Severity</th><th>Predicate</th><th>Interpretation</th></tr></thead><tbody>{dynamics_rows}</tbody></table>
      </div>
      <div class="panel">
        <h2>Temporal Cost Model</h2>
        <pre>{html.escape(json.dumps(trajectory_model.get('temporal_cost_model', {}), indent=2, sort_keys=True))}</pre>
      </div>
    </section>
    <section class="panel">
      <h2>Phase Segments</h2>
      <table><thead><tr><th>ID</th><th>Phase</th><th>Start ms</th><th>End ms</th><th>Actions</th><th>Efficiency</th></tr></thead><tbody>{phase_rows}</tbody></table>
    </section>
    <section class="panel">
      <h2>Phase Transitions</h2>
      <table><thead><tr><th>ID</th><th>Phase Shift</th><th>Kind</th><th>Event</th><th>Confidence</th><th>Irreversibility</th><th>Healthy</th><th>Protected Regressions</th></tr></thead><tbody>{render_phase_transition_rows(trajectory_model, limit=120)}</tbody></table>
    </section>
    <section class="panel">
      <h2>Loop Candidates</h2>
      <table><thead><tr><th>ID</th><th>Kind</th><th>Start event</th><th>End event</th><th>Interpretation</th></tr></thead><tbody>{loop_rows}</tbody></table>
    </section>
    <section class="panel">
      <h2>Transitions</h2>
      <table><thead><tr><th>ID</th><th>Phase</th><th>Action</th><th>Source</th><th>ms</th><th>+</th><th>-</th><th>Efficiency</th></tr></thead><tbody>{render_trajectory_transition_rows(trajectory_model, limit=120)}</tbody></table>
    </section>
""",
    )


def final_status(hard_gates: Dict[str, bool], metrics: Dict[str, Any]) -> str:
    """Document the responsibility of ``final_status``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``final_status`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not all(hard_gates.values()):
        if hard_gates.get("core_obligations", True) is False:
            return "blocked"
        return "draft"
    if metrics["aggregate"]["ungated_rfde_score"] >= 0.78:
        return "complete"
    return "partial"


def build_report(args: argparse.Namespace) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Document the responsibility of ``build_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    evidence = collect_artifact_evidence(args)
    obligations = build_obligation_ledger(evidence)
    metrics = compute_metrics(evidence, args.task or "")
    cost = compute_cost(evidence)
    hard_gates = compute_hard_gates(evidence, metrics)
    trajectory_model = build_trajectory_model(evidence, metrics, hard_gates, cost)
    attach_trajectory_metrics(metrics, trajectory_model, hard_gates)
    hard_gates = compute_hard_gates(evidence, metrics)
    trajectory_model = build_trajectory_model(evidence, metrics, hard_gates, cost)
    attach_trajectory_metrics(metrics, trajectory_model, hard_gates)
    diagnostics = detect_diagnostics(evidence, metrics, cost, trajectory_model)
    parallel_plot_surfaces = build_parallel_plot_surfaces(
        evidence, metrics, trajectory_model
    )
    trajectory_interpretation = build_trajectory_interpretation(
        evidence=evidence,
        metrics=metrics,
        hard_gates=hard_gates,
        trajectory_model=trajectory_model,
        parallel_plot_surfaces=parallel_plot_surfaces,
    )
    timeseries = build_timeseries(evidence, metrics, cost, trajectory_model)
    timeseries["parallel_plot_surfaces"] = parallel_plot_surfaces
    timeseries["trajectory_interpretation"] = trajectory_interpretation
    report = {
        "schema_version": 1,
        "skill": SKILL_NAME,
        "hook_id": HOOK_ID,
        "generated_at_utc": utc_now(),
        "ok": all(hard_gates.values()),
        "run_id": args.run_id,
        "task_packet": {
            "instruction": args.task,
            "context_files": [str(path) for path in args.lean_file],
            "boundaries": [
                "reference-free",
                "artifact-grounded",
                "no gold output required",
            ],
        },
        "trace_summary": evidence["reasoning_trace"],
        "observation_surfaces": {
            "lean_summary": evidence["lean_summary"],
            "artifact_counts": {
                "lean_files": len(args.lean_file),
                "reasoning_logs": len(args.reasoning_log_file),
                "line_translation_packets": len(evidence["line_translation_packets"]),
                "anchor_reports": len(evidence["anchor_reports"]),
                "realness_reports": len(evidence["realness_reports"]),
                "consistency_reports": len(evidence["consistency_reports"]),
                "reference_free_snapshots": len(evidence["reference_free_snapshots"]),
            },
        },
        "claim_ledger": evidence["lean_claims"],
        "claim_ledger_summary": {
            "material_claims": len(evidence["lean_claims"]),
            "supported_claim_mass": supported_claim_mass(evidence["lean_claims"]),
            "unsupported_assertions": sum(
                1 for claim in evidence["lean_claims"] if not claim.get("support")
            ),
        },
        "obligation_ledger": obligations,
        "obligation_ledger_summary": dict(
            Counter(str(item["status"]) for item in obligations)
        ),
        "metrics": metrics,
        "hard_gates": hard_gates,
        "diagnostics": diagnostics,
        "cost": cost,
        "trajectory_model": trajectory_model,
        "parallel_plot_surfaces": parallel_plot_surfaces,
        "trajectory_interpretation": trajectory_interpretation,
        "trajectory": timeseries["points"],
        "final_status": final_status(hard_gates, metrics),
        "recommendations": recommendations(diagnostics, hard_gates),
    }
    return report, timeseries


def recommendations(
    diagnostics: Sequence[Dict[str, Any]], hard_gates: Dict[str, bool]
) -> List[str]:
    """Document the responsibility of ``recommendations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``recommendations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    recs: List[str] = []
    if not hard_gates.get("anchor", True):
        recs.append(
            "Run or repair the source-anchor drift guard and add missing `Source anchors:` comments."
        )
    if not hard_gates.get("realness", True):
        recs.append(
            "Remove placeholders, target axioms, mocks, or scaffold-only completion claims."
        )
    if any(item["kind"] == "mathlib_grounding_gap" for item in diagnostics):
        recs.append(
            "Run mathlib grounding maximization and import/context verification."
        )
    if any(item["kind"] == "weak_workflow_evidence" for item in diagnostics):
        recs.append(
            "Attach reasoning logs, consistency reports, and reference-free critic snapshots to strengthen auditability."
        )
    if not recs:
        recs.append(
            "No blocking RFDE action; inspect medium diagnostics before promotion."
        )
    return recs


def save_outputs(
    report: Dict[str, Any], timeseries: Dict[str, Any], output_dir: Path
) -> Dict[str, str]:
    """Document the responsibility of ``save_outputs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    json_file = output_dir / "rfde_report.json"
    md_file = output_dir / "rfde_report.md"
    html_file = output_dir / "rfde_dashboard.html"
    timeline_file = output_dir / "trajectory_timeline.html"
    ts_file = output_dir / "metrics_timeseries.json"
    trajectory_file = output_dir / "trajectory_model.json"
    write_json(json_file, report)
    write_json(ts_file, timeseries)
    write_json(trajectory_file, report.get("trajectory_model", {}))
    md_file.write_text(render_markdown(report), encoding="utf-8")
    html_file.write_text(render_html(report), encoding="utf-8")
    timeline_file.write_text(render_trajectory_timeline_html(report), encoding="utf-8")
    return {
        "rfde_report_json": rel(json_file),
        "rfde_report_markdown": rel(md_file),
        "rfde_dashboard_html": rel(html_file),
        "trajectory_timeline_html": rel(timeline_file),
        "metrics_timeseries": rel(ts_file),
        "trajectory_model_json": rel(trajectory_file),
    }


def run_self_test() -> Dict[str, Any]:
    """Document the responsibility of ``run_self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        lean = root / "Toy.lean"
        lean.write_text(
            """
import Mathlib.Init

/--
Original source (NL): Every natural number is equal to itself.
Original source (LaTeX): `\\forall n \\in \\mathbb{N}, n = n`.
Source anchors: src_L0001
-/
theorem toy_nat_refl (n : Nat) : n = n := by
  rfl
""".lstrip(),
            encoding="utf-8",
        )
        packet = root / "packet.json"
        packet.write_text(
            json.dumps(
                {
                    "source_lines": [
                        {
                            "id": "src_L0001",
                            "text": "Every natural number is equal to itself.",
                        }
                    ],
                    "translation_units": [
                        {
                            "id": "lt_001",
                            "source_line_ids": ["src_L0001"],
                            "formalizable": True,
                        }
                    ],
                    "summary": {"translation_unit_count": 1},
                }
            ),
            encoding="utf-8",
        )
        anchor = root / "anchor.json"
        anchor.write_text(
            json.dumps(
                {
                    "ok": True,
                    "summary": {
                        "anchor_coverage": 1.0,
                        "orphan_anchor_count": 0,
                    },
                }
            ),
            encoding="utf-8",
        )
        log = root / "reasoning.jsonl"
        log.write_text(
            json.dumps(
                {
                    "event_index": 1,
                    "step": "workflow_start",
                    "elapsed_ms_since_prev_event": 0,
                    "payload": {
                        "skill": "autoformalization-workflow-orchestrator",
                        "hook_id": "intake.workflow_start",
                    },
                }
            )
            + "\n"
            + json.dumps(
                {
                    "event_index": 2,
                    "step": "source_anchor_drift_guard_complete",
                    "elapsed_ms_since_prev_event": 120,
                    "payload": {
                        "skill": "source-formalization-drift-guard",
                        "hook_id": "postformalization.source_anchor_drift_guard",
                        "ok": True,
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        out = root / "out"
        args = argparse.Namespace(
            run_id="self-test",
            task="Prove a toy natural-number reflexivity theorem.",
            lean_file=[lean],
            reasoning_log_file=[log],
            anchor_report=[anchor],
            line_translation_packet=[packet],
            realness_report=[],
            consistency_report=[],
            workflow_report=[],
            history_file=[],
            reference_free_snapshot=[],
            object_run_manifest=[],
            batch_manifest=[],
        )
        report, timeseries = build_report(args)
        outputs = save_outputs(report, timeseries, out)
        checks = {
            "report_ok": report["ok"],
            "has_metrics": bool(report["metrics"]["rfde_profile"]),
            "has_mathformer_metrics": bool(report["metrics"]["mathformer_profile"]),
            "has_trajectory_profile": bool(report["metrics"].get("trajectory_profile")),
            "has_trajectory_model": bool(report.get("trajectory_model")),
            "has_states": len(report["trajectory_model"].get("states", [])) >= 2,
            "has_actions": len(report["trajectory_model"].get("actions", [])) >= 2,
            "has_transitions": len(report["trajectory_model"].get("transitions", []))
            >= 2,
            "has_phase_segments": len(
                report["trajectory_model"].get("phase_segments", [])
            )
            >= 1,
            "has_phase_transition_model": "phase_transitions"
            in report["trajectory_model"],
            "has_phase_transition_summary": "phase_transition_count"
            in report["trajectory_model"].get("summary", {}),
            "has_phase_transition": len(
                report["trajectory_model"].get("phase_transitions", [])
            )
            >= 1,
            "has_phase_transition_profile": "phase_transition_observability"
            in report["metrics"].get("trajectory_profile", {}),
            "has_dynamics": bool(report["trajectory_model"].get("dynamics")),
            "has_claims": len(report["claim_ledger"]) == 1,
            "has_obligations": len(report["obligation_ledger"]) >= 4,
            "has_diagnostics": bool(report["diagnostics"]),
            "has_timeseries": len(timeseries["points"]) >= 2,
            "has_state_timeseries": len(timeseries.get("state_timeseries", [])) >= 2,
            "has_transition_timeseries": len(
                timeseries.get("transition_timeseries", [])
            )
            >= 2,
            "has_phase_transition_timeseries": len(
                timeseries.get("phase_transition_timeseries", [])
            )
            >= 1,
            "wrote_json": (out / "rfde_report.json").exists(),
            "wrote_md": (out / "rfde_report.md").exists(),
            "wrote_html": (out / "rfde_dashboard.html").exists(),
            "wrote_timeline_html": (out / "trajectory_timeline.html").exists(),
            "wrote_timeseries": (out / "metrics_timeseries.json").exists(),
            "wrote_trajectory_model": (out / "trajectory_model.json").exists(),
        }
        return {
            "ok": all(checks.values()),
            "checks": checks,
            "outputs": outputs,
            "summary": report["metrics"]["aggregate"],
        }


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
    parser.add_argument("--run-id", default="rfde-run")
    parser.add_argument("--task", default="")
    parser.add_argument("--lean-file", action="append", type=Path, default=[])
    parser.add_argument("--reasoning-log-file", action="append", type=Path, default=[])
    parser.add_argument("--anchor-report", action="append", type=Path, default=[])
    parser.add_argument(
        "--line-translation-packet", action="append", type=Path, default=[]
    )
    parser.add_argument("--realness-report", action="append", type=Path, default=[])
    parser.add_argument("--consistency-report", action="append", type=Path, default=[])
    parser.add_argument("--workflow-report", action="append", type=Path, default=[])
    parser.add_argument("--history-file", action="append", type=Path, default=[])
    parser.add_argument(
        "--reference-free-snapshot", action="append", type=Path, default=[]
    )
    parser.add_argument("--object-run-manifest", action="append", type=Path, default=[])
    parser.add_argument("--batch-manifest", action="append", type=Path, default=[])
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--reasoning-log-output", type=Path)
    parser.add_argument("--expect-ok", action="store_true")
    parser.add_argument("--self-test", action="store_true")
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
    if args.self_test:
        result = run_self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 3
    output_dir = (
        (REPO_ROOT / args.output_dir).resolve()
        if args.output_dir is not None and not args.output_dir.is_absolute()
        else args.output_dir
    ) or (REPO_ROOT / "artifacts" / "rfde" / args.run_id)
    append_event(
        args.reasoning_log_output, "rfde_report_start", {"run_id": args.run_id}
    )
    report, timeseries = build_report(args)
    append_event(
        args.reasoning_log_output,
        "rfde_surface_measurement_complete",
        {
            "run_id": args.run_id,
            "ungated_rfde_score": report["metrics"]["aggregate"]["ungated_rfde_score"],
            "hard_gate_factor": report["metrics"]["aggregate"]["hard_gate_factor"],
        },
    )
    append_event(
        args.reasoning_log_output,
        "rfde_trajectory_analysis_complete",
        {
            "run_id": args.run_id,
            "diagnostic_count": len(report["diagnostics"]),
            "trajectory_summary": report["trajectory_model"]["summary"],
            "convergence_condition": report["trajectory_model"][
                "convergence_condition"
            ],
            "cost": report["cost"],
        },
    )
    outputs = save_outputs(report, timeseries, output_dir)
    report["outputs"] = outputs
    write_json(output_dir / "rfde_report.json", report)
    append_event(
        args.reasoning_log_output,
        "rfde_report_complete",
        {
            "run_id": args.run_id,
            "ok": report["ok"],
            "final_status": report["final_status"],
            **outputs,
        },
    )
    if args.expect_ok and not report["ok"]:
        append_event(
            args.reasoning_log_output,
            "rfde_report_error",
            {"run_id": args.run_id, "reason": "report not ok"},
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 3
    if args.json:
        print(
            json.dumps(
                {"ok": report["ok"], "final_status": report["final_status"], **outputs},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"ok: {report['ok']}")
        print(f"final_status: {report['final_status']}")
        for key, value in outputs.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

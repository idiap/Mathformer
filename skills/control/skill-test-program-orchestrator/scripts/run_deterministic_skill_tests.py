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

"""Run deterministic tests for Mathformer skills and workflow contracts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "skill-test-program-orchestrator"
HOOK_ID = "test.skill_program"


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
    if reasoning_log is None:
        return
    append_reasoning_log_entry(
        reasoning_log,
        step=step,
        payload={"skill": SKILL_NAME, "hook_id": HOOK_ID, **payload},
    )


def run_command(
    check_id: str,
    cmd: Sequence[str],
    *,
    timeout_sec: int = 120,
    required: bool = True,
) -> Dict[str, Any]:
    """Document the responsibility of ``run_command``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(cmd),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "id": check_id,
            "cmd": list(cmd),
            "ok": proc.returncode == 0,
            "required": required,
            "returncode": proc.returncode,
            "duration_ms": duration_ms,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "id": check_id,
            "cmd": list(cmd),
            "ok": False,
            "required": required,
            "returncode": None,
            "duration_ms": duration_ms,
            "stdout": (exc.stdout or "")[-4000:],
            "stderr": (exc.stderr or f"timeout after {timeout_sec}s")[-4000:],
            "timeout": True,
        }


def python_files() -> List[str]:
    """Document the responsibility of ``python_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``python_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    paths = sorted(
        [
            *REPO_ROOT.glob("skills/*/*/scripts/*.py"),
            *REPO_ROOT.glob("tests/**/*.py"),
            *REPO_ROOT.glob("benchmarks/**/*.py"),
        ]
    )
    return [rel(path) for path in paths if "__pycache__" not in path.parts]


def lean_semantic_comment_files() -> List[str]:
    """Document the responsibility of ``lean_semantic_comment_files``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``lean_semantic_comment_files`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    paths = sorted(
        [
            *REPO_ROOT.glob("backends/lean/Mathformer/*.lean"),
            *REPO_ROOT.glob("libraries/MathformerLib/*.lean"),
            REPO_ROOT / "libraries/MathformerLib.lean",
        ]
    )
    return [rel(path) for path in paths if path.exists()]


def existing_log_checks() -> List[tuple[str, List[str], bool]]:
    """Document the responsibility of ``existing_log_checks``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Validate assumptions or artifacts and return explicit evidence about whether the contract holds.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    checks: List[tuple[str, List[str], bool]] = []
    suite_log = Path("artifacts/wiki_level_suite/reasoning.jsonl")
    if (REPO_ROOT / suite_log).exists():
        checks.append(
            (
                "suite_reasoning_log_strict",
                [
                    "python3",
                    "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py",
                    "--log-file",
                    str(suite_log),
                    "--hooks-file",
                    "skills/SKILL_HOOKS.yaml",
                    "--strict",
                ],
                True,
            )
        )
    reflection_log = Path("artifacts/reflection/reasoning.jsonl")
    if (REPO_ROOT / reflection_log).exists():
        checks.append(
            (
                "reflection_reasoning_log_strict",
                [
                    "python3",
                    "skills/control/reasoning-log-schema-guardian/scripts/validate_reasoning_log.py",
                    "--log-file",
                    str(reflection_log),
                    "--hooks-file",
                    "skills/SKILL_HOOKS.yaml",
                    "--strict",
                ],
                False,
            )
        )
    return checks


def build_checks(
    *, include_slow: bool, help_smoke: bool
) -> List[tuple[str, List[str], int, bool]]:
    """Document the responsibility of ``build_checks``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    checks: List[tuple[str, List[str], int, bool]] = []
    current_python = sys.executable
    venv_python = REPO_ROOT / ".venv" / "bin" / "python"
    sympy_python = str(venv_python if venv_python.exists() else Path(current_python))
    py_files = python_files()
    if py_files:
        checks.append(
            (
                "py_compile_all",
                [current_python, "-m", "py_compile", *py_files],
                120,
                True,
            )
        )
    lean_comment_files = lean_semantic_comment_files()
    checks.extend(
        [
            (
                "skill_hooks_yaml_parse",
                [
                    "ruby",
                    "-e",
                    'require "yaml"; YAML.load_file("skills/SKILL_HOOKS.yaml")',
                ],
                30,
                True,
            ),
            (
                "workflow_contract_strict",
                [
                    "python3",
                    "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py",
                    "--strict",
                ],
                60,
                True,
            ),
            (
                "reasoning_flow_language_self_test",
                [
                    current_python,
                    "skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "reasoning_flow_profiles_strict",
                [
                    current_python,
                    "skills/control/reasoning-flow-language/scripts/validate_reasoning_flow.py",
                    "examples/reasoning_flows",
                    "--strict",
                    "--check-registries",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "reasoning_flow_catalog_synchronized",
                [
                    current_python,
                    "skills/control/reasoning-flow-language/scripts/render_all_reasoning_flows.py",
                    "--check",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "skill_hook_coverage_maximized",
                [
                    "python3",
                    "skills/control/skill-hook-coverage-maximizer/scripts/audit_skill_hook_coverage.py",
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "gate_policy_smoke",
                [
                    "python3",
                    "skills/control/gate-policy-controller/scripts/gate_policy.py",
                    "--gate-id",
                    "skill-test-smoke",
                    "--check",
                    "hook_contract=true:high:true:validator smoke",
                    "--fail-fast",
                ],
                30,
                True,
            ),
            (
                "reasoning_log_agent_usage_instrumentation",
                [
                    "python3",
                    "-c",
                    "from pathlib import Path; import sys, json; "
                    "sys.path.insert(0, 'skills/control/reasoning-log-schema-guardian/scripts'); "
                    "from reasoning_log import append_reasoning_log_entry, reset_reasoning_log_state; "
                    "from validate_reasoning_log import validate_reasoning_log; "
                    "p=Path('artifacts/reasoning_log_instrumentation_smoke/reasoning.jsonl'); "
                    "p.parent.mkdir(parents=True, exist_ok=True); p.write_text(''); reset_reasoning_log_state(p); "
                    "append_reasoning_log_entry(p, step='workflow_start', statement='Truth is derivable.', file_prefix='instrumentation_smoke', payload={'skill':'autoformalization-workflow-orchestrator','hook_id':'intake.workflow_start'}); "
                    "report=validate_reasoning_log(p, hooks_file=Path('skills/SKILL_HOOKS.yaml'), strict=True, require_instrumentation=True); "
                    "assert report['ok'], report; "
                    "entry=json.loads(p.read_text().splitlines()[0]); "
                    "assert entry['payload']['agent_usage']['hook_phase']=='intake', entry; "
                    "assert 'criteria' in entry['payload']['convergence_criteria'], entry; "
                    "print(json.dumps(report['summary'], sort_keys=True))",
                ],
                30,
                True,
            ),
            (
                "lean_line_comment_contract_self_test",
                [
                    "python3",
                    "skills/lean/lean-line-annotation/scripts/validate_lean_line_comments.py",
                    "--self-test",
                ],
                30,
                True,
            ),
            (
                "lean_source_semantic_comment_guard",
                [
                    "python3",
                    "skills/lean/lean-line-annotation/scripts/validate_lean_line_comments.py",
                    *lean_comment_files,
                    "--require-semantic-comments",
                ],
                30,
                True,
            ),
            (
                "source_formalizable_unit_extractor_self_test",
                [
                    "python3",
                    "skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "source_line_translation_packet_builder_self_test",
                [
                    "python3",
                    "skills/autoformalization/source-line-translation-packet-builder/scripts/build_line_translation_packet.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "source_formalization_drift_guard_self_test",
                [
                    "python3",
                    "skills/autoformalization/source-formalization-drift-guard/scripts/validate_source_formalization_alignment.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "paper_docling_layout_extractor_self_test",
                [
                    "python3",
                    "skills/paper/paper-docling-layout-extractor/scripts/extract_paper_layout.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "paper_main_theory_localizer_self_test",
                [
                    "python3",
                    "skills/paper/paper-main-theory-localizer/scripts/localize_paper_theory.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "paper_main_theory_localizer_theorem_smoke",
                [
                    "python3",
                    "skills/paper/paper-main-theory-localizer/scripts/localize_paper_theory.py",
                    "--text",
                    "Main Results\nDefinition 1. A class has intrinsic dimension d if it admits a d-dimensional chart. Assumption 2. Samples are independent. Theorem 3. Under Assumption 2, the risk is bounded by C n^{-1}. Proof. Apply Lemma 4 and the external bound [1]. Lemma 4. The approximation error is bounded. References\n[1] External bound paper.",
                    "--expect-main-kind",
                    "theorem",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "paper_theory_autoformalization_orchestrator_self_test",
                [
                    "python3",
                    "skills/paper/paper-theory-autoformalization-orchestrator/scripts/build_paper_theory_plan.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "latex_archive_theory_extractor_self_test",
                [
                    "python3",
                    "skills/latex-textbook/latex-archive-theory-extractor/scripts/extract_latex_theory.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "textbook_theory_tex_organizer_self_test",
                [
                    "python3",
                    "skills/latex-textbook/textbook-theory-tex-organizer/scripts/organize_theory_tex.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "textbook_autoformalization_batch_orchestrator_self_test",
                [
                    "python3",
                    "skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/build_textbook_autoformalization_batch.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "textbook_chapter_autoformalization_orchestrator_self_test",
                [
                    "python3",
                    "skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/scripts/orchestrate_textbook_chapters.py",
                    "--self-test",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "textbook_autoformalization_batch_runner_self_test",
                [
                    "python3",
                    "skills/latex-textbook/textbook-autoformalization-batch-orchestrator/scripts/run_textbook_autoformalization_batch.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "source_formalizable_unit_extractor_lipschitz_smoke",
                [
                    "python3",
                    "skills/autoformalization/source-formalizable-unit-extractor/scripts/extract_autoformalizable_units.py",
                    "--text",
                    "A function f between metric spaces is called Lipschitz continuous if d(f x, f y) <= K * d(x, y). Every Lipschitz continuous function is uniformly continuous. Proof. Choose delta from epsilon and the Lipschitz constant.",
                    "--title",
                    "Lipschitz continuity",
                    "--expect-kind",
                    "definition",
                    "--expect-kind",
                    "theorem",
                    "--expect-kind",
                    "proof",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "result_realness_clean_fixture",
                [
                    "python3",
                    "skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py",
                    "--text",
                    "/--\nOriginal source (NL): Truth is derivable.\nOriginal source (LaTeX): `\\mathrm{True}`.\n-/\ntheorem t : True := by trivial",
                    "--name",
                    "clean_fixture",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "result_realness_mock_detection",
                [
                    "python3",
                    "skills/autoformalization/autoformalization-result-realness-verifier/scripts/verify_artifact_realness.py",
                    "--text",
                    "theorem t : True := by sorry",
                    "--name",
                    "mocked_sorry_fixture",
                    "--expect-blocking",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "reference_free_critic_monitor_self_test",
                [
                    "python3",
                    "skills/rfde/reference-free-critic-monitor/scripts/monitor_reference_free_critics.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "reference_free_descriptive_evaluator_self_test",
                [
                    "python3",
                    "skills/rfde/reference-free-descriptive-evaluator/scripts/build_rfde_report.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_informalization_extractor_self_test",
                [
                    "python3",
                    "skills/lean/lean-informalization-extractor/scripts/extract_lean_informalization.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_informal_proof_internal_consistency_self_test",
                [
                    "python3",
                    "skills/lean/lean-informal-proof-internal-consistency-verifier/scripts/verify_informal_proof_internal_consistency.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_autoformalized_informal_internal_consistency",
                [
                    "python3",
                    "skills/lean/lean-informal-proof-internal-consistency-verifier/scripts/verify_informal_proof_internal_consistency.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "lean_informal_consistency_verifier_self_test",
                [
                    "python3",
                    "skills/lean/lean-informal-consistency-verifier/scripts/verify_informal_consistency.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_autoformalized_informal_consistency",
                [
                    "python3",
                    "skills/lean/lean-informal-consistency-verifier/scripts/verify_informal_consistency.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "lean_declaration_shape_consistency_self_test",
                [
                    "python3",
                    "skills/lean/lean-declaration-shape-consistency-checker/scripts/check_declaration_shape_consistency.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_autoformalized_declaration_shape_consistency",
                [
                    "python3",
                    "skills/lean/lean-declaration-shape-consistency-checker/scripts/check_declaration_shape_consistency.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "lean_nonvacuity_consistency_self_test",
                [
                    "python3",
                    "skills/lean/lean-nonvacuity-consistency-checker/scripts/check_lean_nonvacuity_consistency.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_autoformalized_nonvacuity_consistency",
                [
                    "python3",
                    "skills/lean/lean-nonvacuity-consistency-checker/scripts/check_lean_nonvacuity_consistency.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "lean_cross_file_concept_indexer_self_test",
                [
                    "python3",
                    "skills/lean/lean-cross-file-concept-consistency-indexer/scripts/index_cross_file_concepts.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_autoformalized_cross_file_concept_consistency",
                [
                    "python3",
                    "skills/lean/lean-cross-file-concept-consistency-indexer/scripts/index_cross_file_concepts.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "lean_consistency_report_orchestrator_self_test",
                [
                    "python3",
                    "skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py",
                    "--self-test",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "workflow_consistency_report_integration_smoke",
                [
                    "python3",
                    "-c",
                    "from pathlib import Path; import sys; "
                    "import json; "
                    "sys.path.insert(0, 'skills/autoformalization/autoformalization-agentc/scripts'); "
                    "from agentc import HardCritiqueAgent, IterativeSelfRefinementAgentC; "
                    "out=Path('artifacts/workflow_consistency_smoke'); out.mkdir(parents=True, exist_ok=True); "
                    "hard=HardCritiqueAgent(formal_language='Lean4', lean_workdir='.'); "
                    "workflow=IterativeSelfRefinementAgentC(autoformalizer=None, hard_critique=hard, soft_critique=None, formal_refiner=None, informal_refiner=None, aspect_description='workflow consistency smoke', max_iterations=0, default_first_formalization_cycles=1, default_target_compatibility_score=None); "
                    "seed='/--\\nOriginal source (NL): Truth is derivable.\\nOriginal source (LaTeX): `\\\\\\\\mathrm{True}`.\\n-/\\ntheorem workflow_consistency_smoke : True := by\\n  trivial\\n'; "
                    "report=workflow.run_systematic_workflow('Truth is derivable.', output_file=out/'workflow_consistency_smoke.lean', report_file=out/'workflow_consistency_smoke.report.json', history_file=out/'workflow_consistency_smoke.history.json', reasoning_log_file=out/'workflow_consistency_smoke.reasoning.jsonl', seed_formalization=seed, enable_default_multi_cycle=False, enable_latex_expansion=False, enable_concept_mapping=False, enforce_mathlib_alignment=False, enable_mathlib_concept_compatibility_loop=False, enable_llm_judges=False, enable_compatibility_audit=False, enable_lean_consistency_report=True, lean_consistency_run_lean_check=True, lean_consistency_target_reference_free_score=60); "
                    "assert report.consistency_target_met is True, report.consistency_report; "
                    "assert report.consistency_report_file and Path(report.consistency_report_file).exists(); "
                    "events=[json.loads(line) for line in (out/'workflow_consistency_smoke.reasoning.jsonl').read_text().splitlines() if line.strip()]; "
                    "assert events and all('agent_usage' in event['payload'] for event in events), events; "
                    "assert all('convergence_criteria' in event['payload'] for event in events), events; "
                    "print(report.consistency_report_file)",
                ],
                90,
                True,
            ),
            (
                "lean_autoformalized_unified_consistency_report",
                [
                    "python3",
                    "skills/lean/lean-consistency-report-orchestrator/scripts/run_lean_consistency_report.py",
                    *[
                        part
                        for path in sorted(
                            REPO_ROOT.glob(
                                "backends/lean/Mathformer/Autoformalized*.lean"
                            )
                        )
                        for part in ("--lean-file", rel(path))
                    ],
                    "--expect-ok",
                    "--json",
                ],
                120,
                True,
            ),
            (
                "mathlib_grounding_maximizer_self_test",
                [
                    "python3",
                    "skills/mathlib/mathlib-grounding-maximizer/scripts/maximize_mathlib_grounding.py",
                    "--self-test",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "mathlib_import_set_clean_fixture",
                [
                    "python3",
                    "skills/mathlib/mathlib-import-set-builder/scripts/build_import_set.py",
                    "--expected-import",
                    "Mathlib.Data.Nat.Basic",
                    "--candidate-import",
                    "Mathlib.Order.Basic",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "lean_import_context_broad_detection",
                [
                    "python3",
                    "skills/lean/lean-import-context-verifier/scripts/verify_import_context.py",
                    "--text",
                    "import Mathlib\n#check Nat",
                    "--expected-import",
                    "Mathlib.Data.Nat.Basic",
                    "--expect-blocking",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_import_minimizer_broad_detection",
                [
                    "python3",
                    "skills/mathlib/mathlib-import-minimizer/scripts/minimize_imports.py",
                    "--text",
                    "import Mathlib\nimport Mathlib\n#check Nat",
                    "--expect-blocking",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_concept_ontology_validation",
                [
                    "python3",
                    "skills/mathlib/mathlib-concept-ontology-manager/scripts/validate_concept_ontology.py",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "result_existence_checker_self_test",
                [
                    "python3",
                    "skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py",
                    "--self-test",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "result_existence_detects_mathformerlib_seed",
                [
                    "python3",
                    "skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py",
                    "--statement",
                    "Truth is derivable in the MathformerLib seed library.",
                    "--expected-name",
                    "MathformerLib.true_intro",
                    "--no-mathlib",
                    "--no-web-plan",
                    "--expect-existing",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "result_existence_requires_web_confirmation",
                [
                    "python3",
                    "skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py",
                    "--statement",
                    "Every zorbledorf manifold is chromatic over a glim field.",
                    "--concept",
                    "zorbledorf manifold",
                    "--no-mathlib",
                    "--expect-web-required",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "result_existence_not_found_after_web_absence",
                [
                    "python3",
                    "skills/mathlib/mathlib-result-existence-checker/scripts/check_result_existence.py",
                    "--statement",
                    "Every zorbledorf manifold is chromatic over a glim field.",
                    "--concept",
                    "zorbledorf manifold",
                    "--no-mathlib",
                    "--web-confirmed-absent",
                    "--expect-not-found",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_web_search_strategy_self_test",
                [
                    "python3",
                    "skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_web_search_strategy_concept_smoke",
                [
                    "python3",
                    "skills/mathlib/mathlib-web-search-strategist/scripts/plan_mathlib_web_search.py",
                    "--concept",
                    "monotone",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_web_evidence_validator_self_test",
                [
                    "python3",
                    "skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "isarmathlib_grounding_navigator_self_test",
                [
                    "python3",
                    "skills/isabelle/isarmathlib-grounding-navigator/scripts/search_isarmathlib.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "isabelle_autoformalization_drafter_self_test",
                [
                    "python3",
                    "skills/isabelle/isabelle-autoformalization-drafter/scripts/draft_isabelle_wiki_case.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "isabelle_execution_runner_self_test",
                [
                    "python3",
                    "skills/isabelle/isabelle-execution-runner/scripts/check_isabelle_theory.py",
                    "--self-test",
                    "--json",
                ],
                180,
                True,
            ),
            (
                "sympy_dependency_probe",
                [
                    sympy_python,
                    "skills/sympy/sympy-dependency-prober/scripts/probe_sympy_dependencies.py",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_api_docs_indexer_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-api-docs-indexer/scripts/index_sympy_api.py",
                    "--self-test",
                    "--json",
                ],
                60,
                True,
            ),
            (
                "sympy_expression_parser_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-expression-parser/scripts/parse_sympy_expressions.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_assumption_modeler_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-assumption-modeler/scripts/model_sympy_assumptions.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_concept_grounding_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-concept-grounding-navigator/scripts/ground_sympy_concepts.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_drafter_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-autoformalization-drafter/scripts/draft_sympy_case.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_execution_runner_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-execution-runner/scripts/run_sympy_artifact.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_identity_validator_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-identity-validator/scripts/validate_sympy_identity.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_counterexample_searcher_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-counterexample-searcher/scripts/search_sympy_counterexamples.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_trace_verifier_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-transformation-trace-verifier/scripts/verify_sympy_trace.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "sympy_consistency_report_self_test",
                [
                    sympy_python,
                    "skills/sympy/sympy-consistency-report-orchestrator/scripts/run_sympy_consistency_report.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_web_evidence_blocks_retrieval_only",
                [
                    "python3",
                    "skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py",
                    "--text",
                    '{"claims":[{"claim_type":"declaration","claim":"CompactSpace is in mathlib from retrieval only.","source_url":"https://loogle.lean-lang.org/?q=CompactSpace","query":"CompactSpace","evidence_summary":"Retrieval aid produced a candidate.","declaration":"CompactSpace","local_verification":{"method":"#check","check_ok":true}}]}',
                    "--expect-blocking",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathlib_web_evidence_accepts_officially_corroborated_retrieval",
                [
                    "python3",
                    "skills/mathlib/mathlib-web-evidence-validator/scripts/validate_mathlib_web_evidence.py",
                    "--text",
                    '{"claims":[{"claim_type":"declaration","claim":"CompactSpace is in mathlib after retrieval-aid discovery and official corroboration.","source_url":"https://loogle.lean-lang.org/?q=CompactSpace","official_corroboration_url":"https://leanprover-community.github.io/mathlib4_docs/Mathlib/Topology/Compactness/Compact.html","query":"CompactSpace","evidence_summary":"Official mathlib docs corroborate the retrieval-aid candidate.","declaration":"CompactSpace","module":"Mathlib.Topology.Compactness.Compact","local_verification":{"method":"#check","check_ok":true}}]}',
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathformerlib_registry_root",
                [
                    "python3",
                    "skills/mathformerlib/mathformerlib-registry-manager/scripts/manage_mathformerlib_registry.py",
                    "--include-root",
                    "MathformerLib",
                    "--include-root",
                    "libraries/MathformerLib.lean",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathformerlib_promotion_clean_fixture",
                [
                    "python3",
                    "skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py",
                    "--text",
                    "/--\nOriginal source (NL): Truth is derivable.\nOriginal source (LaTeX): `\\mathrm{True}`.\n-/\ntheorem t : True := by trivial",
                    "--name",
                    "clean_fixture",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathformerlib_promotion_blocks_sorry",
                [
                    "python3",
                    "skills/mathformerlib/mathformerlib-promotion-gate/scripts/evaluate_mathformerlib_promotion.py",
                    "--text",
                    "theorem t : True := by sorry",
                    "--name",
                    "sorry_fixture",
                    "--expect-blocking",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathformer_library_docs_generator_self_test",
                [
                    "python3",
                    "skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py",
                    "--self-test",
                    "--json",
                ],
                30,
                True,
            ),
            (
                "mathformerlib_root_lean",
                ["lake", "build", "MathformerLib"],
                120,
                True,
            ),
        ]
    )
    for check_id, cmd, required in existing_log_checks():
        checks.append((check_id, cmd, 60, required))
    if include_slow:
        checks.extend(
            [
                (
                    "wiki_level_suite",
                    [current_python, "tests/wiki_level/run_suite.py"],
                    180,
                    True,
                ),
                (
                    "wiki_gold_lean",
                    ["lake", "env", "lean", "tests/lean/WikiLevelGold.lean"],
                    120,
                    True,
                ),
                (
                    "wiki_isabelle_injective_composition",
                    [current_python, "tests/isabelle/run_wiki_case.py", "--json"],
                    300,
                    True,
                ),
                (
                    "wiki_sympy_sum_first_odd_numbers",
                    [current_python, "tests/sympy/run_wiki_case.py", "--json"],
                    180,
                    True,
                ),
                (
                    "sympy_controlled_suite",
                    [current_python, "tests/sympy/run_controlled_suite.py", "--json"],
                    300,
                    True,
                ),
                (
                    "reflective_observer",
                    [
                        current_python,
                        "skills/autoformalization/autoformalization-reflective-refinement-loop/scripts/observe_autoformalization_process.py",
                        "--report-file",
                        "artifacts/wiki_level_suite/report.json",
                        "--reasoning-log-file",
                        "artifacts/wiki_level_suite/reasoning.jsonl",
                        "--hooks-file",
                        "skills/SKILL_HOOKS.yaml",
                        "--baseline-file",
                        "artifacts/reflection/wiki_level_baseline.json",
                    ],
                    90,
                    True,
                ),
            ]
        )
    if help_smoke:
        for script in sorted(REPO_ROOT.glob("skills/*/*/scripts/*.py")):
            checks.append(
                (
                    f"help_{script.parent.parent.name}_{script.stem}",
                    [current_python, rel(script), "--help"],
                    30,
                    False,
                )
            )
    return checks


def run_tests(
    *,
    include_slow: bool,
    help_smoke: bool,
    reasoning_log: Optional[Path],
) -> Dict[str, Any]:
    """Document the responsibility of ``run_tests``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    append_event(
        reasoning_log,
        "skill_test_deterministic_start",
        {"include_slow": include_slow, "help_smoke": help_smoke},
    )
    checks = build_checks(include_slow=include_slow, help_smoke=help_smoke)
    results: List[Dict[str, Any]] = []
    for check_id, cmd, timeout_sec, required in checks:
        result = run_command(check_id, cmd, timeout_sec=timeout_sec, required=required)
        results.append(result)
        append_event(
            reasoning_log,
            "skill_test_deterministic_check_complete",
            {
                "check_id": check_id,
                "ok": result["ok"],
                "required": required,
                "duration_ms": result["duration_ms"],
            },
        )
    blocking_failures = [
        item for item in results if item["required"] and not item["ok"]
    ]
    advisory_failures = [
        item for item in results if not item["required"] and not item["ok"]
    ]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ok": not blocking_failures,
        "summary": {
            "check_count": len(results),
            "passed_count": sum(1 for item in results if item["ok"]),
            "blocking_failure_count": len(blocking_failures),
            "advisory_failure_count": len(advisory_failures),
        },
        "results": results,
    }
    append_event(
        reasoning_log,
        "skill_test_deterministic_complete",
        {
            "ok": report["ok"],
            "check_count": len(results),
            "blocking_failure_count": len(blocking_failures),
        },
    )
    return report


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
        f"checks: {summary['check_count']}",
        f"passed: {summary['passed_count']}",
        f"blocking_failures: {summary['blocking_failure_count']}",
        f"advisory_failures: {summary['advisory_failure_count']}",
    ]
    for item in report["results"]:
        status = "PASS" if item["ok"] else "FAIL"
        req = "required" if item["required"] else "advisory"
        lines.append(f"- {status} {item['id']} ({req}, {item['duration_ms']} ms)")
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
    parser.add_argument("--include-slow", action="store_true")
    parser.add_argument("--help-smoke", action="store_true")
    parser.add_argument(
        "--module-family",
        action="append",
        choices=[
            "control",
            "source",
            "paper",
            "textbook",
            "mathlib",
            "lean",
            "isabelle",
            "sympy",
            "physics_sympy",
            "rfde",
            "docs",
            "mathformerlib",
            "environment",
            "e2e",
            "generative",
            "all",
        ],
        default=[],
        help="Delegate to the comprehensive test runner for selected module families.",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("artifacts/skill_test_program/deterministic_report.json"),
    )
    parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        default=Path("artifacts/skill_test_program/reasoning.jsonl"),
    )
    parser.add_argument("--no-reasoning-log", action="store_true")
    parser.add_argument(
        "--write-junit",
        nargs="?",
        const="artifacts/test_program/deterministic_tests.xml",
        help="Delegate to the comprehensive runner and write JUnit XML.",
    )
    parser.add_argument(
        "--write-jsonl",
        nargs="?",
        const="artifacts/test_program/deterministic_tests.jsonl",
        help="Delegate to the comprehensive runner and write one JSONL event per check.",
    )
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--changed-files-only", action="store_true")
    parser.add_argument("--validate-matrix", action="store_true")
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
    should_delegate = (
        bool(args.module_family)
        or bool(args.write_junit)
        or bool(args.write_jsonl)
        or args.fail_on_warning
        or args.changed_files_only
        or args.validate_matrix
    )
    if should_delegate:
        command = [
            sys.executable,
            str(REPO_ROOT / "tests" / "test_program" / "run_comprehensive_tests.py"),
            "--output-file",
            str(args.output_file),
        ]
        for family in args.module_family or ["all"]:
            command.extend(["--module-family", family])
        if args.write_junit:
            command.extend(["--write-junit", str(args.write_junit)])
        if args.write_jsonl:
            command.extend(["--write-jsonl", str(args.write_jsonl)])
        if args.fail_on_warning:
            command.append("--fail-on-warning")
        if args.changed_files_only:
            command.append("--changed-files-only")
        if args.validate_matrix:
            command.append("--validate-matrix")
        if args.json:
            command.append("--json")
        return subprocess.call(command, cwd=REPO_ROOT)

    reasoning_log = (
        None
        if args.no_reasoning_log
        else (REPO_ROOT / args.reasoning_log_file).resolve()
    )
    report = run_tests(
        include_slow=args.include_slow,
        help_smoke=args.help_smoke,
        reasoning_log=reasoning_log,
    )
    output_file = (REPO_ROOT / args.output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    sys.exit(main())

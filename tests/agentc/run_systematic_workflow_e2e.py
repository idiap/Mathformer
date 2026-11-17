#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Exercise AgentC end to end through deterministic provider seams."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTC_PATH = (
    REPO_ROOT / "skills/autoformalization/autoformalization-agentc/scripts/agentc.py"
)
ARTIFACT_ROOT = REPO_ROOT / "artifacts/agentc/systematic_e2e"
VALID_CODE = "import Mathlib\n\nexample : True := by trivial\n"


def load_agentc():
    spec = importlib.util.spec_from_file_location(
        "mathformer_agentc_e2e_module", AGENTC_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load agentc.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SeededAutoformalizer:
    def __init__(self, code: str = VALID_CODE, error: BaseException | None = None):
        self.code = code
        self.error = error
        self.calls = 0

    def __call__(self, **_: Any) -> tuple[str, str]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.code, f"seeded-provider-call-{self.calls}"


class SeededHardCritic:
    def __init__(self, fail_count: int = 0):
        self.fail_count = fail_count
        self.calls = 0

    def __call__(self, *, formalization: str, file_prefix: str) -> tuple[str, str]:
        self.calls += 1
        if self.calls <= self.fail_count:
            return "False", "seeded compile failure"
        valid = "example : True" in formalization
        return (
            ("True", "seeded kernel success") if valid else ("False", "missing target")
        )


class SeededSoftCritic:
    def __call__(self, **_: Any) -> tuple[str, str]:
        return "True", "seeded semantic acceptance"


class SeededRefiner:
    def __init__(self):
        self.calls = 0

    def __call__(self, **_: Any) -> tuple[str, str]:
        self.calls += 1
        return VALID_CODE, f"seeded-repair-{self.calls}"


def make_agent(
    agentc: Any,
    *,
    auto: SeededAutoformalizer,
    hard: SeededHardCritic,
    max_iterations: int = 1,
):
    formal_refiner = SeededRefiner()
    informal_refiner = SeededRefiner()
    agent = agentc.IterativeSelfRefinementAgentC(
        autoformalizer=auto,
        hard_critique=hard,
        soft_critique=SeededSoftCritic(),
        formal_refiner=formal_refiner,
        informal_refiner=informal_refiner,
        aspect_description="seeded semantic preservation",
        max_iterations=max_iterations,
        default_first_formalization_cycles=1,
        default_target_compatibility_score=None,
        default_max_score_gated_cycles=1,
        enable_llm_refinement_taxonomy=False,
    )
    return agent, formal_refiner, informal_refiner


def workflow_kwargs(case_id: str) -> dict[str, Any]:
    case_root = ARTIFACT_ROOT / case_id
    return {
        "output_file": case_root / "result.lean",
        "report_file": case_root / "report.json",
        "history_file": case_root / "history.json",
        "reasoning_log_file": case_root / "reasoning.jsonl",
        "file_prefix": case_id,
        "normalize_input": True,
        "enable_concept_mapping": False,
        "enable_mathlib_concept_compatibility_loop": False,
        "enable_llm_judges": False,
        "include_dependency_context": False,
        "enforce_mathlib_alignment": False,
        "enable_latex_expansion": False,
        "enable_compatibility_audit": False,
        "enable_lean_consistency_report": False,
        "enable_default_multi_cycle": False,
        "record_round_versions": False,
        "enable_reasoning_log": False,
    }


def run_suite() -> dict[str, Any]:
    agentc = load_agentc()
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    cases: dict[str, dict[str, Any]] = {}

    auto = SeededAutoformalizer()
    hard = SeededHardCritic()
    agent, _, _ = make_agent(agentc, auto=auto, hard=hard)
    report = agent.run_systematic_workflow(
        "Prove that True.", **workflow_kwargs("success")
    )
    cases["success"] = {
        "ok": report.final_correctness == "True"
        and report.final_saved_file_correctness == "True"
        and Path(report.output_file).exists(),
        "history_length": len(
            json.loads(Path(report.history_file).read_text(encoding="utf-8"))
        ),
        "provider_calls": auto.calls,
    }

    repair_auto = SeededAutoformalizer(
        code="import Mathlib\n\nexample : True := by trivial\n"
    )
    repair_hard = SeededHardCritic(fail_count=2)
    repair_agent, formal_refiner, _ = make_agent(
        agentc, auto=repair_auto, hard=repair_hard
    )
    repaired = repair_agent.run_systematic_workflow(
        "Repair a compile failure.", **workflow_kwargs("repair")
    )
    repaired_history = json.loads(
        Path(repaired.history_file).read_text(encoding="utf-8")
    )
    cases["compile_failure_repair"] = {
        "ok": repaired.final_correctness == "True"
        and formal_refiner.calls == 1
        and len(repaired_history) >= 2,
        "hard_critic_calls": repair_hard.calls,
        "formal_refiner_calls": formal_refiner.calls,
    }

    failure_agent, _, _ = make_agent(
        agentc,
        auto=SeededAutoformalizer(error=RuntimeError("seeded provider failure")),
        hard=SeededHardCritic(),
    )
    provider_error = None
    try:
        failure_agent.run_systematic_workflow(
            "Provider failure.", **workflow_kwargs("provider_failure")
        )
    except RuntimeError as exc:
        provider_error = str(exc)
    cases["provider_failure"] = {
        "ok": provider_error == "seeded provider failure",
        "error": provider_error,
    }

    timeout_agent, _, _ = make_agent(
        agentc,
        auto=SeededAutoformalizer(error=TimeoutError("seeded provider timeout")),
        hard=SeededHardCritic(),
    )
    timeout_error = None
    try:
        timeout_agent.run_systematic_workflow(
            "Provider timeout.", **workflow_kwargs("provider_timeout")
        )
    except TimeoutError as exc:
        timeout_error = str(exc)
    cases["provider_timeout"] = {
        "ok": timeout_error == "seeded provider timeout",
        "error": timeout_error,
    }

    cycle_agent, _, _ = make_agent(
        agentc,
        auto=SeededAutoformalizer(),
        hard=SeededHardCritic(),
    )
    cycle_error = None
    normalized = agentc.normalize_informal_statement("Cyclic prerequisite.")
    try:
        cycle_agent.run_systematic_workflow(
            "Cyclic prerequisite.",
            **workflow_kwargs("dependency_cycle"),
            _dependency_stack={normalized},
        )
    except ValueError as exc:
        cycle_error = str(exc)
    cases["dependency_cycle"] = {
        "ok": bool(cycle_error and "Cyclic dependency detected" in cycle_error),
        "error": cycle_error,
    }

    payload = {
        "schema_version": 1,
        "suite": "agentc_systematic_workflow_e2e",
        "ok": all(case["ok"] for case in cases.values()),
        "cases": cases,
    }
    (ARTIFACT_ROOT / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = run_suite()
    print(
        json.dumps(payload, indent=2, sort_keys=True)
        if args.json
        else ("PASS" if payload["ok"] else "FAIL")
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

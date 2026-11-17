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

"""Inventory Mathformer skills and classify deterministic/generative test profiles."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILLS_DIR = REPO_ROOT / "skills"
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

GENERATIVE_MARKERS = {
    "agent",
    "autoformalization",
    "critique",
    "critic",
    "draft",
    "expander",
    "generative",
    "judge",
    "judgement",
    "orchestrator",
    "planner",
    "prompt",
    "refinement",
    "review",
    "semantic",
    "web research",
}

DETERMINISTIC_MARKERS = {
    "audit",
    "benchmark",
    "check",
    "compile",
    "deterministic",
    "execute",
    "inventory",
    "jsonl",
    "lean",
    "navigate",
    "run",
    "schema",
    "script",
    "validate",
    "verify",
}

CONTENT_REQUIRED_NAMES = {
    "mathformer-generative-workflow-coordinator",
    "latex-prerequisite-expander",
    "latex-expansion-completeness-reviewer",
    "latex-expansion-binding-reviewer",
    "latex-expansion-review-orchestrator",
    "proof-expansion-web-researcher",
    "proof-expansion-support-orchestrator",
    "lean-autoformalization-drafter",
    "lean-formal-refinement",
    "lean-critique-and-judging",
    "lean-critique-suite-orchestrator",
    "lean-syntactic-correctness-critic",
    "lean-semantic-preservation-critic",
    "lean-logical-soundness-critic",
    "lean-mathlib-alignment-critic",
    "lean-output-denoiser",
    "lean-refinement-taxonomy",
    "lean-line-annotation",
    "mathlib-api-compatibility-planner",
    "mathlib-compatibility-loop-orchestrator",
    "mathlib-web-grounding-orchestrator",
    "autoformalization-workflow-orchestrator",
    "autoformalization-agentc",
    "autoformalization-reflective-refinement-loop",
}


def infer_theme(name: str) -> str:
    """Return the thematic skill bucket used by one-level skill views."""
    if name in {
        "gate-policy-controller",
        "mathformer-generative-workflow-coordinator",
        "mathformer-workflow-router",
        "reasoning-flow-language",
        "workflow-contract-validator",
        "skill-hook-coverage-maximizer",
        "skill-test-program-orchestrator",
        "reasoning-log-schema-guardian",
    }:
        return "control"
    if name.startswith("formalphysics-"):
        return "physics-common"
    if name.startswith(
        (
            "autoformalization-",
            "final-derivation-",
            "mathematical-final-",
            "result-existence-",
            "proof-expansion-",
            "source-",
        )
    ):
        return "autoformalization"
    if name.startswith("lean-"):
        return "lean"
    if name.startswith("mathlib-") or name == "informal-proof-mathlib-concepts":
        return "mathlib"
    if name.startswith("mathformerlib-") or name.startswith("mathformer-library-"):
        return "mathformerlib"
    if name.startswith("mathformerphysicslib-"):
        return "mathformerphysicslib"
    if name.startswith("physics-lean-"):
        return "physics-lean"
    if name.startswith("physics-sympy-"):
        return "physics-sympy"
    if name.startswith("physics-isabelle-"):
        return "physics-isabelle"
    if name.startswith("physics-"):
        return "physics-common"
    if name.startswith("sympy-") or name.startswith("mathematical-sympy-"):
        return "sympy"
    if name.startswith(("isabelle-", "isarmathlib-", "mathematical-isabelle-")):
        return "isabelle"
    if name.startswith("rocq-"):
        return "rocq"
    if name.startswith("vampire-"):
        return "atp"
    if name.startswith("premise-kb-"):
        return "premise-kb"
    if name.startswith("proofnet-"):
        return "benchmarks"
    if name.startswith("paper-"):
        return "paper"
    if name.startswith(("latex-", "textbook-")):
        return "latex-textbook"
    if name.startswith("reference-free-"):
        return "rfde"
    return "misc"


def parse_frontmatter(text: str) -> Dict[str, str]:
    """Document the responsibility of ``parse_frontmatter``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    body = text[3:end].strip()
    result: Dict[str, str] = {}
    current_key: Optional[str] = None
    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        if raw_line.startswith(" ") and current_key:
            result[current_key] = result[current_key] + " " + raw_line.strip()
            continue
        if ":" in raw_line:
            key, value = raw_line.split(":", 1)
            current_key = key.strip()
            result[current_key] = value.strip().strip('"')
    return result


def parse_hooks_manifest(path: Path) -> Dict[str, Any]:
    """Document the responsibility of ``parse_hooks_manifest``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Parse caller-provided input into the structured representation expected by downstream code.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    owner_hooks: Dict[str, List[str]] = defaultdict(list)
    direct_routes: Dict[str, str] = {}
    current_section: Optional[str] = None
    current_hook: Optional[str] = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "hooks:":
            current_section = "hooks"
            current_hook = None
            continue
        if stripped == "loop_contracts:":
            current_section = "loop_contracts"
            current_hook = None
            continue
        if stripped == "direct_request_routing:":
            current_section = "routing"
            current_hook = None
            continue
        hook_match = re.match(r"^-\s+id:\s*(\S+)\s*$", stripped)
        if current_section == "hooks" and hook_match:
            current_hook = hook_match.group(1)
            continue
        if (
            current_section == "hooks"
            and current_hook
            and stripped.startswith("owner_skill:")
        ):
            owner = stripped.split(":", 1)[1].strip()
            owner_hooks[owner].append(current_hook)
            continue
        if current_section == "routing" and ":" in stripped:
            key, value = stripped.split(":", 1)
            direct_routes[key.strip()] = value.strip()
    return {"owner_hooks": owner_hooks, "direct_routes": direct_routes}


def classify_skill(
    name: str,
    description: str,
    *,
    has_scripts: bool,
    hook_ids: Sequence[str],
) -> Dict[str, Any]:
    """Document the responsibility of ``classify_skill``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``classify_skill`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text = f"{name} {description}".lower().replace("-", " ")
    generative_score = sum(1 for marker in GENERATIVE_MARKERS if marker in text)
    deterministic_score = sum(1 for marker in DETERMINISTIC_MARKERS if marker in text)
    if name in CONTENT_REQUIRED_NAMES:
        generative_score += 3
    if has_scripts:
        deterministic_score += 2
    if any(
        hook.startswith(("control.", "mathlib.", "check.", "execute.", "benchmark."))
        for hook in hook_ids
    ):
        deterministic_score += 1
    if any(
        hook.startswith(
            ("draft.", "critique.", "refine.", "preformalization.", "reflection.")
        )
        for hook in hook_ids
    ):
        generative_score += 1

    if generative_score >= 3 and deterministic_score >= 3:
        profile = "hybrid"
    elif generative_score >= 3:
        profile = "generative"
    else:
        profile = "deterministic"

    return {
        "test_profile": profile,
        "generative_score": generative_score,
        "deterministic_score": deterministic_score,
        "requires_codex_exec_content_probe": profile in {"generative", "hybrid"},
    }


def inventory(skills_dir: Path = SKILLS_DIR) -> Dict[str, Any]:
    """Document the responsibility of ``inventory``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``inventory`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    hooks_manifest = parse_hooks_manifest(skills_dir / "SKILL_HOOKS.yaml")
    owner_hooks = hooks_manifest["owner_hooks"]
    routed_targets = Counter(hooks_manifest["direct_routes"].values())

    skills: List[Dict[str, Any]] = []
    for skill_file in sorted(skills_dir.glob("*/*/SKILL.md")):
        skill_dir = skill_file.parent
        text = skill_file.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        name = frontmatter.get("name") or skill_dir.name
        description = frontmatter.get("description", "")
        scripts = (
            sorted(
                str(path.relative_to(REPO_ROOT))
                for path in (skill_dir / "scripts").glob("*.py")
            )
            if (skill_dir / "scripts").exists()
            else []
        )
        references = (
            sorted(
                str(path.relative_to(REPO_ROOT))
                for path in (skill_dir / "references").glob("*")
                if path.is_file()
            )
            if (skill_dir / "references").exists()
            else []
        )
        agents = (
            sorted(
                str(path.relative_to(REPO_ROOT))
                for path in (skill_dir / "agents").glob("*")
                if path.is_file()
            )
            if (skill_dir / "agents").exists()
            else []
        )
        hook_ids = owner_hooks.get(name, [])
        classification = classify_skill(
            name,
            description,
            has_scripts=bool(scripts),
            hook_ids=hook_ids,
        )
        skills.append(
            {
                "name": name,
                "path": str(skill_file.relative_to(REPO_ROOT)),
                "theme": infer_theme(name),
                "description": description,
                "scripts": scripts,
                "references": references,
                "agents": agents,
                "hook_ids": hook_ids,
                "direct_route_count": routed_targets.get(name, 0),
                **classification,
            }
        )

    counts = Counter(item["test_profile"] for item in skills)
    theme_counts = Counter(item["theme"] for item in skills)
    return {
        "skill_count": len(skills),
        "profile_counts": dict(counts),
        "theme_counts": dict(sorted(theme_counts.items())),
        "codex_exec_probe_required_count": sum(
            1 for item in skills if item["requires_codex_exec_content_probe"]
        ),
        "skills": skills,
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
    lines = [
        f"skills: {report['skill_count']}",
        f"profiles: {report['profile_counts']}",
        f"themes: {report['theme_counts']}",
        f"codex_exec_required: {report['codex_exec_probe_required_count']}",
    ]
    for item in report["skills"]:
        lines.append(
            f"- {item['name']}: {item['theme']} / {item['test_profile']} "
            f"scripts={len(item['scripts'])} hooks={len(item['hook_ids'])}"
        )
    return "\n".join(lines)


def append_event(reasoning_log: Optional[Path], report: Dict[str, Any]) -> None:
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
        step="skill_test_inventory_complete",
        payload={
            "skill": SKILL_NAME,
            "hook_id": HOOK_ID,
            "skill_count": report["skill_count"],
            "profile_counts": report["profile_counts"],
            "theme_counts": report["theme_counts"],
            "codex_exec_probe_required_count": report[
                "codex_exec_probe_required_count"
            ],
        },
    )


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
    parser.add_argument("--skills-dir", type=Path, default=SKILLS_DIR)
    parser.add_argument("--output-file", type=Path)
    parser.add_argument(
        "--reasoning-log-file",
        type=Path,
        default=Path("artifacts/skill_test_program/reasoning.jsonl"),
    )
    parser.add_argument("--no-reasoning-log", action="store_true")
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
    report = inventory(args.skills_dir)
    reasoning_log = (
        None
        if args.no_reasoning_log
        else (REPO_ROOT / args.reasoning_log_file).resolve()
    )
    append_event(reasoning_log, report)
    if args.output_file is not None:
        output_file = (REPO_ROOT / args.output_file).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

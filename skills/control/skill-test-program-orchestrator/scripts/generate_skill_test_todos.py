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

"""Generate self-explanatory TODOs for Mathformer skill testing coverage."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
REASONING_LOG_SCRIPTS = (
    REPO_ROOT / "skills" / "control" / "reasoning-log-schema-guardian" / "scripts"
)
if str(REASONING_LOG_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REASONING_LOG_SCRIPTS))

from inventory_skills import inventory
from reasoning_log import (
    append_reasoning_log_entry,
)

SKILL_NAME = "skill-test-program-orchestrator"
HOOK_ID = "test.skill_program"


def load_optional_json(path: Path) -> Optional[Dict[str, Any]]:
    """Document the responsibility of ``load_optional_json``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Load data from the declared source while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not path.exists():
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else None


def todo(
    *,
    priority: str,
    owner: str,
    title: str,
    why: str,
    done_when: str,
    command: str,
) -> Dict[str, str]:
    """Document the responsibility of ``todo``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``todo`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return {
        "status": "todo",
        "priority": priority,
        "owner": owner,
        "title": title,
        "why": why,
        "done_when": done_when,
        "command": command,
    }


def content_probe_skills(content_report: Optional[Dict[str, Any]]) -> set[str]:
    """Document the responsibility of ``content_probe_skills``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``content_probe_skills`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not content_report:
        return set()
    return {
        str(item.get("skill"))
        for item in content_report.get("results", [])
        if item.get("skill") and item.get("ok")
    }


def declared_probe_skills(probes_file: Path) -> set[str]:
    """Document the responsibility of ``declared_probe_skills``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``declared_probe_skills`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not probes_file.exists():
        return set()
    parsed = json.loads(probes_file.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        return set()
    return {
        str(item.get("skill"))
        for item in parsed.get("probes", [])
        if isinstance(item, dict) and item.get("skill")
    }


def build_todos(
    *,
    inventory_report: Dict[str, Any],
    deterministic_report: Optional[Dict[str, Any]],
    content_report: Optional[Dict[str, Any]],
    declared_content_probe_skills: set[str],
) -> List[Dict[str, str]]:
    """Document the responsibility of ``build_todos``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    todos: List[Dict[str, str]] = []
    if deterministic_report is None:
        todos.append(
            todo(
                priority="P0",
                owner="skill-test-program-orchestrator",
                title="Run the deterministic skill-test lane and capture a report",
                why="Without a deterministic baseline, content-test failures are hard to localize and hook/schema drift can hide behind generative behavior.",
                done_when="artifacts/skill_test_program/deterministic_report.json exists and has ok=true.",
                command="python skills/control/skill-test-program-orchestrator/scripts/run_deterministic_skill_tests.py --include-slow --json",
            )
        )
    elif not deterministic_report.get("ok"):
        for result in deterministic_report.get("results", []):
            if result.get("required") and not result.get("ok"):
                todos.append(
                    todo(
                        priority="P0",
                        owner="skill-test-program-orchestrator",
                        title=f"Fix blocking deterministic check: {result.get('id')}",
                        why="Required deterministic checks protect the hook contract, Lean baseline, suite evidence, and schema validity.",
                        done_when=f"The check `{result.get('id')}` passes in the deterministic report.",
                        command=" ".join(str(part) for part in result.get("cmd", [])),
                    )
                )

    if content_report is None:
        todos.append(
            todo(
                priority="P0",
                owner="skill-test-program-orchestrator",
                title="Run at least one Codex-exec content smoke probe",
                why="Generative skills can pass structural checks while failing semantic fidelity, critique usefulness, or mathematical discipline.",
                done_when="artifacts/skill_test_program/content_report.json exists with at least one executed passing probe.",
                command="python skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py --execute --limit 1 --json",
            )
        )
    elif not content_report.get("ok"):
        for result in content_report.get("results", []):
            if not result.get("ok"):
                todos.append(
                    todo(
                        priority="P1",
                        owner=str(
                            result.get("skill") or "skill-test-program-orchestrator"
                        ),
                        title=f"Repair failing Codex-exec content probe: {result.get('id')}",
                        why="The probe is an executable generative regression; its oracle captures a concrete content-quality expectation.",
                        done_when=f"Probe `{result.get('id')}` passes with --execute.",
                        command=(
                            "python skills/control/skill-test-program-orchestrator/scripts/"
                            f"run_content_skill_codex_exec_tests.py --execute --skill {result.get('skill')} --json"
                        ),
                    )
                )

    probed = content_probe_skills(content_report)
    for skill in inventory_report.get("skills", []):
        if (
            skill.get("requires_codex_exec_content_probe")
            and skill["name"] not in probed
        ):
            has_declared_probe = skill["name"] in declared_content_probe_skills
            title = (
                f"Execute the existing Codex-exec content probe for {skill['name']}"
                if has_declared_probe
                else f"Add and execute a Codex-exec content probe for {skill['name']}"
            )
            done_when = (
                "The existing probe in content_probes.json is executed and the content report records ok=true for it."
                if has_declared_probe
                else (
                    "A probe in content_probes.json targets this skill and an executed "
                    "content report records ok=true for it."
                )
            )
            todos.append(
                todo(
                    priority="P2",
                    owner=skill["name"],
                    title=title,
                    why=(
                        f"{skill['name']} is classified as {skill['test_profile']}, "
                        "so deterministic checks are not enough to validate prompt behavior."
                    ),
                    done_when=done_when,
                    command=(
                        "python skills/control/skill-test-program-orchestrator/scripts/"
                        f"run_content_skill_codex_exec_tests.py --execute --skill {skill['name']} --json"
                    ),
                )
            )

    if not todos:
        todos.append(
            todo(
                priority="P3",
                owner="skill-test-program-orchestrator",
                title="Expand adversarial content probes beyond the smoke set",
                why="The current testing surface is green; the next gains come from harder ambiguity and semantic-preservation probes.",
                done_when="At least one new adversarial probe family is added and executed successfully.",
                command="python skills/control/skill-test-program-orchestrator/scripts/run_content_skill_codex_exec_tests.py --execute --json",
            )
        )
    return todos


def render_markdown(todos: Sequence[Dict[str, str]]) -> str:
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
    lines = [
        "# Skill Testing TODOs",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "Each TODO states why it exists, what proves it done, and the command to run.",
        "",
    ]
    for index, item in enumerate(todos, 1):
        lines.extend(
            [
                f"## {index}. [{item['priority']}] {item['title']}",
                "",
                f"- Status: {item['status']}",
                f"- Owner: `{item['owner']}`",
                f"- Why: {item['why']}",
                f"- Done when: {item['done_when']}",
                f"- Command: `{item['command']}`",
                "",
            ]
        )
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
    parser.add_argument(
        "--deterministic-report",
        type=Path,
        default=Path("artifacts/skill_test_program/deterministic_report.json"),
    )
    parser.add_argument(
        "--content-report",
        type=Path,
        default=Path("artifacts/skill_test_program/content_report.json"),
    )
    parser.add_argument(
        "--probes-file",
        type=Path,
        default=Path(
            "skills/control/skill-test-program-orchestrator/references/content_probes.json"
        ),
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        default=Path("docs/archive/SKILL_TESTING_TODOS.md"),
    )
    parser.add_argument(
        "--json-output-file",
        type=Path,
        default=Path("artifacts/skill_test_program/todos.json"),
    )
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
    inventory_report = inventory()
    deterministic_report = load_optional_json(REPO_ROOT / args.deterministic_report)
    content_report = load_optional_json(REPO_ROOT / args.content_report)
    declared_content_probe_skills = declared_probe_skills(REPO_ROOT / args.probes_file)
    todos = build_todos(
        inventory_report=inventory_report,
        deterministic_report=deterministic_report,
        content_report=content_report,
        declared_content_probe_skills=declared_content_probe_skills,
    )
    output_file = (REPO_ROOT / args.output_file).resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(render_markdown(todos), encoding="utf-8")
    json_output_file = (REPO_ROOT / args.json_output_file).resolve()
    json_output_file.parent.mkdir(parents=True, exist_ok=True)
    json_output_file.write_text(
        json.dumps({"todos": todos}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not args.no_reasoning_log:
        append_reasoning_log_entry(
            REPO_ROOT / args.reasoning_log_file,
            step="skill_test_todos_generated",
            payload={
                "skill": SKILL_NAME,
                "hook_id": HOOK_ID,
                "todo_count": len(todos),
                "output_file": rel(output_file),
                "json_output_file": rel(json_output_file),
            },
        )
    if args.json:
        print(json.dumps({"todos": todos}, ensure_ascii=False, indent=2))
    else:
        print(f"wrote {rel(output_file)} with {len(todos)} todos")
    return 0


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


if __name__ == "__main__":
    sys.exit(main())

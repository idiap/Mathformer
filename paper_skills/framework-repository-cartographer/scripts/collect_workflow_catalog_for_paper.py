#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Paper-writing agents need a compact, reproducible workflow catalogue rather
#   than ad hoc prose copied from the workflow graph HTML report.
#
# Intent:
#   Convert the generated workflow graph JSON into paper-ready JSON, Markdown,
#   and LaTeX appendix snippets that distinguish core workflows, support
#   workflows, hook counts, families, and reflective loops.
#
# Function:
#   Reads `artifacts/workflow_graphs/workflow_graphs.json`, classifies the
#   workflow stacks, and writes summary artifacts under `artifacts/paper_skills/`.
#
# Maintenance Notes:
#   Keep the classification names synchronized with the terminology in
#   `paper/MATHFORMER_FRAMEWORK_PAPER.tex` and `docs/architecture/AGENTIC_HUB.md`.

"""Collect workflow graph evidence into paper-ready catalogue artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_GRAPH = REPO_ROOT / "artifacts" / "workflow_graphs" / "workflow_graphs.json"
DEFAULT_OUTPUT = (
    REPO_ROOT / "artifacts" / "paper_skills" / "workflow_catalog_for_paper.json"
)

CORE_WORKFLOW_IDS = {
    "preformalization-readiness-loop",
    "textbook-theory-autoformalization-loop",
    "mathlib-grounding-loop",
    "draft-execute-refine-loop",
    "artifact-acceptance-loop",
    "lean-consistency-testing-loop",
    "sympy-equational-trace-loop",
    "sympy-physics-derivation-trace-loop",
    "lean-physics-derivation-trace-loop",
    "isabelle-physics-derivation-trace-loop",
    "premise-selection-loop",
}


def latex_escape(value: str) -> str:
    """Escape a short string for use in generated LaTeX tables."""

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in value)


def relation_for_workflow(stack_id: str, family: str) -> str:
    """Map a workflow stack to the paper's transition-relation vocabulary."""

    if "preformalization" in stack_id or "textbook" in stack_id:
        return r"$\Rel_{\mathrm{intake}}, \Rel_{\mathrm{expand}}$"
    if "mathlib" in stack_id:
        return r"$\Rel_{\mathrm{ground}}$"
    if "draft-execute-refine" in stack_id:
        return (
            r"$\Rel_{\mathrm{draft}}, \Rel_{\mathrm{execute}}, \Rel_{\mathrm{repair}}$"
        )
    if "artifact-acceptance" in stack_id or "consistency" in stack_id:
        return r"$\Rel_{\mathrm{consistency}}$"
    if "physics" in stack_id:
        if "sympy" in stack_id:
            return r"$\Rel_{\mathrm{physics}}, \Rel_{\mathrm{symbolic}}$"
        return r"$\Rel_{\mathrm{physics}}$"
    if "premise" in stack_id:
        return r"$\Rel_{\mathrm{premise}}, \Rel_{\mathrm{atp}}$"
    if "sympy" in stack_id:
        return r"$\Rel_{\mathrm{symbolic}}$"
    if "workflow-graph" in stack_id:
        return r"$\Rel_{\mathrm{observe}}, \Rel_{\mathrm{reflect}}$"
    if "reflection" in stack_id:
        return r"$\Rel_{\mathrm{reflect}}$"
    if "control" in family.lower():
        return r"$\Rel_{\mathrm{control}}$"
    return r"$\Rel_{\mathrm{support}}$"


def load_model(path: Path) -> dict[str, Any]:
    """Load the generated workflow graph JSON model."""

    return json.loads(path.read_text(encoding="utf-8"))


def catalogue(model: dict[str, Any]) -> dict[str, Any]:
    """Build the paper catalogue from a workflow graph model."""

    workflows: list[dict[str, Any]] = []
    for stack_id, stack in model["stacks"].items():
        hook_count = len(stack.get("ordered_hooks", []))
        workflows.append(
            {
                "id": stack_id,
                "label": stack["label"],
                "family": stack["family"],
                "kind": "core" if stack_id in CORE_WORKFLOW_IDS else "support",
                "hook_count": hook_count,
                "reflective": bool(stack.get("reflective_edges")),
                "transition_relation": relation_for_workflow(stack_id, stack["family"]),
                "description": stack.get("description", ""),
                "first_hooks": [
                    {
                        "index": hook["index"],
                        "skill": hook["skill"],
                        "role": hook["role"],
                        "output_type": hook["output_type"],
                    }
                    for hook in stack.get("ordered_hooks", [])[:5]
                ],
            }
        )
    return {
        "schema_version": 1,
        "source_graph": "artifacts/workflow_graphs/workflow_graphs.json",
        "source_html": "artifacts/workflow_graphs/workflow_graphs.html",
        "summary": model["summary"],
        "core_workflow_count": sum(1 for item in workflows if item["kind"] == "core"),
        "support_workflow_count": sum(
            1 for item in workflows if item["kind"] == "support"
        ),
        "workflows": workflows,
    }


def markdown_report(packet: dict[str, Any]) -> str:
    """Render a compact Markdown workflow catalogue."""

    summary = packet["summary"]
    lines = [
        "<!--",
        "# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>",
        "#",
        "# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>",
        "# Neuro-symbolic AI Group",
        "#",
        # REUSE-IgnoreStart
        "# SPDX-License-Identifier: MIT",
        # REUSE-IgnoreEnd
        "-->",
        "",
        "# Workflow Catalogue For Paper",
        "",
        f"Source graph: `{packet['source_graph']}`",
        "",
        "## Summary",
        "",
        f"- Workflow stacks: {summary['stacks']}",
        f"- Total hooks: {summary['total_hooks']}",
        f"- Modeled skills: {summary['modeled_skills']} / {summary['available_skills']}",
        f"- Shared skills: {summary['shared_skills']}",
        f"- Reflective stacks: {summary['reflective_stacks']}",
        f"- Families: {summary['families']}",
        "",
        "## Workflows",
        "",
        "| Workflow | Family | Kind | Hooks | Relation | Reflective |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for workflow in packet["workflows"]:
        lines.append(
            "| {label} | {family} | {kind} | {hook_count} | {relation} | {reflective} |".format(
                label=workflow["label"],
                family=workflow["family"],
                kind=workflow["kind"],
                hook_count=workflow["hook_count"],
                relation=workflow["transition_relation"].replace("\\", "\\\\"),
                reflective="yes" if workflow["reflective"] else "no",
            )
        )
    lines.append("")
    return "\n".join(lines)


def latex_table(packet: dict[str, Any]) -> str:
    """Render a LaTeX appendix table for the workflow catalogue."""

    lines = [
        "% Auto-generated by paper_skills/framework-repository-cartographer/scripts/collect_workflow_catalog_for_paper.py",
        r"\begin{longtable}{L{0.24\linewidth}L{0.23\linewidth}L{0.12\linewidth}L{0.09\linewidth}L{0.20\linewidth}}",
        r"\caption{Workflow catalogue extracted from the generated workflow graph report.}",
        r"\label{tab:workflow-catalog-appendix}\\",
        r"\toprule",
        r"Workflow & Family & Kind & Hooks & Transition view \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Workflow & Family & Kind & Hooks & Transition view \\",
        r"\midrule",
        r"\endhead",
    ]
    for workflow in packet["workflows"]:
        reflective = " + reflection" if workflow["reflective"] else ""
        lines.append(
            "{label} & {family} & {kind} & {hooks} & {relation}{reflective} \\\\".format(
                label=latex_escape(workflow["label"]),
                family=latex_escape(workflow["family"]),
                kind=latex_escape(workflow["kind"]),
                hooks=workflow["hook_count"],
                relation=workflow["transition_relation"],
                reflective=reflective,
            )
        )
    lines.extend([r"\bottomrule", r"\end{longtable}", ""])
    return "\n".join(lines)


def write_outputs(
    packet: dict[str, Any], output: Path, repository_root: Path | None = None
) -> dict[str, Any]:
    """Write JSON, Markdown, and LaTeX catalogue artifacts."""

    root = REPO_ROOT if repository_root is None else repository_root
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    md_output = output.with_suffix(".md")
    tex_output = output.with_suffix(".tex")
    md_output.write_text(markdown_report(packet), encoding="utf-8")
    tex_output.write_text(latex_table(packet), encoding="utf-8")
    return {
        "ok": True,
        "json_output": str(output.relative_to(root)),
        "markdown_output": str(md_output.relative_to(root)),
        "latex_output": str(tex_output.relative_to(root)),
        "workflow_count": len(packet["workflows"]),
        "core_workflow_count": packet["core_workflow_count"],
        "support_workflow_count": packet["support_workflow_count"],
    }


def parse_paths(
    argv: list[str] | None = None, repository_root: Path | None = None
) -> dict[str, Any]:
    """Parse the native CLI and resolve paths against its repository mount."""

    root = REPO_ROOT if repository_root is None else repository_root
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--graph", type=Path, default=root / DEFAULT_GRAPH.relative_to(REPO_ROOT)
    )
    parser.add_argument(
        "--output", type=Path, default=root / DEFAULT_OUTPUT.relative_to(REPO_ROOT)
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    graph_path = args.graph if args.graph.is_absolute() else root / args.graph
    output_path = args.output if args.output.is_absolute() else root / args.output
    return {"graph": str(graph_path), "output": str(output_path), "json": args.json}


def emit_result(result: dict[str, Any], json_output: bool) -> int:
    """Preserve the CLI's output and exit status for both native consumers."""
    if json_output:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Wrote {result['json_output']}")
    return 0


def main() -> int:
    """CLI entry point using the same steps exposed over MCP."""
    paths = parse_paths()
    packet = catalogue(load_model(Path(paths["graph"])))
    result = write_outputs(packet, Path(paths["output"]))
    return emit_result(result, paths["json"])


if __name__ == "__main__":
    raise SystemExit(main())

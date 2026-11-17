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

"""Build per-unit textbook autoformalization jobs without mocking Lean results."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[4]
LINE_PACKET_SCRIPT_DIR = (
    REPO_ROOT
    / "skills"
    / "autoformalization"
    / "source-line-translation-packet-builder"
    / "scripts"
)
if str(LINE_PACKET_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(LINE_PACKET_SCRIPT_DIR))

from build_line_translation_packet import (
    build_packet,
)

DEFAULT_TARGET_KINDS: Set[str] = {
    "definition",
    "theorem",
    "lemma",
    "corollary",
    "proposition",
    "assumption",
    "notation",
    "claim",
    "condition",
    "construction",
    "criterion",
    "conclusion",
    "axiom",
    "conjecture",
}

REQUIRED_GATES = [
    "intake.source_unit_inventory",
    "preformalization.line_translation_packet",
    "preformalization.result_existence_precheck",
    "mathlib.grounding_maximize",
    "execute.initial",
    "check.compile",
    "postformalization.source_anchor_drift_guard",
    "artifact.realness_gate",
    "postformalization.informalize",
    "postformalization.informal_internal_consistency",
    "postformalization.informal_consistency",
    "consistency.declaration_shape",
    "consistency.nonvacuity",
    "consistency.cross_file_concepts",
    "consistency.unified_report",
]


def slugify(value: str, default: str = "job") -> str:
    """Document the responsibility of ``slugify``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``slugify`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-").lower()
    return slug[:96] or default


def load_json(path: Path) -> Dict[str, Any]:
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
    return json.loads(path.read_text(encoding="utf-8"))


def bundle_index(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Document the responsibility of ``bundle_index``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``bundle_index`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    index: Dict[str, Dict[str, Any]] = {}
    for bundle in manifest.get("bundles", []):
        for unit_id in bundle.get("unit_ids", []):
            index[unit_id] = bundle
    return index


def source_title(unit: Dict[str, Any]) -> str:
    """Document the responsibility of ``source_title``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``source_title`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return (
        unit.get("title")
        or unit.get("label")
        or f"{unit.get('kind')} at {unit.get('file')}:{unit.get('line_start')}"
    )


def prompt_for_job(job: Dict[str, Any]) -> str:
    """Document the responsibility of ``prompt_for_job``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``prompt_for_job`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    statement = job["source_statement_latex"].rstrip()
    proof = job.get("paired_proof_latex", "").rstrip()
    proof_block = (
        proof
        if proof
        else "No paired proof was extracted; preserve this as an explicit proof gap."
    )
    proof_for = (
        f"- Proof for unit: `{job['proof_for_unit_id']}`\n\n"
        if job.get("proof_for_unit_id")
        else ""
    )
    line_packet = job.get("line_translation_packet") or {}
    line_context = line_packet.get("lean_prompt_context", "")
    line_block = (
        "\n## Line Translation Packet\n\n"
        "Use these literal source anchors when writing source-aware Lean declaration comments.\n\n"
        "```text\n"
        f"{line_context}\n"
        "```\n"
        if line_context
        else ""
    )
    return (
        f"# Textbook Autoformalization Job: {job['job_id']}\n\n"
        f"Status: `{job['status']}`\n\n"
        "Use `autoformalization-workflow-orchestrator` and the required gates listed in the job JSON. "
        "Do not create placeholder Lean, target axioms, `sorry`, `admit`, or completion claims.\n\n"
        "## Source Metadata\n\n"
        f"- Unit id: `{job['source_unit_id']}`\n"
        f"- Kind: `{job['target_kind']}`\n"
        f"- Source: `{job['source_file']}:{job['line_start']}-{job['line_end']}`\n"
        f"- Bundle: `{job.get('bundle_id')}`\n\n"
        f"{proof_for}"
        "## Source Statement TeX\n\n"
        "```tex\n"
        f"{statement}\n"
        "```\n\n"
        "## Paired Proof TeX\n\n"
        "```tex\n"
        f"{proof_block}\n"
        "```\n"
        f"{line_block}"
    )


def attach_line_translation_packet(job: Dict[str, Any]) -> None:
    """Document the responsibility of ``attach_line_translation_packet``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``attach_line_translation_packet`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    text_parts = [job.get("source_statement_latex", "")]
    if job.get("paired_proof_latex"):
        text_parts.append(job["paired_proof_latex"])
    text = "\n".join(part.strip() for part in text_parts if part and part.strip())
    packet = build_packet(
        text=text,
        title=job.get("source_title") or job["job_id"],
        source_id=job["source_unit_id"],
        input_kind="textbook_job",
    )
    job["line_translation_packet"] = {
        "source": packet["source"],
        "summary": packet["summary"],
        "translation_units": packet["translation_units"],
        "lean_prompt_context": packet["lean_prompt_context"],
    }


def build_jobs(
    theory_report: Dict[str, Any],
    organized_manifest: Dict[str, Any],
    output_dir: Path,
    *,
    target_kinds: Set[str],
    max_jobs: Optional[int],
    include_proof_jobs: bool,
) -> Dict[str, Any]:
    """Document the responsibility of ``build_jobs``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    jobs_dir = output_dir / "jobs"
    prompts_dir = output_dir / "prompts"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)

    units = theory_report.get("units", [])
    unit_by_id = {unit["id"]: unit for unit in units}
    proof_by_target: Dict[str, List[Dict[str, Any]]] = {}
    for unit in units:
        if unit.get("kind") == "proof" and unit.get("proof_for_unit_id"):
            proof_by_target.setdefault(unit["proof_for_unit_id"], []).append(unit)
    bundles = bundle_index(organized_manifest)

    jobs: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for unit in sorted(units, key=lambda item: item.get("source_order", 10**9)):
        kind = unit.get("kind")
        if kind == "proof":
            target = unit_by_id.get(unit.get("proof_for_unit_id"))
            if not include_proof_jobs:
                skipped.append(
                    {
                        "unit_id": unit["id"],
                        "reason": "proof jobs disabled",
                        "status": "proof_attached_only",
                    }
                )
                continue
            if target is None:
                skipped.append(
                    {
                        "unit_id": unit["id"],
                        "reason": "standalone proof without paired target",
                        "status": "support_only",
                    }
                )
                continue
            if max_jobs is not None and len(jobs) >= max_jobs:
                skipped.append(
                    {
                        "unit_id": unit["id"],
                        "reason": "max_jobs reached",
                        "status": "queued_later",
                    }
                )
                continue
            bundle = bundles.get(unit["id"]) or bundles.get(target["id"], {})
            stem = slugify(
                f"{unit['id']}-proof-of-{target.get('label') or source_title(target)}"
            )
            job_id = f"textbook-job-{len(jobs) + 1:05d}-{stem}"
            job = {
                "schema_version": 1,
                "job_id": job_id,
                "status": "queued_proof_autoformalization",
                "source_unit_id": unit["id"],
                "proof_for_unit_id": target["id"],
                "target_kind": "proof",
                "source_title": f"Proof of {source_title(target)}",
                "source_file": unit.get("file"),
                "line_start": unit.get("line_start"),
                "line_end": unit.get("line_end"),
                "statement_file": target.get("file"),
                "statement_line_start": target.get("line_start"),
                "statement_line_end": target.get("line_end"),
                "label": target.get("label"),
                "labels": target.get("labels", []),
                "chapter": unit.get("chapter") or target.get("chapter"),
                "section": unit.get("section") or target.get("section"),
                "subsection": unit.get("subsection") or target.get("subsection"),
                "source_statement_latex": target.get("latex", ""),
                "paired_proof_unit_ids": [unit["id"]],
                "paired_proof_latex": unit.get("latex", ""),
                "bundle_id": bundle.get("bundle_id"),
                "bundle_title": bundle.get("title"),
                "bundle_tex_file": bundle.get("tex_file"),
                "required_workflow_skill": "autoformalization-workflow-orchestrator",
                "required_gates": REQUIRED_GATES,
                "completion_policy": "complete only after the source statement and proof produce saved Lean passing execution, realness, grounding, and consistency gates",
                "recommended_output_stem": stem,
            }
            attach_line_translation_packet(job)
            job_file = jobs_dir / f"{job_id}.json"
            prompt_file = prompts_dir / f"{job_id}.md"
            job["job_file"] = str(job_file)
            job["prompt_file"] = str(prompt_file)
            job_file.write_text(
                json.dumps(job, indent=2, sort_keys=True, ensure_ascii=False),
                encoding="utf-8",
            )
            prompt_file.write_text(prompt_for_job(job), encoding="utf-8")
            jobs.append(job)
            continue
        if kind not in target_kinds:
            skipped.append(
                {
                    "unit_id": unit["id"],
                    "reason": f"kind {kind!r} outside target set",
                    "status": "not_targeted",
                }
            )
            continue
        if max_jobs is not None and len(jobs) >= max_jobs:
            skipped.append(
                {
                    "unit_id": unit["id"],
                    "reason": "max_jobs reached",
                    "status": "queued_later",
                }
            )
            continue

        paired_proofs = proof_by_target.get(unit["id"], [])
        bundle = bundles.get(unit["id"], {})
        stem = slugify(f"{unit['id']}-{source_title(unit)}")
        job_id = f"textbook-job-{len(jobs) + 1:05d}-{stem}"
        paired_proof_latex = "\n\n".join(
            proof.get("latex", "") for proof in paired_proofs
        )
        job = {
            "schema_version": 1,
            "job_id": job_id,
            "status": "queued_autoformalization",
            "source_unit_id": unit["id"],
            "target_kind": kind,
            "source_title": source_title(unit),
            "source_file": unit.get("file"),
            "line_start": unit.get("line_start"),
            "line_end": unit.get("line_end"),
            "label": unit.get("label"),
            "labels": unit.get("labels", []),
            "chapter": unit.get("chapter"),
            "section": unit.get("section"),
            "subsection": unit.get("subsection"),
            "source_statement_latex": unit.get("latex", ""),
            "paired_proof_unit_ids": [proof["id"] for proof in paired_proofs],
            "paired_proof_latex": paired_proof_latex,
            "bundle_id": bundle.get("bundle_id"),
            "bundle_title": bundle.get("title"),
            "bundle_tex_file": bundle.get("tex_file"),
            "required_workflow_skill": "autoformalization-workflow-orchestrator",
            "required_gates": REQUIRED_GATES,
            "completion_policy": "complete only after saved Lean passes execution, realness, grounding, and consistency gates",
            "recommended_output_stem": stem,
        }
        attach_line_translation_packet(job)
        job_file = jobs_dir / f"{job_id}.json"
        prompt_file = prompts_dir / f"{job_id}.md"
        job["job_file"] = str(job_file)
        job["prompt_file"] = str(prompt_file)
        job_file.write_text(
            json.dumps(job, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        prompt_file.write_text(prompt_for_job(job), encoding="utf-8")
        jobs.append(job)

    status_counts = Counter(job["status"] for job in jobs)
    skipped_counts = Counter(item["status"] for item in skipped)
    kind_counts = Counter(job["target_kind"] for job in jobs)
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "theory_units_source": theory_report.get("source_root"),
        "organized_manifest_source": organized_manifest.get("manifest_file"),
        "summary": {
            "job_count": len(jobs),
            "skipped_count": len(skipped),
            "status_counts": dict(sorted(status_counts.items())),
            "skipped_status_counts": dict(sorted(skipped_counts.items())),
            "target_kind_counts": dict(sorted(kind_counts.items())),
        },
        "target_kinds": sorted(target_kinds),
        "required_gates": REQUIRED_GATES,
        "jobs": [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "source_unit_id": job["source_unit_id"],
                "target_kind": job["target_kind"],
                "source_file": job["source_file"],
                "line_start": job["line_start"],
                "line_end": job["line_end"],
                "job_file": job["job_file"],
                "prompt_file": job["prompt_file"],
            }
            for job in jobs
        ],
        "skipped_units": skipped,
    }
    manifest_file = output_dir / "batch_manifest.json"
    manifest["manifest_file"] = str(manifest_file)
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


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
        tmp_path = Path(tmp)
        theory = {
            "source_root": "fixture",
            "units": [
                {
                    "id": "u1",
                    "kind": "theorem",
                    "title": "Toy theorem",
                    "label": "thm:toy",
                    "labels": ["thm:toy"],
                    "file": "chapter.tex",
                    "line_start": 1,
                    "line_end": 3,
                    "chapter": "C",
                    "section": "S",
                    "latex": "\\begin{theorem}\\label{thm:toy}True.\\end{theorem}",
                },
                {
                    "id": "u2",
                    "kind": "proof",
                    "file": "chapter.tex",
                    "line_start": 4,
                    "line_end": 5,
                    "proof_for_unit_id": "u1",
                    "latex": "\\begin{proof}Trivial.\\end{proof}",
                },
            ],
        }
        organized = {
            "manifest_file": "organized.json",
            "bundles": [
                {
                    "bundle_id": "c-s",
                    "title": "C / S",
                    "tex_file": "c-s.tex",
                    "unit_ids": ["u1", "u2"],
                }
            ],
        }
        manifest = build_jobs(
            theory,
            organized,
            tmp_path / "out",
            target_kinds=DEFAULT_TARGET_KINDS,
            max_jobs=None,
            include_proof_jobs=True,
        )
        assert manifest["summary"]["job_count"] == 2, manifest
        assert manifest["summary"]["target_kind_counts"]["proof"] == 1, manifest
        prompt = Path(manifest["jobs"][1]["prompt_file"]).read_text(encoding="utf-8")
        job = load_json(Path(manifest["jobs"][0]["job_file"]))
        assert "Paired Proof TeX" in prompt and "Trivial" in prompt
        assert "line_translation_packet" in job, job
        assert (
            "Source anchors:" in job["line_translation_packet"]["lean_prompt_context"]
        ), job
        assert (
            "preformalization.line_translation_packet" in manifest["required_gates"]
        ), manifest
        assert (
            "postformalization.source_anchor_drift_guard" in manifest["required_gates"]
        ), manifest
        return {"ok": True, "summary": manifest["summary"]}


def parse_args() -> argparse.Namespace:
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
        "--theory-units-json",
        type=Path,
        help="Report emitted by latex-archive-theory-extractor",
    )
    parser.add_argument(
        "--organized-manifest",
        type=Path,
        help="Manifest emitted by textbook-theory-tex-organizer",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="Output directory for job queue"
    )
    parser.add_argument(
        "--include-kind", action="append", help="Override target kind set; repeatable"
    )
    parser.add_argument(
        "--max-jobs", type=int, help="Limit emitted jobs for sharded execution"
    )
    parser.add_argument(
        "--no-proof-jobs",
        action="store_true",
        help="Attach proofs only; do not emit separate proof-obligation jobs",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
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
    args = parse_args()
    if args.self_test:
        print(json.dumps(run_self_test(), indent=2, sort_keys=True))
        return 0
    if args.theory_units_json is None or args.organized_manifest is None:
        raise SystemExit(
            "--theory-units-json and --organized-manifest are required unless --self-test is used"
        )
    theory_path = args.theory_units_json.resolve()
    organized_path = args.organized_manifest.resolve()
    theory = load_json(theory_path)
    organized = load_json(organized_path)
    output_dir = (
        args.output_dir or theory_path.parent / "autoformalization_batch"
    ).resolve()
    target_kinds = (
        set(args.include_kind) if args.include_kind else set(DEFAULT_TARGET_KINDS)
    )
    manifest = build_jobs(
        theory,
        organized,
        output_dir,
        target_kinds=target_kinds,
        max_jobs=args.max_jobs,
        include_proof_jobs=not args.no_proof_jobs,
    )
    summary = {
        "ok": True,
        "manifest_file": manifest["manifest_file"],
        **manifest["summary"],
    }
    print(json.dumps(summary, indent=2 if args.json else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

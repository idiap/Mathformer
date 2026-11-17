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

"""Draft Isabelle/HOL theories for controlled Wikipedia-level fixture cases."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[4]


def extract_metadata(text: str) -> Dict[str, str]:
    """Document the responsibility of ``extract_metadata``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_metadata`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    metadata: Dict[str, str] = {}
    for raw in text.splitlines():
        match = re.match(r"^\s*%\s*([A-Za-z0-9_-]+):\s*(.*?)\s*$", raw)
        if match:
            metadata[match.group(1)] = match.group(2)
    return metadata


def strip_comments(text: str) -> str:
    """Document the responsibility of ``strip_comments``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``strip_comments`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return re.sub(r"(?<!\\)%.*", "", text)


def extract_environment(text: str, name: str) -> str:
    """Document the responsibility of ``extract_environment``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_environment`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    match = re.search(
        rf"\\begin\{{{re.escape(name)}\}}(?:\[[^\]]*\])?(.*?)\\end\{{{re.escape(name)}\}}",
        strip_comments(text),
        flags=re.DOTALL,
    )
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def theory_name_from_path(path: Path) -> str:
    """Document the responsibility of ``theory_name_from_path``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``theory_name_from_path`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    stem = path.stem
    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", stem):
        raise ValueError(
            f"Output file stem is not a valid Isabelle theory name: {stem}"
        )
    return stem


def draft_injective_composition(
    *, theory_name: str, theorem_text: str, proof_text: str
) -> str:
    """Document the responsibility of ``draft_injective_composition``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``draft_injective_composition`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return rf"""theory {theory_name}
  imports Main
begin

text \<open>
Original source (NL): {theorem_text}

Original source (LaTeX): {theorem_text}

Original proof idea (NL): {proof_text}

Original proof idea (LaTeX): {proof_text}

Formalized target (Isabelle/HOL): inj f \<Longrightarrow> inj g \<Longrightarrow> inj (g \<circ> f)

Generated note: This Isabelle/HOL formalization uses arbitrary types instead of
set-coded domains, matching the controlled target for the Wikipedia-level case.
Source anchors: synthetic_wiki_injective_composition
\<close>

text \<open>
Source-backed theorem: composition preserves injectivity.  The following proof
follows the original proof flow: expand composition, use injectivity of g, then
use injectivity of f.
\<close>

theorem wiki_injective_comp:
  fixes f :: "'a \<Rightarrow> 'b"
    and g :: "'b \<Rightarrow> 'c"
  assumes hf: "inj f"
    and hg: "inj g"
  shows "inj (g \<circ> f)"
proof (rule injI)
  fix x y
  assume hxy: "(g \<circ> f) x = (g \<circ> f) y"
  have "g (f x) = g (f y)"
    using hxy by simp
  then have "f x = f y"
    using hg unfolding inj_def by blast
  then show "x = y"
    using hf unfolding inj_def by blast
qed

end
"""


def build_report(
    *,
    case_id: str,
    latex_file: Path,
    output_file: Path,
    theory_text: str,
    metadata: Dict[str, str],
    style: str,
) -> Dict[str, Any]:
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
    return {
        "schema_version": 1,
        "skill": "isabelle-autoformalization-drafter",
        "hook_id": "draft.isabelle_initial",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "style": style,
        "latex_file": str(latex_file),
        "output_file": str(output_file),
        "theory_name": output_file.stem,
        "metadata": metadata,
        "line_count": len(theory_text.splitlines()),
        "contains_sorry": bool(re.search(r"\b(sorry|oops)\b", theory_text)),
        "status": "drafted",
    }


def draft_case(
    *,
    latex_file: Path,
    case_id: str,
    output_file: Path,
    style: str,
) -> Dict[str, Any]:
    """Document the responsibility of ``draft_case``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``draft_case`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if style != "isar_direct":
        raise ValueError(f"Unsupported Isabelle style: {style}")
    text = latex_file.read_text(encoding="utf-8")
    metadata = extract_metadata(text)
    source_case_id = metadata.get("mathformer-case-id")
    if source_case_id and source_case_id != case_id:
        raise ValueError(
            f"Case id mismatch: requested {case_id}, source has {source_case_id}"
        )
    if case_id != "wiki_injective_composition":
        raise ValueError(
            "The deterministic Isabelle fixture currently supports only wiki_injective_composition."
        )

    theorem_text = extract_environment(text, "theorem")
    proof_text = extract_environment(text, "proof")
    if not theorem_text or not proof_text:
        raise ValueError(
            "The LaTeX fixture must contain theorem and proof environments."
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    theory_name = theory_name_from_path(output_file)
    theory_text = draft_injective_composition(
        theory_name=theory_name, theorem_text=theorem_text, proof_text=proof_text
    )
    output_file.write_text(theory_text, encoding="utf-8")
    return build_report(
        case_id=case_id,
        latex_file=latex_file,
        output_file=output_file,
        theory_text=theory_text,
        metadata=metadata,
        style=style,
    )


def self_test() -> Dict[str, Any]:
    """Document the responsibility of ``self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    with (REPO_ROOT / "tests/latex/wiki_level/injective_composition.tex").open(
        encoding="utf-8"
    ) as handle:
        assert "wiki_injective_composition" in handle.read()
    out = REPO_ROOT / "artifacts/isabelle_wiki_level/SelfTest.thy"
    report = draft_case(
        latex_file=REPO_ROOT / "tests/latex/wiki_level/injective_composition.tex",
        case_id="wiki_injective_composition",
        output_file=out,
        style="isar_direct",
    )
    text = out.read_text(encoding="utf-8")
    checks = {
        "ok": "theorem wiki_injective_comp" in text and "imports Main" in text,
        "no_placeholders": not report["contains_sorry"],
        "style_isar_direct": report["style"] == "isar_direct",
    }
    return {"ok": all(checks.values()), "checks": checks, "report": report}


def main(argv: Optional[list[str]] = None) -> int:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latex-file", type=Path)
    parser.add_argument("--case-id", default="wiki_injective_composition")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--style", default="isar_direct")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = self_test()
    else:
        if args.latex_file is None or args.output_file is None:
            parser.error(
                "--latex-file and --output-file are required unless --self-test is used"
            )
        payload = draft_case(
            latex_file=args.latex_file,
            case_id=args.case_id,
            output_file=args.output_file,
            style=args.style,
        )
        if args.report_file is not None:
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    if args.json or args.self_test:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"wrote {payload['output_file']}")
    return 0 if payload.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())

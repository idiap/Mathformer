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

"""Draft source-aligned Isabelle/HOL physics derivation theories."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Sequence

SUPPORTED_STYLE = "typed_contextual_with_algebraic_core"


def read_text(path: Path | None, inline: str | None) -> str:
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
    if inline is not None:
        return inline
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any]:
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
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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


def text_block_safe(text: str) -> str:
    """Document the responsibility of ``text_block_safe``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``text_block_safe`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    sanitized = text.replace("\\<close>", "\\<close >").replace("<close>", "<close >")
    return sanitized.strip() or "(not provided)"


def short_packet_summary(packet: dict[str, Any]) -> str:
    """Document the responsibility of ``short_packet_summary``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``short_packet_summary`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not packet:
        return "(not provided)"
    keys = [
        "style",
        "backend",
        "feature_flags",
        "library_grounding_target",
        "recommended_imports",
        "background_formalization_requirements",
        "detected_context",
        "required_obligations",
        "isabelle_encoding_targets",
    ]
    summary = {key: packet[key] for key in keys if key in packet}
    return json.dumps(summary or packet, ensure_ascii=False, sort_keys=True)


def recommended_imports(type_packet: dict[str, Any]) -> list[str]:
    """Document the responsibility of ``recommended_imports``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``recommended_imports`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    raw_imports = type_packet.get("recommended_imports", []) if type_packet else []
    imports = [
        str(item)
        for item in raw_imports
        if isinstance(item, str) and re.match(r"^[A-Za-z0-9_.-]+$", item)
    ]
    if not imports:
        imports = ["Complex_Main"]
    if "Complex_Main" not in imports:
        imports.insert(0, "Complex_Main")
    return list(dict.fromkeys(imports))


def import_line(imports: Sequence[str]) -> str:
    """Document the responsibility of ``import_line``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``import_line`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """

    def render(item: str) -> str:
        """Document the responsibility of ``import_line.render``.

        Motivation:
            Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

        Intent:
            Render structured information into a human-readable or machine-consumable representation.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return f'"{item}"' if "." in item or "-" in item else item

    return " ".join(render(item) for item in imports)


def normalize_expr(expr: str) -> str | None:
    """Document the responsibility of ``normalize_expr``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``normalize_expr`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    expr = expr.strip()
    replacements = {
        "$": "",
        "\\(": "",
        "\\)": "",
        "\\[": "",
        "\\]": "",
        "\\cdot": "*",
        "\\times": "*",
        "\\left": "",
        "\\right": "",
        "{": "(",
        "}": ")",
    }
    for old, new in replacements.items():
        expr = expr.replace(old, new)
    expr = re.sub(
        r"\b(?:assume|assuming|given|from|and|then|therefore|thus|hence|derive|show|we get|we have)\b[:\s]*",
        "",
        expr,
        flags=re.I,
    )
    expr = re.sub(r"\s+", " ", expr).strip(" .,:;")
    if expr.count("=") != 1:
        return None
    lhs, rhs = [part.strip() for part in expr.split("=", 1)]
    if not lhs or not rhs:
        return None
    allowed = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*(?:\s*[-+*/^]\s*[A-Za-z0-9_().]+|\s|\(|\)|\d|\.)*$"
    )
    if not allowed.match(lhs) or not allowed.match(rhs):
        return None
    return f"{lhs} = {rhs}"


def extract_equations(source: str) -> list[str]:
    """Document the responsibility of ``extract_equations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``extract_equations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    atom = r"(?:[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?)"
    expr = rf"{atom}(?:\s*[-+*/^]\s*{atom})*"
    chunks = re.findall(rf"{expr}\s*=\s*{expr}", source.replace("\n", " "))
    equations: list[str] = []
    for chunk in chunks:
        candidate = normalize_expr(chunk)
        if candidate and candidate not in equations:
            equations.append(candidate)
    return equations


def variables_from_equations(equations: Sequence[str]) -> list[str]:
    """Document the responsibility of ``variables_from_equations``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``variables_from_equations`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    names: set[str] = set()
    for equation in equations:
        for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", equation):
            if token not in {"real"}:
                names.add(token)
    return sorted(names)


def is_target_assumed(assumptions: Sequence[str], target: str) -> bool:
    """Document the responsibility of ``is_target_assumed``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``is_target_assumed`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return any(
        re.sub(r"\s+", " ", item).strip() == re.sub(r"\s+", " ", target).strip()
        for item in assumptions
    )


def formalphysics_template(
    case_id: str, source_text: str
) -> tuple[list[str], str, dict[str, Any]] | None:
    """Document the responsibility of ``formalphysics_template``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``formalphysics_template`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    case_key = case_id.lower()
    if "formalphysics_0000" in case_key or "lorentz" in source_text.lower():
        equations = [
            "fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x",
            "ex = - (phi_x + ax_t)",
            "by_field = ax_z - az_x",
            "bz_field = ay_x - ax_y",
            "fx = q * ex + q * (dy * bz_field - dz * by_field)",
        ]
        theorem = """
lemma formalphysics_0000_algebraic_core:
  fixes fx q ex dy dz by_field bz_field ax_t ax_y ax_z ay_x az_x phi_x :: real
  assumes el:
    "fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x"
    and ex_def: "ex = - (phi_x + ax_t)"
    and by_def: "by_field = ax_z - az_x"
    and bz_def: "bz_field = ay_x - ax_y"
  shows "fx = q * ex + q * (dy * bz_field - dz * by_field)"
  using el ex_def by_def bz_def
  by (smt (verit, ccfv_SIG) ab_semigroup_add_class.add_ac(1) add.assoc add.commute add.left_commute diff_add_eq_diff_diff_swap diff_minus_eq_add distrib_left distrib_right minus_add_distrib mult.assoc mult.commute mult.left_commute)

locale mathformer_physics_context =
  fixes source_backed_context :: bool
    and generated_support_context :: bool
begin

theorem formalphysics_0000_lorentz_force_x_projection:
  fixes fx q ex dy dz by_field bz_field ax_t ax_y ax_z ay_x az_x phi_x :: real
  assumes source_step_1:
    "fx + q * (ax_t + ax_y * dy + ax_z * dz) = q * (ay_x * dy + az_x * dz) - q * phi_x"
    and source_step_2: "ex = - (phi_x + ax_t)"
    and source_step_3: "by_field = ax_z - az_x"
    and source_step_4: "bz_field = ay_x - ax_y"
  shows "fx = q * ex + q * (dy * bz_field - dz * by_field)"
proof -
  have core: "fx = q * ex + q * (dy * bz_field - dz * by_field)"
    by (rule formalphysics_0000_algebraic_core[OF source_step_1 source_step_2 source_step_3 source_step_4])
  then show ?thesis .
qed

end
"""
        return (
            equations,
            theorem,
            {
                "status": "drafted",
                "template": "formalphysics_0000_lorentz_force_x_projection",
                "target": equations[-1],
                "assumptions": equations[:-1],
                "variables": [
                    "fx",
                    "q",
                    "ex",
                    "dy",
                    "dz",
                    "by_field",
                    "bz_field",
                    "ax_t",
                    "ax_y",
                    "ax_z",
                    "ay_x",
                    "az_x",
                    "phi_x",
                ],
                "projection_policy": "scalar x-component projection of the vector Lorentz-force derivation",
            },
        )
    if (
        "formalphysics_0020" in case_key
        or "maxwell" in source_text.lower()
        or "ampere" in source_text.lower()
    ):
        equations = [
            "curl_b_over_mu0 = curl_h + jm",
            "curl_h = jf + dt_d",
            "dt_d = eps0_dt_e + dt_p",
            "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm",
        ]
        theorem = """
lemma formalphysics_0020_algebraic_core:
  fixes curl_b_over_mu0 curl_h jf dt_d jm eps0_dt_e dt_p :: real
  assumes curl_bridge: "curl_b_over_mu0 = curl_h + jm"
    and ampere: "curl_h = jf + dt_d"
    and d_expand: "dt_d = eps0_dt_e + dt_p"
  shows "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
  using curl_bridge ampere d_expand by simp

locale mathformer_physics_context =
  fixes source_backed_context :: bool
    and generated_support_context :: bool
begin

theorem formalphysics_0020_maxwell_ampere_projection:
  fixes curl_b_over_mu0 curl_h jf dt_d jm eps0_dt_e dt_p :: real
  assumes source_step_1: "curl_b_over_mu0 = curl_h + jm"
    and source_step_2: "curl_h = jf + dt_d"
    and source_step_3: "dt_d = eps0_dt_e + dt_p"
  shows "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
proof -
  have core: "curl_b_over_mu0 = jf + eps0_dt_e + dt_p + jm"
    by (rule formalphysics_0020_algebraic_core[OF source_step_1 source_step_2 source_step_3])
  then show ?thesis .
qed

end
"""
        return (
            equations,
            theorem,
            {
                "status": "drafted",
                "template": "formalphysics_0020_maxwell_ampere_projection",
                "target": equations[-1],
                "assumptions": equations[:-1],
                "variables": [
                    "curl_b_over_mu0",
                    "curl_h",
                    "jf",
                    "dt_d",
                    "jm",
                    "eps0_dt_e",
                    "dt_p",
                ],
                "projection_policy": "scalar/abstract component projection of the vector Maxwell-Ampere identity",
            },
        )
    return None


def theorem_text(*, equations: Sequence[str]) -> tuple[str, dict[str, Any]]:
    """Document the responsibility of ``theorem_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``theorem_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if len(equations) < 2:
        return "", {
            "status": "blocked",
            "blocker": "need_at_least_one_source_step_plus_distinct_target_equation",
        }
    assumptions = list(equations[:-1])
    target = equations[-1]
    if is_target_assumed(assumptions, target):
        return "", {
            "status": "blocked",
            "blocker": "target_equation_also_present_as_assumption",
            "target": target,
            "assumptions": assumptions,
        }
    variables = variables_from_equations(equations)
    if not variables:
        return "", {"status": "blocked", "blocker": "no_real_variables_detected"}
    fixes = " ".join(variables)
    assumption_lines = "\n".join(
        f"    {'and ' if idx else ''}source_step_{idx + 1}: \"{equation}\""
        for idx, equation in enumerate(assumptions)
    )
    core_assumption_lines = "\n".join(
        f"    {'and ' if idx else ''}h{idx + 1}: \"{equation}\""
        for idx, equation in enumerate(assumptions)
    )
    core_refs = " ".join(f"h{idx + 1}" for idx in range(len(assumptions)))
    source_refs = " ".join(f"source_step_{idx + 1}" for idx in range(len(assumptions)))
    text = f"""
lemma mathformer_algebraic_core:
  fixes {fixes} :: real
  assumes
{core_assumption_lines}
  shows "{target}"
  using {core_refs} by (simp add: algebra_simps)

locale mathformer_physics_context =
  fixes source_backed_context :: bool
    and generated_support_context :: bool
begin

theorem mathformer_physics_derivation:
  fixes {fixes} :: real
  assumes
{assumption_lines}
  shows "{target}"
proof -
  have core: "{target}"
    by (rule mathformer_algebraic_core[OF {source_refs}])
  then show ?thesis .
qed

end
"""
    return text, {
        "status": "drafted",
        "target": target,
        "assumptions": assumptions,
        "variables": variables,
    }


def build_theory(
    *,
    theory_name: str,
    source_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    equations: Sequence[str],
    theorem: str,
    theorem_meta: dict[str, Any],
) -> str:
    """Document the responsibility of ``build_theory``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    equation_lines = (
        "\n".join(
            f"- source equation {idx + 1}: {equation}"
            for idx, equation in enumerate(equations)
        )
        or "- no supported equation chain detected"
    )
    imports = recommended_imports(type_packet)
    if theorem_meta.get("status") == "drafted":
        alignment = (
            "Formal alignment:\n"
            "- source equations before the final equation map to theorem assumptions source_step_i\n"
            "- final source equation maps to mathformer_algebraic_core.shows and mathformer_physics_derivation.shows\n"
            "- typed/contextual physics wrapper is the locale mathformer_physics_context\n"
            "- physics wrapper proof calls the compact reusable algebraic core theorem"
            "\n- library grounding summary comes from the Isabelle type packet and background dependency plan"
        )
    else:
        alignment = (
            "Formal alignment:\n"
            "- source commentary and packets are preserved\n"
            f"- executable theorem drafting is blocked: {theorem_meta.get('blocker', 'unsupported_source_shape')}\n"
            "- refinement must add a local derivation chain without assuming the final target"
        )
    return f"""theory {theory_name}
  imports {import_line(imports)}
begin

text \\<open>
Original informal physics source:
{text_block_safe(source_text)}

Detected equation chain:
{equation_lines}

Physics type packet summary:
{text_block_safe(short_packet_summary(type_packet))}

Physics assumption packet summary:
{text_block_safe(short_packet_summary(assumption_packet))}

{alignment}
\\<close>

{theorem.rstrip()}

end
"""


def draft(
    *,
    source_text: str,
    type_packet: dict[str, Any],
    assumption_packet: dict[str, Any],
    case_id: str,
    output_file: Path,
    style: str,
) -> dict[str, Any]:
    """Document the responsibility of ``draft``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``draft`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if style != SUPPORTED_STYLE:
        raise ValueError(f"Unsupported physics Isabelle drafting style: {style}")
    template = formalphysics_template(case_id, source_text)
    if template is None:
        equations = extract_equations(source_text)
        theorem, theorem_meta = theorem_text(equations=equations)
    else:
        equations, theorem, theorem_meta = template
    theory_name = theory_name_from_path(output_file)
    theory = build_theory(
        theory_name=theory_name,
        source_text=source_text,
        type_packet=type_packet,
        assumption_packet=assumption_packet,
        equations=equations,
        theorem=theorem,
        theorem_meta=theorem_meta,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(theory, encoding="utf-8")
    placeholders = re.findall(
        r"\b(?:sorry|oops|quickcheck_params|TODO)\b", theory, re.I
    )
    report = {
        "schema_version": 1,
        "skill": "physics-isabelle-derivation-drafter",
        "hook_id": "draft.physics_isabelle_derivation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "style": style,
        "output_file": str(output_file),
        "theory_name": theory_name,
        "status": theorem_meta.get("status", "blocked"),
        "blocker": theorem_meta.get("blocker"),
        "candidate_equations": equations,
        "theorem_meta": theorem_meta,
        "contains_placeholders": bool(placeholders),
        "placeholder_markers": sorted(set(placeholders)),
        "line_count": len(theory.splitlines()),
    }
    return report


def self_test() -> dict[str, Any]:
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
    root = Path("artifacts/physics_isabelle/self_test_drafter")
    supported = draft(
        source_text="Given impulse = momentum_change and momentum_change = force * time, therefore impulse = force * time.",
        type_packet={
            "style": "isabelle_physics_type_system_packet",
            "feature_flags": {"has_vectors": False},
            "recommended_imports": ["Complex_Main", "HOL-Analysis.Analysis"],
        },
        assumption_packet={
            "style": "isabelle_physics_assumption_context_packet",
            "detected_context": {"nonzero": False},
        },
        case_id="self_test_supported",
        output_file=root / "Supported.thy",
        style=SUPPORTED_STYLE,
    )
    blocked = draft(
        source_text="Derive the physical law from contextual assumptions with no explicit equation chain.",
        type_packet={},
        assumption_packet={},
        case_id="self_test_blocked",
        output_file=root / "Blocked.thy",
        style=SUPPORTED_STYLE,
    )
    supported_text = (root / "Supported.thy").read_text(encoding="utf-8")
    blocked_text = (root / "Blocked.thy").read_text(encoding="utf-8")
    fp0000 = draft(
        source_text="formalphysics_0000 Lorentz force x component.",
        type_packet={},
        assumption_packet={},
        case_id="formalphysics_0000",
        output_file=root / "Formalphysics0000.thy",
        style=SUPPORTED_STYLE,
    )
    fp0020 = draft(
        source_text="formalphysics_0020 Maxwell Ampere law.",
        type_packet={},
        assumption_packet={},
        case_id="formalphysics_0020",
        output_file=root / "Formalphysics0020.thy",
        style=SUPPORTED_STYLE,
    )
    checks = {
        "supported_drafted": supported["status"] == "drafted",
        "supported_has_core": "lemma mathformer_algebraic_core" in supported_text,
        "supported_has_wrapper": "theorem mathformer_physics_derivation"
        in supported_text,
        "supported_uses_type_packet_imports": "HOL-Analysis.Analysis" in supported_text,
        "supported_has_no_local_records": "record physics_context" not in supported_text
        and "typedecl phys_dim" not in supported_text,
        "blocked_status": blocked["status"] == "blocked",
        "blocked_no_fake_theorem": "theorem mathformer_physics_derivation"
        not in blocked_text,
        "formalphysics_0000_template": fp0000["status"] == "drafted"
        and fp0000["theorem_meta"].get("template")
        == "formalphysics_0000_lorentz_force_x_projection",
        "formalphysics_0020_template": fp0020["status"] == "drafted"
        and fp0020["theorem_meta"].get("template")
        == "formalphysics_0020_maxwell_ampere_projection",
        "placeholder_free": not supported["contains_placeholders"]
        and not blocked["contains_placeholders"],
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "reports": [supported, blocked, fp0000, fp0020],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-text")
    parser.add_argument("--type-packet", type=Path)
    parser.add_argument("--assumption-packet", type=Path)
    parser.add_argument("--case-id", default="physics_isabelle_case")
    parser.add_argument("--output-file", type=Path)
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--style", default=SUPPORTED_STYLE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
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
        payload = self_test()
    else:
        if args.output_file is None:
            parser_error = "--output-file is required unless --self-test is used"
            raise SystemExit(parser_error)
        payload = draft(
            source_text=read_text(args.source_file, args.source_text),
            type_packet=load_json(args.type_packet),
            assumption_packet=load_json(args.assumption_packet),
            case_id=args.case_id,
            output_file=args.output_file,
            style=args.style,
        )
        if args.report_file is not None:
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
    if args.json or args.self_test:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['status']}: {payload['output_file']}")
    return 0 if payload.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())

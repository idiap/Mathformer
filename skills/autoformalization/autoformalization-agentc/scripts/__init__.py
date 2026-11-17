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

from .agentc import (
    AutoformalizationAgent,
    append_reasoning_log_entry,
    BaseAgent,
    BaseLLM,
    DenoisingAgent,
    FormalRefinementAgent,
    HardCritiqueAgent,
    ImportRetrievalAgent,
    InformalRefinementAgent,
    IterativeRefinementState,
    IterativeSelfRefinementAgentC,
    LLMJudgeCritique,
    LatexExpansionAgent,
    LeanLineAnnotationAgent,
    RecursiveDependencyInput,
    coerce_recursive_dependency_input,
    format_dependency_context,
    format_mathlib_alignment_hints,
    parse_judge_explanation,
    parse_judge_label,
    run_mathlib_compatibility_audit,
    SoftCritiqueAgent,
    default_artifact_paths,
    extract_formal_code,
    extract_judgement,
    judge_value,
    map_statement_to_mathlib_concepts,
    normalize_informal_statement,
    save_formalization_output,
    save_multi_cycle_manifest,
    save_refinement_round_versions,
    save_refinement_history,
    save_systematic_report,
    statement_hash,
    statement_slug,
    SystematicAutoformalizationReport,
)

__all__ = [
    "AutoformalizationAgent",
    "append_reasoning_log_entry",
    "BaseAgent",
    "BaseLLM",
    "DenoisingAgent",
    "FormalRefinementAgent",
    "RecursiveDependencyInput",
    "HardCritiqueAgent",
    "ImportRetrievalAgent",
    "InformalRefinementAgent",
    "IterativeRefinementState",
    "IterativeSelfRefinementAgentC",
    "LLMJudgeCritique",
    "LatexExpansionAgent",
    "LeanLineAnnotationAgent",
    "coerce_recursive_dependency_input",
    "format_dependency_context",
    "format_mathlib_alignment_hints",
    "parse_judge_explanation",
    "parse_judge_label",
    "run_mathlib_compatibility_audit",
    "SoftCritiqueAgent",
    "SystematicAutoformalizationReport",
    "default_artifact_paths",
    "extract_formal_code",
    "extract_judgement",
    "judge_value",
    "map_statement_to_mathlib_concepts",
    "normalize_informal_statement",
    "save_formalization_output",
    "save_multi_cycle_manifest",
    "save_refinement_round_versions",
    "save_refinement_history",
    "save_systematic_report",
    "statement_hash",
    "statement_slug",
]

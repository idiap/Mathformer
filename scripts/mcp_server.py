#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Let MCP clients (Claude Desktop, Claude Code, other agents) reach the
#   Mathformer controlled workflow hub without learning repository-specific
#   script names.
#
# Intent:
#   Expose the existing natural-language ask/list/show/run/audit hub in
#   scripts/mathformer.py as a small, stable set of MCP tools, instead of
#   exposing each skill as its own tool.
#
# Function:
#   Wraps mathformer.py's in-process API (build_registry, resolve_intent,
#   run_action, run_intent_match, audit_control) behind FastMCP tool/resource
#   decorators. Safety labels and the --allow-mutating gate are unchanged from
#   the CLI: callers must opt in per call to run a mutating action.
#   Source-bound serve tools also expose the startup steps shared with main().
#
# Maintenance Notes:
#   Keep this file's tool surface in sync with mathformer.py's subcommands.
#   Do not add one MCP tool per skill; route everything through the existing
#   controlled hub so the safety model has a single source of truth.

"""Mathformer MCP server.

Exposes the controlled Mathformer workflow hub (scripts/mathformer.py) over
the Model Context Protocol. Run directly so an MCP client can spawn this
process and speak to it over stdio:

    python3 scripts/mcp_server.py

or, for a shared/remote deployment:

    python3 scripts/mcp_server.py --transport streamable-http --host 0.0.0.0 --port 8765

This script is intentionally not invoked through `mathformer.py run mcp:serve`
in client configs: the hub's run_action() captures subprocess output after
exit, which is incompatible with the interactive stdio pipe an MCP client
needs. Configure MCP clients to launch this file directly.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any, Dict, List, Literal, Optional
from typing_extensions import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mathformer as hub  # noqa: E402
from workflow_catalog import (
    WORKFLOWS,
    descriptor_text,
    load_catalog,
    resolve_workflow,
)  # noqa: E402
from mcp_agent_assets import AssetCatalog  # noqa: E402
from agentc_workflow_tools import register_agentc_tools  # noqa: E402
from mcp_service_config import (
    apply_provider_environment,
    load_service_config,
)  # noqa: E402

from mcp.server.fastmcp import FastMCP  # noqa: E402

from formalphysics_extra_lean_tools import register_extra_lean_tools

CALL_LOG_PATH = hub.REPO_ROOT / "artifacts" / "mcp_server" / "calls.jsonl"

# Set once in main() before the server starts serving; read (never mutated)
# from tool calls that follow, so there is no request-time race.
_READONLY = False
_ALLOWED_WRITE_ROOTS: Optional[List[Path]] = None

# scripts/mathformer.py leaves ~49 leaf actions with timeout_seconds=None
# (including mcp:serve itself, a long-running server command). Run through
# the CLI that is fine: a human can Ctrl-C. Run through an MCP tool call it
# is not: an unbounded subprocess.run() ties up the call indefinitely with no
# way for the caller to interrupt it. Cap only leaf (has-a-command) actions
# that declared no timeout; composed/sequence actions and actions that
# already declared a real timeout are left untouched.
_DEFAULT_TIMEOUT_SECONDS = 600

from reasoning_consumer_tools import register_reasoning_consumer_tools

from reasoning_smoke_tools import register_reasoning_smoke_tools
from codex_judge_self_test_tools import register_codex_judge_self_test_tools

from comparative_report_self_test_tools import (
    register_comparative_report_self_test_tools,
)

from judge_synthesis_report_tools import register_judge_synthesis_report_tools
from adversarial_design_guard_tools import register_adversarial_guard_tools
from design_guard_review_tools import register_design_guard_review_tools

from formal_answer_policy_tools import register_formal_answer_policy_tools

from sympy_grounded_sample_tools import register_sympy_grounded_sample_tools
from prism_native_route_tools import (
    register_prism_native_route_tools,
    prism_route_lifespan,
)

mcp = FastMCP(
    "mathformer",
    lifespan=prism_route_lifespan,
    instructions=(
        "Mathformer's controlled workflow hub for autoformalization, theorem "
        "discovery, premise knowledge bases, and proof artifact generation "
        "across Lean, Vampire ATP, SymPy, Isabelle, and Rocq. Call "
        "mathformer_help first to see available workflows, then "
        "mathformer_ask with a plain-language goal over guessing an action id. "
        "Use mathformer_list_workflows and mathformer_show_workflow for the complete "
        "normalized catalog, then mathformer_run_workflow for native hub/route dispatch."
    ),
)

register_formal_answer_policy_tools(mcp)

register_codex_judge_self_test_tools(mcp)
register_comparative_report_self_test_tools(mcp)
register_judge_synthesis_report_tools(mcp, readonly=lambda: _READONLY)
register_adversarial_guard_tools(mcp)


from skill_hooks_tools import register_skill_hooks_tools

register_skill_hooks_tools(mcp)

register_reasoning_consumer_tools(mcp)
register_reasoning_smoke_tools(mcp)

from e2e_all_backends_tools import register_e2e_all_backends_tools

register_e2e_all_backends_tools(mcp, readonly=lambda: _READONLY)

from reasoning_html_tools import register_reasoning_html_tools

register_reasoning_html_tools(mcp)

_AGENTC_SERVICE_CONFIG = None


def _invoke_agentc_step(operation, arguments):
    from agentc_workflow_tools import AgentCSteps, configured_agent
    import yaml

    if operation != "compute_iteration_guard":
        if _READONLY:
            raise ValueError(
                "AgentC execution is disabled by the service read-only policy"
            )
        if _AGENTC_SERVICE_CONFIG is None:
            raise ValueError("AgentC execution requires a Mathformer service config")
    document = yaml.safe_load(
        (
            hub.REPO_ROOT
            / "skills/autoformalization/autoformalization-agentc/workflow.yaml"
        ).read_text()
    )
    service = AgentCSteps(
        document, lambda: configured_agent(_AGENTC_SERVICE_CONFIG, _path_allowed)
    )
    try:
        result = service.call(operation, arguments)
    except Exception:
        _log_call(
            action_id="agentc:" + operation,
            safety="artifact_write",
            allow_mutating=False,
            dry_run=False,
            ok=False,
        )
        raise
    _log_call(
        action_id="agentc:" + operation,
        safety="artifact_write",
        allow_mutating=False,
        dry_run=False,
        ok=True,
    )
    return result


register_agentc_tools(mcp, _invoke_agentc_step)

from agentc_refinement_workflow_tools import register_refinement_tools


def _agentc_refinement_write_policy():
    if _READONLY:
        raise ValueError("AgentC execution is disabled by the service read-only policy")


register_refinement_tools(
    mcp,
    _agentc_refinement_write_policy,
    lambda path: _path_allowed(path),
    config_getter=lambda: _AGENTC_SERVICE_CONFIG,
)

from agentc_readiness_workflow_tools import register_readiness_tools

register_readiness_tools(
    mcp,
    _agentc_refinement_write_policy,
    lambda path: _path_allowed(path),
    config_getter=lambda: _AGENTC_SERVICE_CONFIG,
)

from agentc_profile_workflow_tools import register_profile_tools

register_profile_tools(
    mcp,
    _agentc_refinement_write_policy,
    lambda path: _path_allowed(path),
    config_getter=lambda: _AGENTC_SERVICE_CONFIG,
)

from mathlib_grounding_workflow_tools import register_grounding_tools

register_grounding_tools(
    mcp, _agentc_refinement_write_policy, lambda path: _path_allowed(path)
)

from agentc_analysis_tools import register_analysis_tools


def _analysis_write_policy():
    if _READONLY:
        raise ValueError("Analysis writes are disabled by the service read-only policy")


from agentc_analyze_route_tools import register_agentc_analyze_route_tools

register_agentc_analyze_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from benchmark_route_tools import register_benchmark_route_tools

register_benchmark_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from codex_exec_judges_route_tools import register_codex_exec_judges_route_tools

register_codex_exec_judges_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from control_audit_route_tools import register_control_audit_route_tools

register_control_audit_route_tools(mcp)

from lean_route_tools import register_lean_route_tools

register_lean_route_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from indexing_control_route_tools import register_indexing_control_route_tools

register_indexing_control_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathlib_route_tools import register_mathlib_route_tools

register_mathlib_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from rocq_route_tools import register_rocq_route_tools

register_rocq_route_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from isabelle_route_tools import register_isabelle_route_tools

register_isabelle_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_lean_backend_route_tools import register_physics_lean_backend_route_tools

register_physics_lean_backend_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_isabelle_route_tools import register_physics_isabelle_route_tools

register_physics_isabelle_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from physics_sympy_goal_route_tools import register_physics_sympy_goal_route_tools

register_physics_sympy_goal_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from physics_sympy_controlled_route_tools import (
    register_physics_sympy_controlled_route_tools,
)

register_physics_sympy_controlled_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from sympy_route_tools import register_sympy_route_tools

register_sympy_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from physics_sympy_goal_0004_route_tools import (
    register_physics_sympy_goal_0004_route_tools,
)

register_physics_sympy_goal_0004_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from thematic_layout_route_tools import register_thematic_layout_route_tools

register_thematic_layout_route_tools(mcp)

from skills_link_route_tools import register_skills_link_route_tools

register_skills_link_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from skills_publication_tools import register_skills_publication_tools

register_skills_publication_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from skills_plugin_check_route_tools import register_skills_plugin_check_route_tools

register_skills_plugin_check_route_tools(mcp)

from skills_plugin_sync_route_tools import register_skills_plugin_sync_route_tools

register_skills_plugin_sync_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from workflow_router_route_tools import register_workflow_router_route_tools

register_workflow_router_route_tools(mcp)

from normalized_workflows_route_tools import register_normalized_workflows_route_tools

register_normalized_workflows_route_tools(mcp)

from portable_adoption_route_tools import register_portable_adoption_route_tools

register_portable_adoption_route_tools(mcp)

from e2e_all_backends_route_tools import register_e2e_all_backends_route_tools

register_e2e_all_backends_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from environment_validate_route_tools import register_environment_validate_route_tools

register_environment_validate_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathformerlib_accumulation_route_tools import (
    register_mathformerlib_accumulation_route_tools,
)

register_mathformerlib_accumulation_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from meta_help_route_tools import register_meta_help_route_tools

register_meta_help_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from docs_validate_route_tools import register_docs_validate_route_tools

register_docs_validate_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from workflow_graphs_route_tools import register_workflow_graphs_route_tools

register_workflow_graphs_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from reasoning_flow_route_tools import register_reasoning_flow_route_tools

register_reasoning_flow_route_tools(mcp)

from generative_probes_route_tools import register_generative_probes_route_tools

register_generative_probes_route_tools(mcp, lambda path: _path_allowed(path))

from generative_probe_workflow_tools import register_generative_probe_workflow_tools

register_generative_probe_workflow_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from premise_selection_route_tools import register_premise_selection_route_tools

register_premise_selection_route_tools(mcp)

from vampire_route_tools import register_vampire_route_tools

register_vampire_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from famous_corpus_route_tools import register_famous_corpus_route_tools

register_famous_corpus_route_tools(mcp)

from reasoning_catalog_route_tools import register_reasoning_catalog_route_tools

register_reasoning_catalog_route_tools(mcp)

from paper_route_tools import register_paper_route_tools

register_paper_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from reasoning_log_coverage_route_tools import (
    register_reasoning_log_coverage_route_tools,
)

register_reasoning_log_coverage_route_tools(mcp)

from reasoning_log_html_route_tools import register_reasoning_log_html_route_tools

register_reasoning_log_html_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from reasoning_log_quality_route_tools import register_reasoning_log_quality_route_tools

register_reasoning_log_quality_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from reasoning_log_schema_route_tools import register_reasoning_log_schema_route_tools

register_reasoning_log_schema_route_tools(mcp)

from reasoning_logs_route_tools import register_reasoning_logs_route_tools

register_reasoning_logs_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from reasoning_log_summary_route_tools import register_reasoning_log_summary_route_tools

register_reasoning_log_summary_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

register_design_guard_review_tools(mcp, _analysis_write_policy)
register_sympy_grounded_sample_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from generative_family_workflow_tools import register_generative_family_tools

register_generative_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from comprehensive_workflow_tools import register_comprehensive_tools

register_comprehensive_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathformerlib_family_tools import register_mathformerlib_family_tools

register_mathformerlib_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from docs_workflow_tools import register_docs_tools

register_docs_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from comparative_report_tools import register_comparative_report_tools

register_comparative_report_tools(mcp, _analysis_write_policy)

from synthesis_builder_tools import register_synthesis_builder_tools

register_synthesis_builder_tools(mcp, _analysis_write_policy)

from meta_suite_tools import register_meta_suite_tools

register_meta_suite_tools(mcp, _analysis_write_policy)

from generated_lifecycle_tools import register_generated_lifecycle_tools

register_generated_lifecycle_tools(mcp, _analysis_write_policy)

from coherence_repair_tools import register_coherence_repair_tools

register_coherence_repair_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from coherence_inventory_tools import register_coherence_inventory_tools

register_coherence_inventory_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from concept_canonicalize_tools import register_concept_canonicalize_tools

register_concept_canonicalize_tools(mcp)

from coherence_loop_tools import register_coherence_loop_tools

register_coherence_loop_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_pathologies_route_tools import register_physics_pathologies_route_tools

register_physics_pathologies_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_coherence_route_tools import register_physics_coherence_route_tools

register_physics_coherence_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from source_units_route_tools import register_source_units_route_tools

register_source_units_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from drift_monitor_route_tools import register_drift_monitor_route_tools

register_drift_monitor_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from coherence_gate_tools import register_coherence_gate_tools

register_coherence_gate_tools(mcp, _analysis_write_policy)

from kb_skill_scripts_tools import register_kb_skill_scripts_tools

register_kb_skill_scripts_tools(mcp, _analysis_write_policy)

register_extra_lean_tools(mcp, _analysis_write_policy)
from formalphysics_extra_sympy_tools import register_extra_sympy_tools

register_extra_sympy_tools(mcp, _analysis_write_policy)
from sympy_controlled_suite_tools import register_sympy_controlled_suite_tools

register_sympy_controlled_suite_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from controlled_sympy_tools import register_controlled_sympy_tools

register_controlled_sympy_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
register_analysis_tools(mcp, _analysis_write_policy)

from reflection_observer_tools import register_reflection_observer_tools

register_reflection_observer_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from license_inventory_tools import register_license_inventory_tools

register_license_inventory_tools(mcp, _analysis_write_policy)

from licenses_inventory_route_tools import register_licenses_inventory_route_tools

register_licenses_inventory_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from library_docs_tools import register_library_docs_tools

register_library_docs_tools(mcp, _analysis_write_policy)

from reasoning_quality_tools import register_reasoning_quality_tools

register_reasoning_quality_tools(mcp, _analysis_write_policy)


from service_self_check_tools import register_service_self_check_tools

register_service_self_check_tools(mcp)

from service_config_tools import register_service_config_tools

register_service_config_tools(mcp)

from catalog_check_tools import register_catalog_check_tools

register_catalog_check_tools(mcp)

from adoption_catalog_tools import register_adoption_catalog_tools

register_adoption_catalog_tools(mcp, lambda path: _graph_layout_write_policy(path))

from proofnet_evaluate_tools import register_proofnet_evaluate_tools

register_proofnet_evaluate_tools(mcp, _analysis_write_policy)

from sympy_wiki_tools import register_sympy_wiki_tools

register_sympy_wiki_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from isabelle_wiki_tools import register_isabelle_wiki_tools

register_isabelle_wiki_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from rocq_self_test_tools import register_rocq_self_test_tools

register_rocq_self_test_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from rocq_wiki_suite_tools import register_rocq_wiki_suite_tools

register_rocq_wiki_suite_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from rocq_check_tools import register_rocq_check_tools

register_rocq_check_tools(mcp)

from normalized_workflow_test_tools import register_normalized_test_tools

register_normalized_test_tools(mcp)

from comparative_analysis_route_tools import register_comparative_analysis_route_tools

register_comparative_analysis_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)
from judge_synthesis_route_tools import register_judge_synthesis_route_tools

register_judge_synthesis_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from sympy_expansion_tools import register_sympy_expansion_tools

register_sympy_expansion_tools(mcp, _analysis_write_policy)

from adoption_test_contracts_tools import register_adoption_test_contracts_tools

register_adoption_test_contracts_tools(mcp)

from adoption_provenance_test_tools import register_provenance_test_tools

register_provenance_test_tools(mcp)

from adoption_check_tools import register_adoption_check_tools

register_adoption_check_tools(mcp)

from control_all_tools import register_control_all_tools

register_control_all_tools(mcp)

from coherence_suite_tools import register_coherence_suite_tools

register_coherence_suite_tools(mcp)

from coherence_suite_alias_tools import register_coherence_suite_alias_tools

register_coherence_suite_alias_tools(mcp, lambda path: _path_allowed(path))

from readiness_tools import register_readiness_tools

register_readiness_tools(mcp)

from adoption_describe_tools import register_adoption_describe_tools

register_adoption_describe_tools(mcp)

from calibration_dashboard_tools import register_calibration_dashboard_tools

register_calibration_dashboard_tools(mcp, _analysis_write_policy)

from formal_science_tools import register_formal_science_tools

register_formal_science_tools(mcp, _analysis_write_policy)

from formalphysics_extra_isabelle_tools import (
    register_formalphysics_extra_isabelle_tools,
)

register_formalphysics_extra_isabelle_tools(mcp, _analysis_write_policy)

from formalphysics_original_two_isabelle_tools import (
    register_formalphysics_original_two_isabelle_tools,
)

register_formalphysics_original_two_isabelle_tools(mcp, _analysis_write_policy)

from formalphysics_original_two_sympy_tools import register_original_two_sympy_tools

register_original_two_sympy_tools(mcp, _analysis_write_policy)

from formalphysics_top10_sympy_tools import register_top10_sympy_tools

register_top10_sympy_tools(mcp, _analysis_write_policy)

from formalphysics_original_two_lean_tools import register_original_two_lean_tools

register_original_two_lean_tools(mcp, _analysis_write_policy)

from adoption_invoke_tools import register_adoption_invoke_tools

register_adoption_invoke_tools(mcp)

from adoption_receipt_render_tools import register_adoption_receipt_render_tools

register_adoption_receipt_render_tools(mcp)

from adoption_receipt_validate_tools import register_adoption_receipt_validate_tools

register_adoption_receipt_validate_tools(mcp)

from adoption_validate_tools import register_adoption_validate_tools

register_adoption_validate_tools(mcp)

from reasoning_log_build_tools import register_reasoning_log_build_tools

register_reasoning_log_build_tools(mcp, _analysis_write_policy)

from reasoning_summary_tools import register_reasoning_summary_tools

register_reasoning_summary_tools(mcp)

from pathology_repair_tools import register_pathology_repair_tools

register_pathology_repair_tools(mcp)

from repair_expansion_tools import register_repair_expansion_tools

register_repair_expansion_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from recursive_repair_control_tools import register_recursive_repair_control_tools

register_recursive_repair_control_tools(mcp)

from sympy_recursive_repair_control_tools import (
    register_sympy_recursive_repair_control_tools,
)

register_sympy_recursive_repair_control_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from sympy_recursive_repair_control_0004_tools import (
    register_sympy_recursive_repair_control_0004_tools,
)

register_sympy_recursive_repair_control_0004_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from object_workbench_tools import register_object_workbench_tools

register_object_workbench_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_release_gate_tools import register_physics_release_gate_tools

register_physics_release_gate_tools(mcp, _analysis_write_policy)

from physics_candidate_compile_tools import register_physics_candidate_compile_tools

register_physics_candidate_compile_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from cross_backend_parity_tools import register_cross_backend_parity_tools

register_cross_backend_parity_tools(mcp)

from cross_backend_semantic_packet_tools import (
    register_cross_backend_semantic_packet_tools,
)

register_cross_backend_semantic_packet_tools(mcp)

from workflow_runtime.audit_control_tools import register_audit_control_tools

register_audit_control_tools(mcp)

from mathlib_indexing_control_tools import register_mathlib_indexing_control_tools

register_mathlib_indexing_control_tools(mcp, _analysis_write_policy)

from mathlib_term_tools import register_mathlib_term_tools

register_mathlib_term_tools(mcp, _analysis_write_policy)

from mathlib_navigation_tools import register_mathlib_navigation_tools

register_mathlib_navigation_tools(mcp, _analysis_write_policy)

from mathlib_index_validation_tools import register_mathlib_index_validation_tools

register_mathlib_index_validation_tools(mcp)

from mathlib_index_build_tools import register_mathlib_index_build_tools

register_mathlib_index_build_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathlib_grounding_tools import register_mathlib_grounding_tools

register_mathlib_grounding_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from foundations_workflow_tools import register_foundations_workflow_tools

register_foundations_workflow_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from foundation_draft_tools import register_foundation_draft_tools

register_foundation_draft_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from foundation_verify_tools import register_foundation_verify_tools

register_foundation_verify_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from foundation_surface_tools import register_foundation_surface_tools

register_foundation_surface_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from foundation_intake_tools import register_foundation_intake_tools

register_foundation_intake_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_lean_grounding_tools import register_physics_lean_grounding_tools

register_physics_lean_grounding_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from integration_critic_tools import register_integration_critic_tools

register_integration_critic_tools(mcp)

from redefinition_critic_tools import register_redefinition_critic_tools

register_redefinition_critic_tools(mcp)

from api_critic_tools import register_api_critic_tools

register_api_critic_tools(mcp)

from coherence_api_alias_tools import register_coherence_api_alias_tools

register_coherence_api_alias_tools(mcp)

from coherence_gate_alias_tools import register_coherence_gate_alias_tools

register_coherence_gate_alias_tools(mcp)

from coherence_canonicalize_alias_tools import (
    register_coherence_canonicalize_alias_tools,
)

register_coherence_canonicalize_alias_tools(mcp)

from generative_critic_tools import register_generative_critic_tools

_generative_critic_steps = register_generative_critic_tools(mcp)

from coherence_generative_alias_tools import register_coherence_generative_alias_tools

register_coherence_generative_alias_tools(mcp, _generative_critic_steps)
from coherence_inventory_alias_tools import register_coherence_inventory_alias_tools

register_coherence_inventory_alias_tools(mcp)
from coherence_redefinition_alias_tools import (
    register_coherence_redefinition_alias_tools,
)

register_coherence_redefinition_alias_tools(mcp)

from coherence_repair_alias_tools import register_coherence_repair_alias_tools

register_coherence_repair_alias_tools(mcp)

from coherence_integration_alias_tools import register_coherence_integration_alias_tools

register_coherence_integration_alias_tools(mcp)

from coherence_grounding_alias_tools import register_coherence_grounding_alias_tools

register_coherence_grounding_alias_tools(mcp)

from reasoning_index_tools import register_reasoning_index_tools

register_reasoning_index_tools(mcp)

from wiki_suite_tools import register_wiki_suite_tools

register_wiki_suite_tools(mcp, _analysis_write_policy)

from physics_backend_suite_tools import register_physics_backend_suite_tools

register_physics_backend_suite_tools(mcp, _analysis_write_policy)

from derivation_completeness_tools import register_derivation_completeness_tools

register_derivation_completeness_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from grounded_sample_tools import register_grounded_sample_tools

register_grounded_sample_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from derivation_regression_tools import register_derivation_regression_tools

register_derivation_regression_tools(mcp, _analysis_write_policy)


from reasoning_catalog_tools import register_reasoning_catalog_tools

register_reasoning_catalog_tools(mcp)

from reasoning_catalog_render_tools import register_reasoning_catalog_render_tools

register_reasoning_catalog_render_tools(mcp)

from reasoning_flow_tools import register_reasoning_flow_tools

register_reasoning_flow_tools(mcp)

from router_coverage_tools import register_router_coverage_tools

register_router_coverage_tools(mcp)

from skill_coverage_tools import register_skill_coverage_tools

register_skill_coverage_tools(mcp)

from reasoning_coverage_tools import register_reasoning_coverage_tools

register_reasoning_coverage_tools(mcp)

from drift_pathology_tools import register_drift_pathology_tools

register_drift_pathology_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from grounding_debt_tools import register_grounding_debt_tools

register_grounding_debt_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from generative_repair_tools import register_generative_repair_tools

register_generative_repair_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_object_detector_tools import register_physics_object_detector_tools

register_physics_object_detector_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_ir_tools import register_physics_ir_tools

register_physics_ir_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from physics_registry_tools import register_physics_registry_tools

register_physics_registry_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mechanistic_diagram_tools import register_mechanistic_diagram_tools

register_mechanistic_diagram_tools(mcp, lambda path: _graph_layout_write_policy(path))

from theory_evolution_simulate_tools import register_theory_evolution_simulate_tools

register_theory_evolution_simulate_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from theory_evolution_suite_tools import register_theory_evolution_suite_tools

register_theory_evolution_suite_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from theory_evolution_model_tools import register_theory_evolution_model_tools

register_theory_evolution_model_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from plugin_check_tools import register_plugin_check_tools

register_plugin_check_tools(mcp)

from client_discovery_tools import register_client_discovery_tools

register_client_discovery_tools(mcp)

from normalize_workflows_tools import register_normalize_workflows_tools

register_normalize_workflows_tools(mcp, _analysis_write_policy)

from workflow_evolution_tools import register_workflow_evolution_tools

register_workflow_evolution_tools(mcp, lambda path: _graph_layout_write_policy(path))

from task_registry_tools import register_task_registry_tools

register_task_registry_tools(mcp, lambda path: _graph_layout_write_policy(path))

from quality_card_tools import register_quality_card_tools

register_quality_card_tools(mcp, lambda path: _graph_layout_write_policy(path))

from theorem_seed_tools import register_theorem_seed_tools

register_theorem_seed_tools(mcp, _analysis_write_policy)

from thematic_layout_tools import register_thematic_layout_tools

register_thematic_layout_tools(mcp, _analysis_write_policy)


from skill_projection_tools import register_skill_projection_tools

register_skill_projection_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mcp_boundary_tools import register_mcp_boundary_tools

register_mcp_boundary_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from runtime_trace_validation_tools import register_runtime_trace_validation_tools

register_runtime_trace_validation_tools(
    mcp, lambda path: _graph_layout_write_policy(path)
)

from runtime_trace_tools import register_runtime_trace_tools

register_runtime_trace_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from integration_audit_tools import register_integration_audit_tools

register_integration_audit_tools(mcp, _analysis_write_policy)


def _cap_unbounded_timeouts(
    registry: Dict[str, "hub.WorkflowAction"],
) -> Dict[str, "hub.WorkflowAction"]:
    capped: Dict[str, "hub.WorkflowAction"] = {}
    for action_id, item in registry.items():
        if item.command and item.timeout_seconds is None:
            capped[action_id] = dataclasses.replace(
                item, timeout_seconds=_DEFAULT_TIMEOUT_SECONDS
            )
        else:
            capped[action_id] = item
    return capped


# _REGISTRY mirrors scripts/mathformer.py's registry exactly, byte-for-byte,
# for discoverability (mathformer_list_actions/mathformer_show_action/the
# mathformer://actions resource) and NL routing, so a client sees the same
# contract the CLI would show it. _EXEC_REGISTRY is the same registry with
# unbounded timeouts capped (see _DEFAULT_TIMEOUT_SECONDS above) and is used
# only at the moment something actually executes, in mathformer_run_action
# and mathformer_ask's run=True path.
_REGISTRY = hub.build_registry()
_EXEC_REGISTRY = _cap_unbounded_timeouts(_REGISTRY)


def apply_runtime_config(
    *,
    call_log_path: Optional[str] = None,
    default_timeout_seconds: Optional[int] = None,
    allowed_write_roots: Optional[List[str]] = None,
) -> None:
    """Apply service runtime settings that affect MCP execution."""

    global CALL_LOG_PATH, _DEFAULT_TIMEOUT_SECONDS, _EXEC_REGISTRY, _ALLOWED_WRITE_ROOTS
    if call_log_path:
        CALL_LOG_PATH = Path(call_log_path)
    if default_timeout_seconds is not None:
        _DEFAULT_TIMEOUT_SECONDS = int(default_timeout_seconds)
        _EXEC_REGISTRY = _cap_unbounded_timeouts(_REGISTRY)
    if allowed_write_roots is not None:
        _ALLOWED_WRITE_ROOTS = [Path(root).resolve() for root in allowed_write_roots]


def _path_allowed(path: Path) -> bool:
    if _ALLOWED_WRITE_ROOTS is None:
        return True
    resolved = path.resolve()
    for root in _ALLOWED_WRITE_ROOTS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _proofnet_write_policy(paths):
    if _READONLY:
        raise ValueError("ProofNet writes are disabled by the service read-only policy")
    if any(not _path_allowed(path) for path in paths):
        raise ValueError("ProofNet output or cache is outside allowed write roots")


from workflow_graph_layout_tools import register_workflow_graph_layout_tools


def _graph_layout_write_policy(path):
    _analysis_write_policy()
    if not _path_allowed(path):
        raise ValueError("Graph layout output is outside service write roots")


register_workflow_graph_layout_tools(mcp, _graph_layout_write_policy)

from codex_judge_runner_tools import register_codex_judge_runner_tools

register_codex_judge_runner_tools(mcp, _graph_layout_write_policy)

from taxonomic_navigation_tools import register_taxonomic_navigation_tools

register_taxonomic_navigation_tools(mcp, _graph_layout_write_policy)

from lean_build_tools import register_lean_build_tools

register_lean_build_tools(mcp, _graph_layout_write_policy)

from new_qm_source_only_tools import register_new_qm_source_only_tools

register_new_qm_source_only_tools(mcp, _graph_layout_write_policy)

from dirac_recursive_tools import register_dirac_recursive_tools

register_dirac_recursive_tools(mcp, _graph_layout_write_policy)

from famous_generator_tools import register_famous_generator_tools

register_famous_generator_tools(mcp, _graph_layout_write_policy)

from famous_corpus_tools import register_famous_corpus_tools

register_famous_corpus_tools(mcp, _graph_layout_write_policy)

from kb_manage_tools import register_kb_manage_tools

register_kb_manage_tools(mcp, _graph_layout_write_policy)

from premise_kb_index_tools import register_premise_kb_index_tools

register_premise_kb_index_tools(mcp, _graph_layout_write_policy)

from premise_kb_e2e_tools import register_premise_kb_e2e_tools

register_premise_kb_e2e_tools(mcp, _graph_layout_write_policy)

from service_dependency_tools import register_service_dependency_tools

register_service_dependency_tools(mcp)

from dependency_failure_tools import register_dependency_failure_tools

register_dependency_failure_tools(mcp)

from dependency_lock_tools import register_dependency_lock_tools

register_dependency_lock_tools(mcp)

from workflow_graph_render_tools import register_workflow_graph_render_tools

register_workflow_graph_render_tools(mcp, _graph_layout_write_policy)

from mechanistic_figure_tools import register_mechanistic_figure_tools

register_mechanistic_figure_tools(mcp, _graph_layout_write_policy)

from proofnet_tools import register_proofnet_tools

register_proofnet_tools(mcp, _proofnet_write_policy)


def _service_write_root_errors(action_ids: List[str]) -> List[str]:
    errors: List[str] = []
    seen: set[str] = set()

    def visit(action_id: str) -> None:
        if action_id in seen:
            return
        seen.add(action_id)
        item = _REGISTRY.get(action_id)
        if item is None:
            return
        for child in item.depends_on:
            visit(child)
        for write in item.writes:
            write_path = Path(write)
            if not write_path.is_absolute():
                write_path = hub.REPO_ROOT / write_path
            if not _path_allowed(write_path):
                roots = ", ".join(str(root) for root in _ALLOWED_WRITE_ROOTS or [])
                errors.append(
                    f"{action_id} writes outside configured service roots: {write} (allowed: {roots})"
                )

    for action_id in action_ids:
        visit(action_id)
    return errors


def _run_context(
    *, dry_run: bool, allow_mutating: bool, keep_going: bool
) -> "hub.RunContext":
    return hub.RunContext(
        dry_run=dry_run,
        json_output=True,
        keep_going=keep_going,
        allow_mutating=allow_mutating and not _READONLY,
        write_report=False,
    )


def _independent_service_route_guard(action_id, context, repository_root):
    # Explicit mounts must name this service's repository, never a client path.
    if (
        repository_root is not None
        and repository_root.resolve() != hub.REPO_ROOT.resolve()
    ):
        raise ValueError("repository_root must match the service repository mount")
    if not context.dry_run:
        errors = _service_write_root_errors([action_id])
        if errors:
            raise PermissionError("; ".join(errors))
    context.allow_mutating = context.allow_mutating and not _READONLY


from independent_service_route_tools import register_independent_service_route_tools

register_independent_service_route_tools(
    mcp,
    lambda: _EXEC_REGISTRY,
    _independent_service_route_guard,
)

from mcp_serve_route_tools import register_mcp_serve_route_tools

register_mcp_serve_route_tools(
    mcp, lambda: _EXEC_REGISTRY, _independent_service_route_guard
)


def _runtime_trace_guard(context):
    if not context["dry_run"]:
        _analysis_write_policy()
        errors = _service_write_root_errors(["meta-skills:runtime-trace"])
        if errors:
            raise PermissionError("; ".join(errors))


def _quality_full_guard(context, root, registry, action_id="quality:full"):
    """Apply service write ceilings to the explicit native repository mount."""
    if context["dry_run"]:
        return
    _analysis_write_policy()
    pending, seen = [action_id], set()
    while pending:
        action_id = pending.pop()
        if action_id in seen:
            continue
        seen.add(action_id)
        item = registry[action_id]
        pending.extend(item.depends_on)
        for write in item.writes:
            path = Path(write)
            if not _path_allowed(path if path.is_absolute() else root / path):
                raise PermissionError(
                    f"{action_id} writes outside configured service roots: {write}"
                )


def _quality_smoke_guard(context, root, registry):
    """Apply the same service ceilings to the compact gate's native writes."""
    _quality_full_guard(context, root, registry, action_id="quality:smoke")


from repo_diff_check_tools import register_repo_diff_check_tools

register_repo_diff_check_tools(mcp)


from quality_smoke_tools import register_quality_smoke_tools

register_quality_smoke_tools(mcp, _quality_smoke_guard)

from quality_smoke_route_tools import register_quality_smoke_route_tools

register_quality_smoke_route_tools(
    mcp,
    _analysis_write_policy,
    lambda path: _path_allowed(path),
    _cap_unbounded_timeouts,
)

from test_runner_route_tools import register_test_runner_route_tools

register_test_runner_route_tools(
    mcp,
    _analysis_write_policy,
    lambda path: _path_allowed(path),
    _cap_unbounded_timeouts,
)

from textbook_route_tools import register_textbook_route_tools

register_textbook_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from rfde_route_tools import register_rfde_route_tools

register_rfde_route_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))


from review_framework_tools import register_review_framework_tools


def _review_framework_guard(context, root, registry):
    _quality_full_guard(
        context, root, registry, action_id="review:autoformalization-framework"
    )


register_review_framework_tools(mcp, _review_framework_guard)


from quality_full_tools import register_quality_full_tools

register_quality_full_tools(mcp, _quality_full_guard)

from quality_full_route_tools import register_quality_full_route_tools

register_quality_full_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


def _quality_strict_guard(context, root, registry):
    """Apply service ceilings without altering the native strict registry."""
    _quality_full_guard(context, root, registry, action_id="quality:strict")


from quality_strict_tools import register_quality_strict_tools

register_quality_strict_tools(mcp, _quality_strict_guard)

from framework_review_route_tools import register_framework_review_route_tools

register_framework_review_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from quality_strict_route_tools import register_quality_strict_route_tools

register_quality_strict_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


from hub_runtime_trace_tools import register_hub_runtime_trace_tools

register_hub_runtime_trace_tools(mcp, _runtime_trace_guard)


def _paper_claim_audit_guard(context):
    if not context["dry_run"]:
        _analysis_write_policy()
        errors = _service_write_root_errors(["paper:claim-audit-framework"])
        if errors:
            raise PermissionError("; ".join(errors))


def _paper_evidence_packet_guard(path):
    _analysis_write_policy()
    if not _path_allowed(path):
        raise PermissionError(
            f"paper evidence output outside configured service roots: {path}"
        )


def _paper_update_mount_guard(root):
    if root.resolve() != hub.REPO_ROOT.resolve():
        raise PermissionError(
            "independent service requires its configured repository mount"
        )


from paper_update_plan_tools import register_paper_update_plan_tools

register_paper_update_plan_tools(
    mcp, _paper_update_mount_guard, _paper_evidence_packet_guard
)

from paper_workflow_catalog_tools import register_paper_workflow_catalog_tools

register_paper_workflow_catalog_tools(
    mcp, _paper_update_mount_guard, _graph_layout_write_policy
)


from paper_evidence_packet_tools import register_paper_evidence_packet_tools

register_paper_evidence_packet_tools(mcp, _paper_evidence_packet_guard)


from paper_claim_audit_tools import register_paper_claim_audit_tools

register_paper_claim_audit_tools(mcp, _paper_claim_audit_guard)


def _paper_functionality_suite_guard(context):
    if not context["dry_run"]:
        _analysis_write_policy()
        errors = _service_write_root_errors(["paper:functionality-update-suite"])
        if errors:
            raise PermissionError("; ".join(errors))


from paper_functionality_suite_tools import register_paper_functionality_suite_tools

register_paper_functionality_suite_tools(mcp, _paper_functionality_suite_guard)


def _paper_claim_audit_rfde_guard(context):
    if not context["dry_run"]:
        _analysis_write_policy()
        errors = _service_write_root_errors(["paper:claim-audit-rfde"])
        if errors:
            raise PermissionError("; ".join(errors))


from paper_claim_audit_rfde_tools import register_paper_claim_audit_rfde_tools

register_paper_claim_audit_rfde_tools(mcp, _paper_claim_audit_rfde_guard)


def _log_call(
    *,
    action_id: str,
    safety: Optional[str],
    allow_mutating: bool,
    dry_run: bool,
    ok: bool,
) -> None:
    """Append one audit-trail line for a mutating-capable MCP call.

    Read-only-by-construction tools (list/show/audit, or ask without run=True)
    are not logged here; see docs/architecture/MCP_SERVER.md's Observability section for
    why this is a lightweight call log rather than reasoning-log coverage.
    """

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_id": action_id,
        "safety": safety,
        "allow_mutating": allow_mutating,
        "dry_run": dry_run,
        "ok": ok,
    }
    CALL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CALL_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def _atp_demo_guard():
    if _READONLY:
        raise ValueError("ATP execution disabled by service read-only policy")
    errors = _service_write_root_errors(["atp:demo"])
    if errors:
        raise ValueError("; ".join(errors))


from atp_demo_tools import register_atp_demo_tools

_ATP_DEMO_TOOLS = register_atp_demo_tools(mcp, _atp_demo_guard)


def _premise_group_guard(path):
    if _READONLY:
        raise PermissionError("group regression writes artifacts")
    if not _path_allowed(path.resolve()):
        raise PermissionError("group artifact root is outside service write roots")


from premise_group_tools import register_premise_group_tools

register_premise_group_tools(mcp, _premise_group_guard)


def _premise_triple_guard():
    if _READONLY:
        raise PermissionError("triple regression writes artifacts")
    errors = _service_write_root_errors(["atp:premise-guided-triple"])
    if errors:
        raise PermissionError("; ".join(errors))


from premise_triple_tools import register_premise_triple_tools

_TRIPLE_TOOLS = register_premise_triple_tools(mcp, _premise_triple_guard)


def _group_example_guard():
    if _READONLY:
        raise PermissionError("group example disabled by read-only policy")
    errors = _service_write_root_errors(["example:vampire-group"])
    if errors:
        raise PermissionError("; ".join(errors))


def _policy_example_guard():
    if _READONLY:
        raise PermissionError("policy example disabled by read-only policy")
    errors = _service_write_root_errors(["example:vampire-policy"])
    if errors:
        raise PermissionError("; ".join(errors))


from vampire_policy_tools import register_vampire_policy_tools

_POLICY_EXAMPLE_TOOLS = register_vampire_policy_tools(mcp, _policy_example_guard)


def _strict_order_guard():
    if _READONLY:
        raise PermissionError("strict-order example disabled by read-only policy")
    errors = _service_write_root_errors(["example:vampire-strict-order"])
    if errors:
        raise PermissionError("; ".join(errors))


from vampire_strict_order_tools import register_vampire_strict_order_tools

_STRICT_ORDER_TOOLS = register_vampire_strict_order_tools(mcp, _strict_order_guard)


from vampire_group_example_tools import register_vampire_group_example_tools

_GROUP_EXAMPLE_TOOLS = register_vampire_group_example_tools(mcp, _group_example_guard)


def _refresh_reports_guard():
    if _READONLY:
        raise PermissionError("report refresh disabled by read-only policy")
    errors = _service_write_root_errors(["formalphysics:refresh-extra-lean-reports"])
    if errors:
        raise PermissionError("; ".join(errors))


from setup_atp_kb_tools import register_setup_atp_kb_tools

register_setup_atp_kb_tools(mcp, _graph_layout_write_policy)

from setup_atp_kb_route_tools import register_setup_atp_kb_route_tools

register_setup_atp_kb_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from setup_full_route_tools import register_setup_full_route_tools

register_setup_full_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from setup_lean_route_tools import register_setup_lean_route_tools

register_setup_lean_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


from setup_sympy_tools import register_setup_sympy_tools

register_setup_sympy_tools(mcp, _graph_layout_write_policy)

from setup_lean_tools import register_setup_lean_tools

register_setup_lean_tools(mcp, _graph_layout_write_policy)

from setup_python_all_route_tools import register_setup_python_all_route_tools

register_setup_python_all_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from setup_python_all_tools import register_setup_python_all_tools

register_setup_python_all_tools(mcp, _graph_layout_write_policy)

from setup_all_tools import register_setup_all_tools

register_setup_all_tools(mcp, _graph_layout_write_policy)


from formalphysics_refresh_tools import register_refresh_tools

register_refresh_tools(mcp, _refresh_reports_guard)


@mcp.tool()
def mathformer_ask(
    request: str,
    run: bool = False,
    dry_run: bool = False,
    allow_mutating: bool = False,
    family: Optional[str] = None,
    limit: int = 5,
    keep_going: bool = False,
) -> Dict[str, Any]:
    """Resolve a natural-language request to controlled Mathformer workflows.

    Set run=True to execute the top-matched route. Mutating routes (those
    that write environment state or tracked repository files) only execute
    when allow_mutating=True; otherwise they report a blocking preflight
    error so the caller can confirm intent first.
    """

    matches = hub.resolve_intent(request, _REGISTRY, limit=max(1, limit), family=family)
    payload: Dict[str, Any] = {
        "schema_version": 1,
        "ok": bool(matches),
        "request": request,
        "interface": "natural_language",
        "matches": [hub.intent_match_to_dict(match, _REGISTRY) for match in matches],
    }
    if not matches:
        payload["message"] = (
            "No controlled workflow route matched this request. Rephrase with "
            "the desired outcome, backend, or artifact type, or call "
            "mathformer_list_actions to inspect the catalogue."
        )
        return payload
    if run:
        context = _run_context(
            dry_run=dry_run, allow_mutating=allow_mutating, keep_going=keep_going
        )
        root_errors = (
            []
            if dry_run
            else _service_write_root_errors(list(matches[0].route.action_ids))
        )
        if root_errors:
            run_payload = {
                "schema_version": 1,
                "ok": False,
                "status": "blocked_by_service_write_roots",
                "preflight_errors": root_errors,
                "route": hub.intent_match_to_dict(matches[0], _REGISTRY),
            }
        else:
            run_payload = hub.run_intent_match(matches[0], _EXEC_REGISTRY, context)
        payload["selected_route_id"] = matches[0].route.route_id
        payload["run"] = run_payload
        route_action_ids = matches[0].route.action_ids
        first_action = _REGISTRY.get(route_action_ids[0]) if route_action_ids else None
        _log_call(
            action_id=",".join(route_action_ids) or matches[0].route.route_id,
            safety=first_action.safety if first_action else None,
            allow_mutating=allow_mutating,
            dry_run=dry_run,
            ok=bool(run_payload.get("ok")),
        )
    return payload


@mcp.tool()
def mathformer_list_actions(family: Optional[str] = None) -> Dict[str, Any]:
    """List registered Mathformer workflow actions and their safety labels."""

    items = sorted(_REGISTRY.values(), key=lambda item: item.action_id)
    if family:
        items = [item for item in items if item.family == family]
    return {
        "schema_version": 1,
        "ok": True,
        "actions": [hub.action_to_dict(item) for item in items],
    }


@mcp.tool()
def mathformer_show_action(action_id: str) -> Dict[str, Any]:
    """Show the full contract (command, safety, writes, dependencies) for one action id."""

    item = _REGISTRY.get(action_id)
    if item is None:
        return {
            "schema_version": 1,
            "ok": False,
            "error": f"unknown action: {action_id}",
        }
    return {"schema_version": 1, "ok": True, "action": hub.action_to_dict(item)}


@mcp.tool()
def mathformer_run_action(
    action_id: str,
    dry_run: bool = False,
    allow_mutating: bool = False,
    keep_going: bool = False,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Run one registered Mathformer action id directly, bypassing NL routing.

    Use mathformer_list_actions or mathformer_show_action first to confirm the
    action id and its safety label. Actions labeled writes_repo or
    writes_environment require allow_mutating=True.
    """

    context = _run_context(
        dry_run=dry_run, allow_mutating=allow_mutating, keep_going=keep_going
    )
    root_errors = [] if dry_run else _service_write_root_errors([action_id])
    if root_errors:
        result = {
            "schema_version": 1,
            "ok": False,
            "status": "blocked_by_service_write_roots",
            "preflight_errors": root_errors,
            "action": (
                hub.action_to_dict(_REGISTRY[action_id])
                if action_id in _REGISTRY
                else None
            ),
        }
    else:
        result = hub.run_action(
            action_id, _EXEC_REGISTRY, context, extra_args=tuple(extra_args or ())
        )
    item = _REGISTRY.get(action_id)
    _log_call(
        action_id=action_id,
        safety=item.safety if item else None,
        allow_mutating=allow_mutating,
        dry_run=dry_run,
        ok=bool(result.get("ok")),
    )
    return result


@mcp.tool()
def mathformer_list_workflows(
    category: Optional[str] = None,
    query: Optional[str] = None,
    offset: int = 0,
    limit: int = 50,
) -> Dict[str, Any]:
    """Discover every normalized workflow, including declarative contracts.

    Categories are hub, route, loop and profile. Results are paginated; use
    next_offset until null. This does not execute or qualify any binding.
    """
    try:
        catalog = load_catalog()
    except (OSError, ValueError) as exc:
        return {
            "ok": False,
            "status": "workflow_catalog_unavailable",
            "error": str(exc),
        }
    if category is not None and category not in catalog["counts"]:
        return {"ok": False, "status": "unknown_workflow_category", "error": category}
    rows = catalog["workflows"]
    if category:
        rows = [row for row in rows if row["category"] == category]
    if query:
        needle = query.casefold()
        rows = [
            row
            for row in rows
            if needle
            in " ".join([row["id"], row["description"], *row["aliases"]]).casefold()
        ]
    offset, limit = max(0, offset), max(1, min(limit, 1000))
    selected = rows[offset : offset + limit]
    return {
        "schema_version": 1,
        "ok": True,
        "total_count": len(rows),
        "catalog_count": len(catalog["workflows"]),
        "categories": catalog["counts"],
        "offset": offset,
        "next_offset": offset + limit if offset + limit < len(rows) else None,
        "workflows": [
            {
                key: row[key]
                for key in (
                    "id",
                    "aliases",
                    "description",
                    "category",
                    "owner_skill",
                    "coverage",
                    "binding_declared",
                    "runtime_qualified",
                )
            }
            for row in selected
        ],
    }


@mcp.tool()
def mathformer_show_workflow(workflow_id: str) -> Dict[str, Any]:
    """Read a full normalized YAML contract by canonical ID or explicit alias."""
    try:
        row = resolve_workflow(workflow_id)
        text = descriptor_text(row)
    except (OSError, ValueError) as exc:
        return {
            "schema_version": 1,
            "ok": False,
            "status": "workflow_unavailable",
            "error": str(exc),
        }
    return {
        "schema_version": 1,
        "ok": True,
        "workflow": row,
        "workflow_yaml": text,
        "schema_resource": "mathformer://workflow-schema",
    }


@mcp.tool()
def mathformer_run_workflow(
    workflow_id: str,
    dry_run: bool = False,
    allow_mutating: bool = False,
    keep_going: bool = False,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Dispatch a normalized hub/route ID through existing native MCP controls.

    Loop/profile contracts are inspectable specifications without executable
    bindings and return specification_only. This is native-controller dispatch,
    not an interpreter for arbitrary YAML operations or draft generated skills.
    """
    outcome = read_workflow_dispatch(workflow_id)
    if not outcome["loaded"]:
        return unavailable_workflow_dispatch(outcome)
    row = outcome["row"]
    if row["category"] not in ("hub", "route"):
        return specification_workflow_dispatch(outcome)
    native = row["aliases"][0]
    if row["category"] == "hub":
        return {
            "workflow_id": row["id"],
            **mathformer_run_action(
                native,
                dry_run=dry_run,
                allow_mutating=allow_mutating,
                keep_going=keep_going,
                extra_args=extra_args,
            ),
        }
    if extra_args:
        return {"ok": False, "status": "extra_args_for_route", "workflow_id": row["id"]}
    route = next(
        (route for route in hub.build_intent_routes() if route.route_id == native), None
    )
    if route is None:
        return {"ok": False, "status": "native_route_missing", "workflow_id": row["id"]}
    root_errors = [] if dry_run else _service_write_root_errors(list(route.action_ids))
    if root_errors:
        result = {
            "ok": False,
            "status": "blocked_by_service_write_roots",
            "workflow_id": row["id"],
            "preflight_errors": root_errors,
        }
    else:
        match = hub.IntentMatch(route=route, score=0, matched_terms=())
        result = hub.run_intent_match(
            match,
            _EXEC_REGISTRY,
            _run_context(
                dry_run=dry_run,
                allow_mutating=allow_mutating,
                keep_going=keep_going,
            ),
        )
    _log_call(
        action_id=",".join(route.action_ids),
        safety="native_route",
        allow_mutating=allow_mutating,
        dry_run=dry_run,
        ok=bool(result.get("ok")),
    )
    return {"workflow_id": row["id"], **result}


class ProfileDispatchResult(TypedDict):
    result: Dict[str, Any]


def read_workflow_dispatch(workflow_id: str, root: Optional[Path] = None) -> dict:
    """The dispatcher's ordered resolve/read block, including its exact catch set.

    A root selects an isolated repository catalog for read-only inspection. The
    ordinary dispatcher continues using the native dependencies' default root.
    """
    try:
        row = (
            resolve_workflow(workflow_id)
            if root is None
            else resolve_workflow(workflow_id, root)
        )
        if root is None:
            descriptor_text(row)
        else:
            descriptor_text(row, root)
    except (OSError, ValueError) as exc:
        return {"loaded": False, "row": None, "error": str(exc)}
    return {"loaded": True, "row": row, "error": None}


def unavailable_workflow_dispatch(outcome: dict) -> dict:
    """Preserve the native unavailable result as ordinary negative return data."""
    if outcome["loaded"]:
        raise ValueError("unavailable result requires a failed read")
    return {"ok": False, "status": "workflow_unavailable", "error": outcome["error"]}


def specification_workflow_dispatch(outcome: dict) -> dict:
    """The native non-hub/non-route early return; no scientific action follows."""
    if not outcome["loaded"]:
        raise ValueError("specification result requires a successful read")
    row = outcome["row"]
    if row["category"] in ("hub", "route"):
        raise ValueError("executable native dispatch cannot return specification_only")
    return {
        "schema_version": 1,
        "ok": False,
        "status": "specification_only",
        "workflow_id": row["id"],
        "coverage": row["coverage"],
        "message": "Read this contract with mathformer_show_workflow; no executable native binding is declared.",
    }


class ProfileDispatchContext(TypedDict):
    repository_root: str


class ProfileDispatchRead(TypedDict):
    outcome: Dict[str, Any]


_PREMISE_REUSE_IDENTITIES = (
    "profile_premise_retrieval_and_verified_reuse_workflow",
    "premise_retrieval_and_verified_reuse",
)


def _premise_reuse_outcome(outcome: dict) -> None:
    if outcome["loaded"] and (
        outcome["row"]["id"] != _PREMISE_REUSE_IDENTITIES[0]
        or outcome["row"]["category"] != "profile"
    ):
        raise ValueError(
            "only the premise_retrieval_and_verified_reuse profile may be inspected"
        )


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def mathformer_premise_reuse_resolve_and_read(
    workflow_id: Literal[
        "profile_premise_retrieval_and_verified_reuse_workflow",
        "premise_retrieval_and_verified_reuse",
    ],
    context: Optional[ProfileDispatchContext] = None,
) -> ProfileDispatchRead:
    """Resolve and digest-check this profile; read errors are native result data."""
    if workflow_id not in _PREMISE_REUSE_IDENTITIES:
        raise ValueError(
            "only the premise_retrieval_and_verified_reuse profile may be inspected"
        )
    root = None
    if context is not None:
        root = Path(context["repository_root"]).resolve()
        root.relative_to(hub.REPO_ROOT.resolve())
    outcome = read_workflow_dispatch(workflow_id, root)
    _premise_reuse_outcome(outcome)
    return {"outcome": outcome}


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def mathformer_premise_reuse_return_unavailable(outcome: dict) -> ProfileDispatchResult:
    """Return the dispatcher's unavailable status without retry or native actions."""
    _premise_reuse_outcome(outcome)
    return {"result": unavailable_workflow_dispatch(outcome)}


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def mathformer_premise_reuse_return_specification(
    outcome: dict,
) -> ProfileDispatchResult:
    """Return specification_only; this transport success verifies no reuse claim."""
    _premise_reuse_outcome(outcome)
    return {"result": specification_workflow_dispatch(outcome)}


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
def mathformer_formal_proof_discovery_dispatch(
    workflow_id: Literal[
        "profile_formal_proof_discovery_workflow", "formal_proof_discovery"
    ] = "profile_formal_proof_discovery_workflow",
    dry_run: bool = False,
    allow_mutating: bool = False,
    keep_going: bool = False,
    extra_args: Optional[List[str]] = None,
) -> ProfileDispatchResult:
    """Inspect the native proof profile dispatch; no proof search is implemented.

    Keep the native negative status as result data. Successful transport neither
    checks a proof nor makes the declarative scientific dependency graph runnable.
    The restricted identity cannot dispatch a mutating hub action or route.
    """
    if workflow_id not in (
        "profile_formal_proof_discovery_workflow",
        "formal_proof_discovery",
    ):
        raise ValueError("only the formal_proof_discovery profile may be inspected")
    return {
        "result": mathformer_run_workflow(
            workflow_id,
            dry_run=dry_run,
            allow_mutating=allow_mutating,
            keep_going=keep_going,
            extra_args=extra_args,
        )
    }


@mcp.tool()
def mathformer_audit() -> Dict[str, Any]:
    """Audit repository Python entrypoints against the hub, test matrix, and skill-hook contract."""

    return hub.audit_control(_REGISTRY)


@mcp.tool()
def mathformer_help() -> Dict[str, Any]:
    """Quick orientation: list the natural-language workflows this server can resolve.

    Call this first. It returns the curated, human-readable workflow catalogue
    (title, description, example phrasing per workflow) instead of the full
    low-level action registry — use mathformer_ask with a plain-language goal
    next, or mathformer_list_actions only if you need the low-level contract.
    """

    routes = hub.build_intent_routes()
    return {
        "schema_version": 1,
        "ok": True,
        "summary": (
            "Mathformer is a controlled workflow hub for autoformalization, "
            "theorem discovery, premise knowledge bases, and proof artifact "
            "generation across Lean, Vampire ATP, SymPy, Isabelle, and Rocq."
        ),
        "workflow_count": len(routes),
        "normalized_workflow_count": len(load_catalog()["workflows"]),
        "normalized_workflow_catalog": "mathformer://workflows",
        "workflows": [
            {
                "route_id": route.route_id,
                "title": route.title,
                "description": route.description,
                "examples": list(route.examples),
            }
            for route in routes
        ],
        "other_tools": {
            "mathformer_list_workflows": "List/filter all normalized workflow IDs, including loop and reasoning contracts.",
            "mathformer_show_workflow": "Read the complete typed YAML contract and its coverage gaps.",
            "mathformer_run_workflow": "Dispatch a normalized ID through the existing native action/route controls; declarative contracts remain inspection-only.",
            "mathformer_ask": "Resolve a natural-language request to one of these workflows, optionally run it.",
            "mathformer_list_actions": "List the full low-level action registry (advanced; mathformer_ask covers most needs).",
            "mathformer_show_action": "Show one action id's full contract: command, safety, writes, dependencies.",
            "mathformer_run_action": "Run one action id directly, bypassing natural-language routing.",
            "mathformer_audit": "Audit that repository entrypoints are controlled.",
        },
    }


_AGENT_ASSET_CATALOG = None


def _agent_asset_catalog(refresh: bool = False):
    """Freeze canonical skill bytes and native registry-selected workflow assets."""
    global _AGENT_ASSET_CATALOG
    if refresh or _AGENT_ASSET_CATALOG is None:
        catalog = load_catalog()
        root = hub.REPO_ROOT
        directory = root / WORKFLOWS
        source_files = [
            source["path"]
            for row in catalog["workflows"]
            for source in row.get("source_selectors", [])
        ]
        schemas = [
            *directory.glob("*.schema.json"),
            directory.parent / "workflow.schema.json",
        ]
        _AGENT_ASSET_CATALOG = AssetCatalog(
            root,
            skills=(root / "skills").rglob("SKILL.md"),
            workflows=[directory / row["path"] for row in catalog["workflows"]],
            source_files=source_files,
            schema_files=schemas,
        )
    return _AGENT_ASSET_CATALOG


@mcp.tool()
def list_agent_assets(cursor: Optional[str] = None) -> Dict[str, Any]:
    """List exact canonical skill/workflow assets; never execute their contents."""
    return _agent_asset_catalog(refresh=cursor is None).list(cursor)


@mcp.tool()
def read_agent_asset(path: str) -> Dict[str, Any]:
    """Read immutable bytes only for a path declared by list_agent_assets."""
    return _agent_asset_catalog().read(path)


@mcp.resource("mathformer://actions")
def actions_resource() -> str:
    """Full JSON action registry, equivalent to `mathformer.py list --json`."""

    import json

    items = sorted(_REGISTRY.values(), key=lambda item: item.action_id)
    payload = {
        "schema_version": 1,
        "ok": True,
        "actions": [hub.action_to_dict(item) for item in items],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


@mcp.resource("mathformer://workflows")
def workflows_resource() -> str:
    """Complete normalized workflow registry, including canonical and native IDs."""
    return json.dumps(load_catalog(), indent=2)


@mcp.resource("mathformer://workflows/{workflow_id}")
def workflow_resource(workflow_id: str) -> str:
    """Full source-linked normalized descriptor selected by registered identity."""
    return json.dumps(mathformer_show_workflow(workflow_id), indent=2)


@mcp.resource("mathformer://workflow-schema")
def workflow_schema_resource() -> str:
    """Shared workflow-skill/v1 structural schema."""
    return (hub.REPO_ROOT / WORKFLOWS.parent / "workflow.schema.json").read_text()


@mcp.resource("mathformer://reasoning-logs")
def reasoning_logs_resource() -> str:
    """Stable reasoning-log index, built by the reasoning-log hub actions."""

    index_file = hub.REPO_ROOT / "artifacts" / "reasoning" / "index.json"
    if not index_file.exists():
        payload = {
            "schema_version": 1,
            "ok": False,
            "status": "index_missing",
            "index_file": "artifacts/reasoning/index.json",
            "build_action": "control:reasoning-log-index",
            "readiness_action": "control:reasoning-log-consumer-readiness",
        }
        return json.dumps(payload, indent=2, sort_keys=True)
    return index_file.read_text(encoding="utf-8")


@mcp.resource("mathformer://reasoning-log-schema")
def reasoning_log_schema_resource() -> str:
    """Reasoning-log schema and consumer-grade profile."""

    return (
        hub.REPO_ROOT
        / "skills"
        / "control"
        / "reasoning-log-schema-guardian"
        / "references"
        / "schema.md"
    ).read_text(encoding="utf-8")


@mcp.resource("mathformer://reasoning-log-quality-policy")
def reasoning_log_quality_policy_resource() -> str:
    """Machine-readable summary of the reasoning-log quality criteria."""

    payload = {
        "schema_version": 1,
        "ok": True,
        "profile": "consumer-grade",
        "dimensions": [
            "self_contained",
            "self_explanatory",
            "concise",
            "human_understandable",
            "machine_processable",
        ],
        "blocking_findings": [
            "missing_skill_application",
            "missing_intent",
            "missing_human_summary",
            "non_object_skill_application_section",
            "unknown_hook_id",
            "secret_looking_value",
        ],
        "resource_policy": {
            "workflow_level_only": True,
            "no_per_skill_mcp_tools": True,
            "no_arbitrary_file_reads": True,
            "individual_log_access": "via artifacts listed in mathformer://reasoning-logs or controlled hub actions",
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True)


class _BearerAuthMiddleware:
    """Reject streamable-http requests without a matching bearer token.

    A minimal alternative to FastMCP's built-in OAuth-shaped auth subsystem
    (mcp.server.auth), which requires a full issuer_url/AuthSettings even for
    a single shared secret. This checks one static token against the
    Authorization header, which is enough for a trusted-internal deployment
    behind a reverse proxy; it is not a substitute for real OAuth if this
    server is ever exposed to untrusted clients directly.
    """

    def __init__(self, app: Any, token: str) -> None:
        self._app = app
        self._token = token

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        from starlette.responses import JSONResponse

        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        provided = headers.get(b"authorization", b"").decode("latin-1")
        if provided != f"Bearer {self._token}":
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await self._app(scope, receive, send)


class _RateLimitMiddleware:
    """Cap requests per client IP per minute using an in-process sliding window.

    Intentionally process-local, not distributed: this guards a single
    `mcp_server.py --transport streamable-http` instance against one client
    monopolizing it (for example by looping mathformer_run_action on
    test:comprehensive). A multi-instance deployment still needs the
    reverse-proxy rate limiting documented in docs/architecture/MCP_SERVER.md.
    """

    def __init__(self, app: Any, max_per_minute: int) -> None:
        self._app = app
        self._limit = max_per_minute
        self._windows: Dict[str, List[float]] = {}

    async def __call__(self, scope: Dict[str, Any], receive: Any, send: Any) -> None:
        from starlette.responses import JSONResponse

        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = time.monotonic()
        bucket = self._windows.setdefault(key, [])
        cutoff = now - 60.0
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= self._limit:
            response = JSONResponse({"error": "rate_limited"}, status_code=429)
            await response(scope, receive, send)
            return
        bucket.append(now)
        await self._app(scope, receive, send)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional config/mathformer_mcp*.toml service config. CLI flags override config values.",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default=None,
        help="stdio for local MCP clients (default); streamable-http for a shared/remote server.",
    )
    parser.add_argument(
        "--host", default=None, help="Bind host for --transport streamable-http."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Bind port for --transport streamable-http.",
    )
    parser.add_argument(
        "--readonly",
        action="store_true",
        default=None,
        help="Force every tool call to behave as allow_mutating=False, regardless of the caller's argument.",
    )
    parser.add_argument(
        "--auth-token",
        default=None,
        help=(
            "Require this bearer token on --transport streamable-http requests. "
            "Defaults to the MATHFORMER_MCP_TOKEN environment variable. "
            "Ignored for --transport stdio, which has no network surface."
        ),
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=None,
        help="Max requests per client IP per minute on --transport streamable-http. 0 disables the guard.",
    )
    return parser.parse_args(argv)


@mcp.tool()
def mathformer_serve_parse(argv: Optional[List[str]]) -> dict:
    """Parse native server arguments; null retains argparse process-argument semantics."""
    args = vars(parse_args(argv))
    args["has_config"] = bool(args["config"])
    args["config"] = str(args["config"]) if args["config"] is not None else None
    return {"args": args}


@mcp.tool()
def mathformer_serve_load_config(args: dict) -> dict:
    """Load native service configuration and apply its runtime and provider settings."""
    global _AGENTC_SERVICE_CONFIG
    args = argparse.Namespace(**args)
    overrides: dict[str, dict[str, Any]] = {"service": {}, "security": {}}
    if args.transport is not None:
        overrides["service"]["transport"] = args.transport
    if args.host is not None:
        overrides["service"]["host"] = args.host
    if args.port is not None:
        overrides["service"]["port"] = args.port
    if args.readonly is not None:
        overrides["service"]["readonly"] = args.readonly
    if args.rate_limit is not None:
        overrides["service"]["rate_limit_per_minute"] = args.rate_limit
    if args.auth_token is not None:
        overrides["security"]["mcp_bearer_token"] = args.auth_token
    config = load_service_config(
        Path(args.config), cli_overrides=overrides, require_existing=True
    )
    if not config.ok:
        print(
            json.dumps(
                {"ok": False, "errors": list(config.errors)},
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return {"startup": {"valid": False}}
    _AGENTC_SERVICE_CONFIG = config
    runtime = config.runtime_settings()
    apply_runtime_config(
        call_log_path=runtime["call_log_path"],
        default_timeout_seconds=runtime["default_timeout_seconds"],
        allowed_write_roots=runtime["allowed_write_roots"],
    )
    apply_provider_environment(config)
    transport = runtime["transport"]
    host = runtime["host"]
    port = runtime["port"]
    readonly = runtime["readonly"]
    auth_token = runtime["auth_token"]
    rate_limit = runtime["rate_limit"]
    require_auth_for_http = runtime["require_auth_for_http"]
    return {
        "startup": {
            "valid": True,
            "runtime": {
                "transport": transport,
                "host": host,
                "port": port,
                "readonly": readonly,
                "auth_token": auth_token,
                "rate_limit": rate_limit,
                "require_auth_for_http": require_auth_for_http,
            },
        }
    }


@mcp.tool()
def mathformer_serve_defaults(args: dict) -> dict:
    """Resolve the native no-config defaults and explicit CLI overrides."""
    args = argparse.Namespace(**args)
    transport = args.transport or "stdio"
    host = args.host or "127.0.0.1"
    port = args.port if args.port is not None else 8765
    readonly = bool(args.readonly)
    auth_token = (
        args.auth_token
        if args.auth_token is not None
        else os.environ.get("MATHFORMER_MCP_TOKEN")
    )
    rate_limit = args.rate_limit if args.rate_limit is not None else 60
    require_auth_for_http = False
    return {
        "startup": {
            "valid": True,
            "runtime": {
                "transport": transport,
                "host": host,
                "port": port,
                "readonly": readonly,
                "auth_token": auth_token,
                "rate_limit": rate_limit,
                "require_auth_for_http": require_auth_for_http,
            },
        }
    }


@mcp.tool()
def mathformer_serve_invalid_config(startup: dict) -> dict:
    """Return the native invalid-configuration exit code."""
    return {"exit_code": 2}


@mcp.tool()
def mathformer_serve_apply_policy(startup: dict) -> dict:
    """Install the shared read-only policy before serving."""
    global _READONLY
    runtime = startup["runtime"]
    _READONLY = runtime["readonly"]
    return {"runtime": runtime}


@mcp.tool()
def mathformer_serve_stdio(runtime: dict) -> dict:
    """Serve until FastMCP terminates, propagating native exceptions."""
    mcp.run(transport="stdio")
    return {"exit_code": 0}


@mcp.tool()
def mathformer_serve_http(runtime: dict) -> dict:
    """Run the native HTTP guards, middleware and Uvicorn server until shutdown."""
    runtime["transport"]
    host = runtime["host"]
    port = runtime["port"]
    runtime["readonly"]
    auth_token = runtime["auth_token"]
    rate_limit = runtime["rate_limit"]
    require_auth_for_http = runtime["require_auth_for_http"]
    import uvicorn

    if require_auth_for_http and not auth_token:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "streamable-http config requires a bearer token",
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return {"exit_code": 2}

    mcp.settings.host = host
    mcp.settings.port = port
    app = mcp.streamable_http_app()
    if rate_limit > 0:
        app = _RateLimitMiddleware(app, rate_limit)
    if auth_token:
        app = _BearerAuthMiddleware(app, auth_token)
    else:
        print(
            "[mcp_server] WARNING: --transport streamable-http started without "
            "--auth-token/MATHFORMER_MCP_TOKEN. Anyone who can reach "
            f"{host}:{port} can call every tool. Set a token or put "
            "this behind an authenticating reverse proxy.",
            file=sys.stderr,
        )
    uvicorn.run(app, host=host, port=port)
    return {"exit_code": 0}


def main(argv: Optional[List[str]] = None) -> int:
    args = mathformer_serve_parse(argv)["args"]
    startup = (
        mathformer_serve_load_config(args)
        if args["has_config"]
        else mathformer_serve_defaults(args)
    )["startup"]
    if not startup["valid"]:
        return mathformer_serve_invalid_config(startup)["exit_code"]
    runtime = mathformer_serve_apply_policy(startup)["runtime"]
    result = (
        mathformer_serve_stdio(runtime)
        if runtime["transport"] == "stdio"
        else mathformer_serve_http(runtime)
    )
    return result["exit_code"]


from sympy_goal_plan_tools import register_sympy_goal_plan_tools

register_sympy_goal_plan_tools(mcp, _graph_layout_write_policy)

from sympy_source_only_tools import register_sympy_source_only_tools

register_sympy_source_only_tools(mcp, _graph_layout_write_policy)

from recursive_goal_tools import register_recursive_goal_tools

register_recursive_goal_tools(mcp, _graph_layout_write_policy)

from prism_verification_tools import register_prism_verification_tools

register_prism_verification_tools(mcp, _analysis_write_policy)
register_prism_native_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from plugin_sync_tools import register_plugin_sync_tools

register_plugin_sync_tools(mcp, _graph_layout_write_policy)

from plugin_test_tools import register_plugin_test_tools

register_plugin_test_tools(mcp)

from backend_test_tools import register_backend_test_tools

register_backend_test_tools(mcp, _graph_layout_write_policy)


from comprehensive_strict_tools import register_comprehensive_strict_tools

register_comprehensive_strict_tools(mcp)

from atp_family_workflow_tools import register_atp_family_tools

register_atp_family_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from lean_fixture_route_tools import register_lean_fixture_route_tools

register_lean_fixture_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from validate_atp_route_tools import register_validate_atp_route_tools

register_validate_atp_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from control_family_workflow_tools import register_control_family_tools

register_control_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from sympy_family_workflow_tools import register_sympy_family_tools

register_sympy_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from docs_family_workflow_tools import register_docs_family_tools

register_docs_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from environment_family_workflow_tools import register_environment_family_tools

register_environment_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from e2e_family_workflow_tools import register_e2e_family_tools

register_e2e_family_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from isabelle_family_workflow_tools import register_isabelle_family_tools

register_isabelle_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from lean_family_workflow_tools import register_lean_family_tools

register_lean_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathformerphysicslib_family_tools import register_mathformerphysicslib_family_tools

register_mathformerphysicslib_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mathlib_family_workflow_tools import register_mathlib_family_tools

register_mathlib_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from mcp_family_workflow_tools import register_mcp_family_tools

register_mcp_family_tools(mcp, _analysis_write_policy, lambda path: _path_allowed(path))

from paper_family_workflow_tools import register_paper_family_tools

register_paper_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from meta_skills_family_workflow_tools import register_meta_skills_family_tools

register_meta_skills_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from skills_family_workflow_tools import register_skills_family_tools

register_skills_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_lean_family_tools import register_physics_lean_family_tools

register_physics_lean_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


from rfde_family_workflow_tools import register_rfde_family_tools

register_rfde_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


from lean_consistency_workflow_tools import register_lean_consistency_tools

register_lean_consistency_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)


from isabelle_trace_workflow_tools import register_isabelle_trace_tools

# Embedding hosts provision scoped services through this registry's open API.
isabelle_trace_registry = register_isabelle_trace_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from repo_status_tools import register_repo_status_tools

register_repo_status_tools(mcp)

from textbook_family_workflow_tools import register_textbook_family_tools

register_textbook_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from derivation_completeness_route_tools import (
    register_derivation_completeness_route_tools,
)

register_derivation_completeness_route_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

from textbook_chapter_workflow_tools import register_textbook_chapter_tools

register_textbook_chapter_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from physics_sympy_family_workflow_tools import register_physics_sympy_family_tools

register_physics_sympy_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

from adversarial_validation_tools import register_adversarial_validation_tools

register_adversarial_validation_tools(mcp, config_getter=lambda: _AGENTC_SERVICE_CONFIG)

from source_family_workflow_tools import register_source_family_tools

register_source_family_tools(
    mcp, _analysis_write_policy, lambda path: _path_allowed(path)
)

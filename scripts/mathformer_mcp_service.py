#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Provide a stable independent-service entrypoint for deploying the whole
#   Mathformer pipeline over MCP.
#
# Intent:
#   Keep scripts/mcp_server.py as the MCP implementation while this wrapper
#   owns service config loading, self-checks, and operator-facing launch
#   semantics.
#
# Function:
#   Validates service config, runs dependency/hub/router/auth checks in
#   --self-check mode, or delegates to scripts/mcp_server.py for serving.
#
# Maintenance Notes:
#   Keep release checks synchronized with
#   docs/operations/INDEPENDENT_MCP_SERVICE_TODOS.md.

"""Independent Mathformer MCP service launcher."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import mathformer as hub  # noqa: E402
from workflow_catalog import load_catalog  # noqa: E402
from mcp_service_config import (
    load_service_config,
    provider_environment,
    redacted_config,
    scan_paths_for_secrets,
    service_config_report,
    tracked_service_files,
)  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "mathformer_mcp.local.toml"


def build_local_router_coverage() -> dict[str, Any]:
    routes = hub.build_intent_routes()
    registry = hub.build_registry()
    families = sorted({action.family for action in registry.values()})
    covered: set[str] = set()
    for route in routes:
        for action_id in route.action_ids:
            if action_id in registry:
                covered.add(registry[action_id].family)
            elif action_id.startswith("test:family:"):
                covered.add(action_id.rsplit(":", 1)[1])
    missing = sorted(set(families) - covered)
    return {
        "ok": not missing,
        "family_count": len(families),
        "covered_family_count": len(covered),
        "missing_families": missing,
        "route_count": len(routes),
    }


def dependency_probe() -> dict[str, Any]:
    from probe_mcp_service_dependencies import build_dependency_report

    return build_dependency_report()


def service_coverage_report(
    config_path: Path, config_data: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    registry = hub.build_registry()
    routes = hub.build_intent_routes()
    family_actions: dict[str, int] = {}
    family_routes: dict[str, int] = {}
    for action in registry.values():
        family_actions[action.family] = family_actions.get(action.family, 0) + 1
    for route in routes:
        families = set()
        for action_id in route.action_ids:
            if action_id in registry:
                families.add(registry[action_id].family)
            elif action_id.startswith("test:family:"):
                families.add(action_id.rsplit(":", 1)[1])
        for family in families:
            family_routes[family] = family_routes.get(family, 0) + 1
    return {
        "schema_version": 1,
        "config_path": str(config_path),
        "config_requirements": {
            "api_key_source": "config/",
            "allowed_write_roots": (
                [config_data.get("paths", {}).get("artifacts_dir", "artifacts")]
                if config_data
                else ["artifacts"]
            ),
            "requires_http_auth": (
                bool(config_data.get("security", {}).get("require_auth_for_http"))
                if config_data
                else False
            ),
            "readonly_default": (
                bool(config_data.get("service", {}).get("readonly"))
                if config_data
                else False
            ),
        },
        "mcp_tools": [
            *[
                "mathformer_probe_" + step
                for step in (
                    "initialize",
                    "inspect_probe",
                    "retain_empty",
                    "build_report",
                    "publish",
                )
            ],
            *[
                "mathformer_skills_family_" + step
                for step in (
                    "enter",
                    "snapshot",
                    "prepare",
                    "retain_empty",
                    "advance",
                    "finalize",
                    "saved_report",
                    "publish",
                )
            ],
            *[
                "mathformer_independent_service_" + step
                for step in (
                    "inputs",
                    "initialize",
                    "select_action",
                    "run_child",
                    "advance",
                    "finish",
                )
            ],
            *[
                "mathformer_physicslib_" + step
                for step in (
                    "parse",
                    "enter",
                    "snapshot_frame",
                    "prepare",
                    "cursor_guard",
                    "retain",
                    "advance",
                    "snapshot",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_control_family_" + step
                for step in (
                    "prepare",
                    "cursor_guard",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_docs_" + step
                for step in (
                    "parse",
                    "prepare",
                    "guard",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_sympy_controlled_suite_" + step
                for step in (
                    "initialize",
                    "preflight_step",
                    "preflight_failure",
                    "prepare_cases",
                    "run_case",
                    "collect_case",
                    "skip_cases",
                    "finish",
                )
            ],
            *[
                "mathformer_sympy_equational_trace_" + step
                for step in (
                    "initialize",
                    "preflight_step",
                    "preflight_failure",
                    "prepare_cases",
                    "suite_case",
                    "collect_case",
                    "skip_cases",
                    "finish",
                )
            ],
            *[
                "mathformer_plugin_test_" + step
                for step in ("initialize", "next", "finish")
            ],
            *[
                "mathformer_plugin_sync_" + step
                for step in (
                    "project",
                    "discover_stale",
                    "compare_pack",
                    "write_next",
                    "reset_cursor",
                    "remove_next",
                    "return_differences",
                    "skip_sweep",
                )
            ],
            *[
                "mathformer_setup_sympy_" + step
                for step in (
                    "prepare_boundary",
                    "return_preflight",
                    "launch_installer",
                    "audit_result",
                )
            ],
            *[
                "mathformer_rocq_wiki_suite_" + step
                for step in ("prepare", "draft", "check", "aggregate")
            ],
            *[
                "mathformer_rocq_self_test_" + step
                for step in (
                    "initialize",
                    "draft_next",
                    "begin_reread",
                    "validate_next",
                    "aggregate",
                )
            ],
            *[
                "mathformer_review_framework_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_repo_diff_check_" + step
                for step in (
                    "admit",
                    "reject",
                    "prepare",
                    "early_return",
                    "launch",
                    "finish",
                )
            ],
            *[
                "mathformer_quality_smoke_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_sympy_source_only_" + step
                for step in ("prepare", "pack_state", "execute_stage", "assess", "emit")
            ],
            *[
                "mathformer_semantic_packet_" + step
                for step in ("inspect", "collect", "align", "assemble")
            ],
            *[
                "mathformer_pathology_repair_" + step
                for step in ("aggregate", "assign_status", "assemble")
            ],
            *[
                "mathformer_generative_repair_" + step
                for step in (
                    "load",
                    "prepare",
                    "prompts",
                    "guards",
                    "assemble",
                    "emit",
                    "help",
                )
            ],
            *[
                "mathformer_foundation_surface_" + step
                for step in (
                    "parse",
                    "fixture",
                    "load",
                    "design",
                    "modules",
                    "assemble",
                    "check_self_test",
                    "emit",
                    "help",
                )
            ],
            *[
                "mathformer_dirac_" + step
                for step in (
                    "load_and_pack",
                    "write_next_source",
                    "build_grounding",
                    "compile_next",
                    "review_next",
                    "check_next",
                    "compute_guards",
                    "return_status",
                    "write_reports",
                )
            ],
            *[
                "mathformer_physics_objects_" + step
                for step in (
                    "parse_cli",
                    "fixed_fixture",
                    "load_inputs",
                    "initialize_state",
                    "accumulate_detections",
                    "finalize_packet",
                    "check_and_emit",
                    "help",
                )
            ],
            *[
                "mathformer_physics_grounding_" + step
                for step in (
                    "initialize_scan",
                    "audit_next",
                    "assert_grounding",
                    "retain_cases",
                    "empty_traversal",
                    "initialize_updates",
                    "update_next",
                    "emit_audit",
                )
            ],
            *[
                "mathformer_paper_catalog_" + step
                for step in (
                    "parse_paths",
                    "load_graph",
                    "catalogue",
                    "write_outputs",
                    "emit_result",
                    "print_json",
                    "print_text",
                )
            ],
            *[
                "mathformer_paper_update_" + step
                for step in ("prepare", "load", "build", "publish", "finish")
            ],
            *[
                "mathformer_figure_" + step
                for step in ("load", "svg", "tex", "pdf", "report", "carry", "help")
            ],
            *[
                "mathformer_paper_evidence_" + step
                for step in (
                    "parse",
                    "build_all",
                    "build_one",
                    "finalize",
                    "write",
                    "emit",
                )
            ],
            *[
                "mathformer_meta_suite_" + step
                for step in ("initialize", "select", "run", "append", "finalize")
            ],
            *[
                "mathformer_taxonomic_" + step
                for step in (
                    "initialize",
                    "evaluate_case",
                    "advance",
                    "empty_state",
                    "finalize",
                    "finish_cli",
                )
            ],
            *[
                "mathformer_skill_projections_" + step
                for step in (
                    "initialize",
                    "registry_iteration",
                    "prepare_card_pass",
                    "card_iteration",
                    "write_cards",
                    "write_report",
                )
            ],
            *[
                "mathformer_trace_validation_" + step
                for step in (
                    "initialize",
                    "validate_file",
                    "accumulate",
                    "empty_state",
                    "write_report",
                )
            ],
            *[
                "mathformer_task_registry_" + step
                for step in (
                    "initialize",
                    "validate_accumulate",
                    "empty_state",
                    "write_report",
                )
            ],
            *[
                "mathformer_quality_cards_" + step
                for step in ("initialize", "validate_next", "empty", "write_report")
            ],
            *[
                "mathformer_self_check_" + step
                for step in (
                    "load_config",
                    "probe_dependencies",
                    "router_coverage",
                    "audit_hub",
                    "scan_secrets",
                    "build_coverage",
                    "evaluate_auth",
                    "assemble_report",
                    "emit",
                )
            ],
            *[
                "mathformer_theory_simulate_" + step
                for step in (
                    "load",
                    "initialize_run",
                    "prepare_phase",
                    "advance_step",
                    "finish_phase",
                    "finish_run",
                    "report",
                )
            ],
            *[
                "mathformer_plugin_check_" + step
                for step in ("project", "find_stale", "compare", "report")
            ],
            *[
                "mathformer_service_dependencies_" + step
                for step in (
                    "initialize",
                    "package_next",
                    "tool_next",
                    "classify",
                    "requirements",
                    "assemble",
                )
            ],
            *[
                "mathformer_terms_" + step
                for step in (
                    "initialize",
                    "select_fixture",
                    "annotate",
                    "check_append",
                    "write_report",
                    "emit",
                )
            ],
            *[
                "mathformer_navigation_" + step
                for step in (
                    "require_text",
                    "plan",
                    "monotonic",
                    "finish_self_test",
                    "emit",
                )
            ],
            *[
                "mathformer_physics_release_" + step
                for step in (
                    "build",
                    "coherence",
                    "lean_version",
                    "scan_imports",
                    "assess",
                    "write_report",
                )
            ],
            *[
                "mathformer_physics_registry_" + step
                for step in (
                    "discover",
                    "build",
                    "write",
                    "check_guard",
                    "check",
                    "emit",
                    "skip_write",
                    "skip_check",
                )
            ],
            *[
                "mathformer_redefinition_critic_" + step
                for step in ("initialize", "visit_concept", "finish_report")
            ],
            *[
                "mathformer_parity_" + step
                for step in (
                    "prepare",
                    "select_case",
                    "build_packet",
                    "append_case",
                    "empty",
                    "report",
                )
            ],
            *[
                "mathformer_concept_canonicalize_" + step
                for step in (
                    "prepare",
                    "self_test",
                    "canonicalize",
                    "finish",
                    "stopped",
                )
            ],
            *[
                "mathformer_coherence_loop_" + step
                for step in (
                    "prepare_directory",
                    "inventory",
                    "canonicalize",
                    "audit_grounding",
                    "compare_previous",
                    "critics",
                    "plan_and_gate",
                    "write_reports",
                    "check_and_summarize",
                )
            ],
            *[
                "mathformer_coherence_repair_" + step
                for step in (
                    "parse_arguments",
                    "load_reports",
                    "default_reports",
                    "plan",
                    "write_output",
                    "emit",
                )
            ],
            *[
                "mathformer_coherence_inventory_" + step
                for step in (
                    "parse",
                    "fixture",
                    "canonicalize",
                    "grounding",
                    "critics",
                    "finish",
                    "inventory",
                    "emit",
                )
            ],
            *[
                "mathformer_api_critic_" + step
                for step in ("initialize", "visit", "finish")
            ],
            *[
                "mathformer_coherence_gate_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_api_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_canonicalize_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_inventory_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_redefinition_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_repair_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_integration_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_grounding_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_generative_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "prepare_child",
                    "reports",
                    "plan",
                    "carry_stage",
                    "complete_child",
                    "skip_child",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_license_inventory_" + step
                for step in ("parse", "help", "collect", "render", "mkdir", "write")
            ],
            *[
                "mathformer_physics_backend_" + step
                for step in (
                    "prepare_controlled",
                    "collect_plan",
                    "begin_arguments",
                    "append_argument",
                    "finish_controlled",
                    "begin_adversarial",
                    "check_fixture",
                    "derivation_regression",
                    "thoroughness_regression",
                    "write_suite",
                )
            ],
            *[
                "mathformer_derivation_" + step
                for step in (
                    "self_test",
                    "fixture",
                    "formal_case",
                    "assertions",
                    "persist",
                    "emit_return",
                )
            ],
            *[
                "mathformer_wiki_suite_" + step
                for step in (
                    "prepare",
                    "case_step",
                    "empty_cases",
                    "compile_gold",
                    "audit",
                    "check_declarations",
                    "skip_declarations",
                    "finish",
                )
            ],
            *[
                "mathformer_kb_skill_scripts_" + step
                for step in ("prepare", "generate", "index", "finish")
            ],
            *[
                "mathformer_kb_manage_" + step
                for step in (
                    "prepare",
                    "initialize",
                    "ingest",
                    "index",
                    "refresh",
                    "query",
                    "enqueue",
                    "curate",
                    "report",
                    "finish",
                )
            ],
            *[
                "mathformer_kb_index_" + step
                for step in (
                    "initialize",
                    "ingest_file",
                    "files_empty",
                    "retain",
                    "ingest_vampire",
                    "build_bloom",
                    "build_embeddings",
                    "search",
                    "report",
                )
            ],
            *[
                "mathformer_theorem_seed_" + step
                for step in (
                    "parse",
                    "inspect",
                    "retain",
                    "skip",
                    "done",
                    "write",
                    "help",
                    "halt",
                )
            ],
            *[
                "mathformer_seed_" + step
                for step in ("parse", "open", "append", "advance", "slice", "write")
            ],
            *[
                "mathformer_kb_e2e_" + step
                for step in (
                    "prepare",
                    "populate",
                    "query",
                    "update_report",
                    "assess",
                    "emit",
                )
            ],
            *[
                "mathformer_isabelle_wiki_" + step
                for step in ("prepare", "ground", "draft", "execute", "finalize")
            ],
            *[
                "mathformer_e2e_family_" + step
                for step in (
                    "prepare",
                    "cursor_done",
                    "advance",
                    "retain_empty",
                    "finalize",
                )
            ],
            *[
                "mathformer_isabelle_family_" + step
                for step in (
                    "prepare",
                    "pending",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_physics_sympy_family_" + step
                for step in (
                    "enter",
                    "snapshot",
                    "prepare",
                    "pending",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_paper_family_" + step
                for step in (
                    "enter",
                    "snapshot",
                    "prepare",
                    "pending",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_rfde_family_" + step
                for step in (
                    "enter",
                    "snapshot",
                    "prepare",
                    "pending",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_meta_skills_family_" + step
                for step in (
                    "prepare",
                    "pending",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_atp_family_" + step
                for step in (
                    "prepare",
                    "guard",
                    "advance",
                    "retain_empty",
                    "finalize",
                    "publish",
                )
            ],
            *[
                "mathformer_audit_" + step
                for step in (
                    "registered",
                    "matrix",
                    "hooks",
                    "pack_sources",
                    "inspect_paths",
                    "dependencies",
                    "report",
                )
            ],
            *[
                "mathformer_group_example_" + step
                for step in (
                    "read_statement",
                    "initialize_search",
                    "direct_attempt",
                    "carry_candidate",
                    "finalize_report",
                    "print_and_check",
                    "return_code",
                )
            ],
            *[
                "mathformer_graph_render_" + step
                for step in (
                    "prepare_directory",
                    "load_catalogue",
                    "assemble_model",
                    "publish",
                )
            ],
            *[
                "mathformer_library_docs_" + step
                for step in (
                    "configure",
                    "collect_modules",
                    "publish_docs",
                    "complete_main",
                )
            ],
            *[
                "mathformer_router_coverage_" + step
                for step in (
                    "initialize",
                    "begin_route",
                    "visit_action",
                    "finish_route",
                    "finalize",
                    "empty_state",
                )
            ],
            *[
                "mathformer_skill_coverage_" + step
                for step in (
                    "load_and_pack",
                    "classify_one",
                    "pack_empty_state",
                    "thresholds_and_pack",
                    "inspect_contract",
                    "finalize",
                )
            ],
            *[
                "mathformer_reasoning_smoke_" + step
                for step in (
                    "create_fixture",
                    "validate_fixture",
                    "render_fixture",
                    "audit_coverage",
                    "finish",
                )
            ],
            *[
                "mathformer_reasoning_summary_" + step
                for step in (
                    "load",
                    "validate",
                    "audit",
                    "initialize",
                    "advance",
                    "finish",
                )
            ],
            *[
                "mathformer_reasoning_index_" + step
                for step in ("load", "advance", "finalize")
            ],
            *[
                "mathformer_reasoning_catalog_" + step
                for step in ("construct", "compare", "construction_failure", "emit")
            ],
            *[
                "mathformer_coherence_suite_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_coherence_alias_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                    "return_result",
                )
            ],
            *[
                "mathformer_readiness_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            "mathformer_help",
            "mathformer_ask",
            "mathformer_list_actions",
            "mathformer_show_action",
            "mathformer_run_action",
            "mathformer_audit",
            *[
                "mathformer_prism_" + step
                for step in (
                    "initialize",
                    "validate_entry",
                    "prepare_runtime",
                    "await_entry",
                    "finish_runtime",
                    "write_report",
                    "close",
                )
            ],
            *[
                "mathformer_prism_route_" + step
                for step in (
                    "initialize",
                    "validate_entry",
                    "await_entry",
                    "retain_state",
                    "finalize",
                    "close",
                )
            ],
            *[
                "mathformer_client_discovery_" + step
                for step in ("collect", "initialize", "check", "advance", "aggregate")
            ],
            *[
                "mathformer_isabelle_trace_" + step
                for step in (
                    "reason",
                    "first",
                    "repair",
                    "record",
                    "assemble",
                    "verify",
                )
            ],
            *[
                "mathformer_lean_fixture_route_" + step
                for step in (
                    "initialize",
                    "select_action",
                    "invoke_action",
                    "advance",
                    "finish",
                )
            ],
            "mathformer_list_workflows",
            "mathformer_show_workflow",
            "mathformer_run_workflow",
            *[
                "mathformer_provenance_tests_" + step
                for step in (
                    "prepare",
                    "initialize",
                    "run_case",
                    "advance",
                    "inactive",
                    "finish",
                    "early",
                )
            ],
            *[
                "mathformer_quality_full_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_quality_strict_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_control_all_" + step
                for step in (
                    "admit",
                    "reject",
                    "initialize",
                    "visit",
                    "advance",
                    "finish",
                    "carry",
                )
            ],
            *[
                "mathformer_control_audit_" + step
                for step in (
                    "initialize_route",
                    "admit",
                    "initialize_dependencies",
                    "visit",
                    "advance",
                    "finish_dependencies",
                    "reject",
                    "carry",
                    "finish_route",
                )
            ],
            "mathformer_adoption_admit",
            "mathformer_adoption_reject",
            "mathformer_adoption_initialize",
            "mathformer_adoption_visit_child",
            "mathformer_adoption_advance",
            "mathformer_adoption_finish",
            *[
                "mathformer_validate_" + step
                for step in (
                    "load",
                    "initialize",
                    "check_surface",
                    "advance_guard",
                    "finish",
                )
            ],
            "mathformer_describe_parse",
            "mathformer_describe_load",
            "mathformer_describe_emit",
            "mathformer_describe_error",
            "mathformer_receipt_read_check",
            "mathformer_receipt_pack_cursor",
            "mathformer_receipt_validate_event",
            "mathformer_receipt_finish_joins",
            "mathformer_receipt_validate",
            "mathformer_receipt_base_rows",
            "mathformer_receipt_append_metadata",
            "mathformer_receipt_assemble_html",
            *[
                "mathformer_profile_" + step
                for step in (
                    "normalize_and_pack_cycles",
                    "dependencies_expand_annotate",
                    "initialize_concepts",
                    "concept_round_and_pack",
                    "concepts_once_or_skip",
                    "context_draft_and_hard_check",
                    "initialize_refinement",
                    "refinement_round_and_pack",
                    "finalize_without_refinement",
                    "save_check_audit_report",
                    "advance_cycles_and_guards",
                    "finish",
                    "retain_unrefined",
                )
            ],
            *[
                "mathformer_agentc_" + step
                for step in (
                    "initialize_and_assess",
                    "compute_iteration_guard",
                    "record_early_stop",
                    "formal_repair_round",
                    "semantic_repair_round",
                )
            ],
        ],
        "normalized_workflows": {
            "count": len(load_catalog()["workflows"]),
            "categories": load_catalog()["counts"],
            "catalog_resource": "mathformer://workflows",
            "schema_resource": "mathformer://workflow-schema",
            "execution": "native hub/route dispatch and AgentC refinement steps; other declarative loops and profiles are inspectable",
        },
        "families": {
            family: {
                "action_count": family_actions.get(family, 0),
                "route_count": family_routes.get(family, 0),
                "external_tools": {
                    "lean": family in {"lean", "physics_lean", "mathformerphysicslib"},
                    "vampire": family == "atp",
                    "rocq": family == "rocq",
                    "isabelle": family in {"isabelle", "physics_isabelle"},
                    "provider_sdk": family
                    in {"generative", "physics_lean", "mathformerphysicslib"},
                    "network": family in {"benchmark", "paper", "mathlib"},
                },
            }
            for family in sorted(family_actions)
        },
    }


def evaluate_self_check_auth(config) -> dict[str, Any]:
    ok = (
        config.get("service", "transport") != "streamable-http"
        or not config.get("security", "require_auth_for_http")
        or bool(config.get("security", "mcp_bearer_token"))
        or config.source_kind == "example"
    )
    return {
        "ok": ok,
        "transport": config.get("service", "transport"),
        "require_auth_for_http": config.get("security", "require_auth_for_http"),
        "has_token": bool(config.get("security", "mcp_bearer_token")),
    }


def assemble_self_check_report(
    config, dependencies, router, audit, secret_findings, coverage, auth
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "style": "mathformer_mcp_service_self_check",
        "ok": bool(
            config.ok
            and dependencies.get("ok")
            and router.get("ok")
            and audit.get("ok")
            and auth["ok"]
            and not secret_findings
        ),
        "config": service_config_report(config),
        "provider_env_keys": sorted(provider_environment(config)),
        "dependencies": dependencies,
        "router_coverage": router,
        "hub_audit": {
            "ok": audit.get("ok"),
            "entrypoint_count": audit.get("entrypoint_count"),
            "controlled_count": audit.get("controlled_count"),
            "uncontrolled_entrypoints": audit.get("uncontrolled_entrypoints"),
        },
        "auth_policy": auth,
        "secret_scan_findings": secret_findings,
        "service_coverage": coverage,
        "redacted_config": redacted_config(config),
    }
    return payload


def emit_self_check(
    payload: dict[str, Any], exit_code: int, *, json_output: bool = True
) -> int:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("ok" if payload["ok"] else "failed")
    return exit_code


def self_check(config_path: Path) -> dict[str, Any]:
    config = load_service_config(config_path, require_existing=True)
    dependencies = dependency_probe()
    router = build_local_router_coverage()
    audit = hub.audit_control(hub.build_registry())
    secret_findings = scan_paths_for_secrets(tracked_service_files())
    coverage = service_coverage_report(config_path, config.data)
    auth = evaluate_self_check_auth(config)
    return assemble_self_check_report(
        config, dependencies, router, audit, secret_findings, coverage, auth
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--transport", choices=["stdio", "streamable-http"])
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--readonly", action="store_true", default=None)
    parser.add_argument("--auth-token")
    parser.add_argument("--rate-limit", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_check:
        payload = self_check(args.config)
        return emit_self_check(
            payload, 0 if payload["ok"] else 1, json_output=args.json
        )

    forwarded = ["--config", str(args.config)]
    for flag, value in (
        ("--transport", args.transport),
        ("--host", args.host),
        ("--port", args.port),
        ("--auth-token", args.auth_token),
        ("--rate-limit", args.rate_limit),
    ):
        if value is not None:
            forwarded.extend([flag, str(value)])
    if args.readonly:
        forwarded.append("--readonly")
    import mcp_server

    return mcp_server.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

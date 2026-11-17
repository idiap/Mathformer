#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   scripts/mcp_server.py has no automated coverage: earlier verification was a
#   manual one-off client/server handshake run by hand during development.
#
# Intent:
#   Boot the real server subprocess over real stdio transport and drive it
#   through an actual MCP ClientSession, so the test exercises the same path a
#   real MCP client uses instead of FastMCP's in-process dispatch helpers.
#
# Function:
#   Deterministic check consumed by tests/test_program/run_comprehensive_tests.py
#   under the `mcp` module family, and runnable standalone for local debugging.
#
# Maintenance Notes:
#   Keep EXPECTED_TOOL_TO_SUBCOMMAND synchronized with scripts/mcp_server.py's
#   @mcp.tool() functions and scripts/mathformer.py's subcommands; the
#   tool/CLI sync check below fails loudly on drift in either direction.

"""Deterministic self-test for the Mathformer MCP server."""

from __future__ import annotations

import argparse
from mcp.types import TextResourceContents
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

EXPECTED_TOOL_TO_SUBCOMMAND = {
    "mathformer_ask": "ask",
    "mathformer_list_actions": "list",
    "mathformer_show_action": "show",
    "mathformer_run_action": "run",
    "mathformer_audit": "audit",
}

# Help and normalized-workflow tools are MCP-native, not 1:1 CLI mirrors.
# Track them explicitly while keeping CLI-mirroring tools in exact sync.
MCP_NATIVE_TOOLS = {
    "list_agent_assets",
    "read_agent_asset",
    *{
        "mathformer_agentc_" + step
        for step in (
            "initialize_and_assess",
            "compute_iteration_guard",
            "record_early_stop",
            "formal_repair_round",
            "semantic_repair_round",
        )
    },
    "mathformer_help",
    "mathformer_list_workflows",
    "mathformer_show_workflow",
    "mathformer_run_workflow",
}
EXPECTED_RESOURCES = {
    "mathformer://actions",
    "mathformer://reasoning-logs",
    "mathformer://reasoning-log-schema",
    "mathformer://reasoning-log-quality-policy",
    "mathformer://workflows",
    "mathformer://workflow-schema",
}


def cli_subcommands() -> set:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import argparse as argparse_module

    import mathformer as hub

    parser = hub.build_parser()
    for action in parser._actions:
        if isinstance(action, argparse_module._SubParsersAction):
            return set(action.choices.keys())
    return set()


def run_cli_json(*args: str) -> Dict[str, Any]:
    result = subprocess.run(
        [PYTHON, "scripts/mathformer.py", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    return json.loads(result.stdout)


def tool_result(call_result: Any) -> Dict[str, Any]:
    if call_result.structuredContent and "result" in call_result.structuredContent:
        return call_result.structuredContent["result"]
    return json.loads(call_result.content[0].text)


async def run_checks() -> Tuple[bool, List[Dict[str, Any]]]:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from pydantic import AnyUrl

    checks: List[Dict[str, Any]] = []
    params = StdioServerParameters(
        command=PYTHON, args=["scripts/mcp_server.py"], cwd=str(REPO_ROOT)
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = {t.name for t in tools.tools}
            checks.append(
                {
                    "id": "tools.expected_set",
                    "ok": tool_names
                    == set(EXPECTED_TOOL_TO_SUBCOMMAND) | MCP_NATIVE_TOOLS,
                    "detail": sorted(tool_names),
                }
            )

            expected_subcommands = set(EXPECTED_TOOL_TO_SUBCOMMAND.values())
            actual_subcommands = cli_subcommands()
            checks.append(
                {
                    "id": "tools.cli_sync",
                    "ok": expected_subcommands == actual_subcommands,
                    "detail": {
                        "expected_subcommands": sorted(expected_subcommands),
                        "actual_cli_subcommands": sorted(actual_subcommands),
                    },
                }
            )

            help_result = tool_result(await session.call_tool("mathformer_help", {}))
            sys.path.insert(0, str(REPO_ROOT / "scripts"))
            import mathformer as hub_module

            expected_workflow_count = len(hub_module.build_intent_routes())
            checks.append(
                {
                    "id": "help.lists_curated_workflows",
                    "ok": help_result.get("ok") is True
                    and help_result.get("workflow_count") == expected_workflow_count
                    and len(help_result.get("workflows", [])) == expected_workflow_count
                    and all(
                        {"route_id", "title", "description", "examples"} <= set(item)
                        for item in help_result.get("workflows", [])
                    ),
                    "detail": {"workflow_count": help_result.get("workflow_count")},
                }
            )

            resources = await session.list_resources()
            resource_uris = {str(r.uri) for r in resources.resources}
            checks.append(
                {
                    "id": "resources.expected_set_visible",
                    "ok": EXPECTED_RESOURCES <= resource_uris,
                    "detail": sorted(resource_uris),
                }
            )

            from workflow_catalog import load_catalog

            catalog = load_catalog()
            workflows = tool_result(
                await session.call_tool("mathformer_list_workflows", {"limit": 1000})
            )
            expected_ids = {row["id"] for row in catalog["workflows"]}
            checks.append(
                {
                    "id": "workflows.complete_normalized_catalog",
                    "ok": workflows.get("ok") is True
                    and workflows.get("total_count") == len(expected_ids)
                    and {row["id"] for row in workflows.get("workflows", [])}
                    == expected_ids,
                    "detail": {"count": workflows.get("total_count")},
                }
            )
            page = tool_result(
                await session.call_tool(
                    "mathformer_list_workflows", {"category": "loop", "limit": 5}
                )
            )
            checks.append(
                {
                    "id": "workflows.filtered_pagination",
                    "ok": page.get("total_count") == catalog["counts"]["loop"]
                    and page.get("next_offset") == 5
                    and len(page.get("workflows", [])) == 5,
                    "detail": {
                        "total_count": page.get("total_count"),
                        "next_offset": page.get("next_offset"),
                    },
                }
            )
            for category in catalog["counts"]:
                row = next(
                    row for row in catalog["workflows"] if row["category"] == category
                )
                shown = tool_result(
                    await session.call_tool(
                        "mathformer_show_workflow", {"workflow_id": row["aliases"][0]}
                    )
                )
                checks.append(
                    {
                        "id": f"workflows.show_{category}_by_alias",
                        "ok": shown.get("ok") is True
                        and shown.get("workflow", {}).get("id") == row["id"]
                        and f'id: {row["id"]}' in shown.get("workflow_yaml", ""),
                        "detail": row["id"],
                    }
                )
            spec = next(
                row for row in catalog["workflows"] if row["category"] == "loop"
            )
            blocked_spec = tool_result(
                await session.call_tool(
                    "mathformer_run_workflow", {"workflow_id": spec["id"]}
                )
            )
            checks.append(
                {
                    "id": "workflows.declarative_execution_blocked",
                    "ok": blocked_spec.get("ok") is False
                    and blocked_spec.get("status") == "specification_only",
                    "detail": blocked_spec.get("status"),
                }
            )
            mutating_workflow = next(
                row
                for row in catalog["workflows"]
                if row["aliases"] == ["setup:atp-kb"]
            )
            blocked_mutation = tool_result(
                await session.call_tool(
                    "mathformer_run_workflow", {"workflow_id": mutating_workflow["id"]}
                )
            )
            checks.append(
                {
                    "id": "workflows.native_mutation_preflight_preserved",
                    "ok": blocked_mutation.get("ok") is False
                    and bool(blocked_mutation.get("preflight_errors")),
                    "detail": blocked_mutation.get("preflight_errors"),
                }
            )
            audit_route = next(
                route
                for route in hub_module.build_intent_routes()
                if route.action_ids == ("control:normalized-workflows",)
            )
            route_row = next(
                row
                for row in catalog["workflows"]
                if row["aliases"] == [audit_route.route_id]
            )
            dry_route = tool_result(
                await session.call_tool(
                    "mathformer_run_workflow",
                    {"workflow_id": route_row["id"], "dry_run": True},
                )
            )
            checks.append(
                {
                    "id": "workflows.native_route_dry_run",
                    "ok": dry_route.get("ok") is True
                    and all(
                        child.get("status") == "dry_run"
                        for child in dry_route.get("children", [])
                    ),
                    "detail": dry_route.get("status"),
                }
            )
            workflows_read = await session.read_resource(
                AnyUrl("mathformer://workflows")
            )
            workflow_catalog = json.loads(workflows_read.contents[0].text)
            checks.append(
                {
                    "id": "resources.workflows_match_catalog",
                    "ok": workflow_catalog == catalog,
                    "detail": len(workflow_catalog.get("workflows", [])),
                }
            )
            descriptor_read = await session.read_resource(
                AnyUrl(f'mathformer://workflows/{spec["id"]}')
            )
            checks.append(
                {
                    "id": "resources.workflow_template_resolves",
                    "ok": json.loads(descriptor_read.contents[0].text)
                    .get("workflow", {})
                    .get("id")
                    == spec["id"],
                    "detail": spec["id"],
                }
            )
            workflow_schema = await session.read_resource(
                AnyUrl("mathformer://workflow-schema")
            )
            checks.append(
                {
                    "id": "resources.workflow_schema_available",
                    "ok": json.loads(workflow_schema.contents[0].text).get("$id")
                    == "urn:workflow-skill:schema:v1",
                    "detail": "workflow-skill/v1",
                }
            )

            resource_read = await session.read_resource(AnyUrl("mathformer://actions"))

            assert isinstance(resource_read.contents[0], TextResourceContents)
            resource_payload = json.loads(resource_read.contents[0].text)
            cli_list_payload = run_cli_json("list", "--json")
            checks.append(
                {
                    "id": "resources.actions_matches_cli_list",
                    "ok": resource_payload == cli_list_payload,
                    "detail": {
                        "resource_action_count": len(
                            resource_payload.get("actions", [])
                        ),
                        "cli_action_count": len(cli_list_payload.get("actions", [])),
                    },
                }
            )

            schema_read = await session.read_resource(
                AnyUrl("mathformer://reasoning-log-schema")
            )
            assert isinstance(schema_read.contents[0], TextResourceContents)
            checks.append(
                {
                    "id": "resources.reasoning_schema_has_consumer_profile",
                    "ok": "Consumer-Grade Profile" in schema_read.contents[0].text,
                    "detail": {
                        "bytes": len(schema_read.contents[0].text.encode("utf-8"))
                    },
                }
            )

            policy_read = await session.read_resource(
                AnyUrl("mathformer://reasoning-log-quality-policy")
            )
            assert isinstance(policy_read.contents[0], TextResourceContents)
            policy_payload = json.loads(policy_read.contents[0].text)
            checks.append(
                {
                    "id": "resources.reasoning_quality_policy_machine_readable",
                    "ok": policy_payload.get("ok") is True
                    and "self_contained" in policy_payload.get("dimensions", []),
                    "detail": policy_payload,
                }
            )

            fixed_request = "audit workflow control coverage"
            ask_result = tool_result(
                await session.call_tool("mathformer_ask", {"request": fixed_request})
            )
            cli_ask_payload = run_cli_json("ask", fixed_request, "--json")
            mcp_top_route = (ask_result.get("matches") or [{}])[0].get("route_id")
            cli_top_route = (cli_ask_payload.get("matches") or [{}])[0].get("route_id")
            checks.append(
                {
                    "id": "ask.matches_cli_route",
                    "ok": bool(mcp_top_route) and mcp_top_route == cli_top_route,
                    "detail": {
                        "mcp_route_id": mcp_top_route,
                        "cli_route_id": cli_top_route,
                    },
                }
            )

            mutating_result = tool_result(
                await session.call_tool(
                    "mathformer_run_action", {"action_id": "setup:atp-kb"}
                )
            )
            checks.append(
                {
                    "id": "run_action.mutating_blocked_without_allow_mutating",
                    "ok": mutating_result.get("ok") is False
                    and bool(mutating_result.get("preflight_errors")),
                    "detail": mutating_result.get("preflight_errors"),
                }
            )

            read_only_result = tool_result(
                await session.call_tool(
                    "mathformer_run_action", {"action_id": "hub:audit"}
                )
            )
            cli_run_payload = run_cli_json("run", "hub:audit", "--json")
            mcp_audit_ok = (
                json.loads(read_only_result.get("stdout", "{}")).get("ok")
                if read_only_result.get("stdout")
                else None
            )
            cli_audit_ok = (
                json.loads(cli_run_payload.get("stdout", "{}")).get("ok")
                if cli_run_payload.get("stdout")
                else None
            )
            checks.append(
                {
                    "id": "run_action.read_only_executes_and_matches_cli",
                    "ok": read_only_result.get("ok") is True
                    and cli_run_payload.get("ok") is True
                    and mcp_audit_ok is True
                    and mcp_audit_ok == cli_audit_ok,
                    "detail": {
                        "mcp_ok": read_only_result.get("ok"),
                        "cli_ok": cli_run_payload.get("ok"),
                    },
                }
            )

            unknown_result = tool_result(
                await session.call_tool(
                    "mathformer_show_action", {"action_id": "does-not-exist"}
                )
            )
            checks.append(
                {
                    "id": "show_action.unknown_id_reports_ok_false",
                    "ok": unknown_result.get("ok") is False
                    and "error" in unknown_result,
                    "detail": unknown_result,
                }
            )

            # setup:atp-kb has timeout_seconds=None in scripts/mathformer.py's
            # registry. mcp_server.py caps unbounded timeouts only on its
            # internal execution registry (see _EXEC_REGISTRY), not on the
            # registry shown to callers, so discoverability must still report
            # the true None here, matching the CLI exactly.
            show_result = tool_result(
                await session.call_tool(
                    "mathformer_show_action", {"action_id": "setup:atp-kb"}
                )
            )
            cli_show_payload = run_cli_json("show", "setup:atp-kb", "--json")
            checks.append(
                {
                    "id": "show_action.reports_true_timeout_not_exec_cap",
                    "ok": show_result.get("action", {}).get("timeout_seconds") is None
                    and show_result == cli_show_payload,
                    "detail": show_result,
                }
            )

    # Exercise configured service guards with execution mocked, so even a
    # regression cannot start an installer or mutate the real checkout.
    import mcp_server as server

    with (
        patch.object(server, "_READONLY", True),
        patch.object(server, "_log_call"),
        patch.object(server.hub, "run_action", return_value={"ok": False}) as execute,
    ):
        server.mathformer_run_workflow(mutating_workflow["id"], allow_mutating=True)
        checks.append(
            {
                "id": "workflows.readonly_context_preserved",
                "ok": execute.call_args.args[2].allow_mutating is False,
                "detail": "execution mocked; readonly context denies mutation",
            }
        )
    with (
        patch.object(server, "_ALLOWED_WRITE_ROOTS", []),
        patch.object(server, "_log_call"),
        patch.object(server.hub, "run_action") as execute,
    ):
        result = server.mathformer_run_workflow(
            mutating_workflow["id"], allow_mutating=True
        )
        checks.append(
            {
                "id": "workflows.service_write_roots_preserved",
                "ok": result.get("status") == "blocked_by_service_write_roots"
                and not execute.called,
                "detail": result.get("preflight_errors"),
            }
        )
    setup_route = next(
        route
        for route in hub_module.build_intent_routes()
        if "setup:atp-kb" in route.action_ids
    )
    setup_route_row = next(
        row
        for row in catalog["workflows"]
        if row["category"] == "route" and row["aliases"] == [setup_route.route_id]
    )
    with (
        patch.object(server, "_ALLOWED_WRITE_ROOTS", []),
        patch.object(server, "_log_call") as log,
        patch.object(server.hub, "run_intent_match") as execute,
    ):
        result = server.mathformer_run_workflow(
            setup_route_row["id"], allow_mutating=True
        )
        checks.append(
            {
                "id": "workflows.route_service_write_roots_and_audit_preserved",
                "ok": result.get("status") == "blocked_by_service_write_roots"
                and not execute.called
                and log.called,
                "detail": result.get("preflight_errors"),
            }
        )

    ok = all(item["ok"] for item in checks)
    return ok, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        ok, checks = asyncio.run(run_checks())
    except ModuleNotFoundError as exc:
        if exc.name == "mcp":
            ok = True
            checks = [
                {
                    "id": "self_test.optional_mcp_dependency_missing",
                    "ok": True,
                    "skipped": True,
                    "detail": "Install the mcp extra to run the live stdio client/server handshake.",
                }
            ]
        else:
            ok = False
            checks = [
                {
                    "id": "self_test.unhandled_exception",
                    "ok": False,
                    "detail": repr(exc),
                }
            ]
    except Exception as exc:  # noqa: BLE001 - surfaced as a failing check, not a crash
        ok = False
        checks = [
            {"id": "self_test.unhandled_exception", "ok": False, "detail": repr(exc)}
        ]

    payload = {"schema_version": 1, "ok": ok, "checks": checks}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in checks:
            print(f"{'PASS' if item['ok'] else 'FAIL'} {item['id']}")
        print(f"{'PASS' if ok else 'FAIL'} mcp_server_self_test")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

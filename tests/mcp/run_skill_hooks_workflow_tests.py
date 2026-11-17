#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Fixture-only native skill-hook validation through MCP and real Lunar/PRISM.

This deterministic workflow has no provider/model or external compiler calls.
PRISM parsing, checking, compilation and runtime are never substituted.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts")]
import asyncio
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import unittest
import yaml
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_control_workflow_contract_workflow/workflow.yaml"
SOURCE = "skills/control/workflow-contract-validator/scripts/validate_skill_hooks.py"
PREFIX = "mathformer_skill_hooks_"
BASE = """runtime_contract:
  orchestrator_skill: fixture-owner
  reasoning_log_required_payload_fields:
    - skill
  shared_runtime_scripts:
    - runtime.py
hooks:
  - id: fixture.first
    phase: before
    trigger: explicit
    owner_skill: fixture-owner
    reasoning_log_steps:
      - start
loop_contracts:
  - id: ignored.loop
    nonsense: ignored
    owner_skill: missing-ignored
direct_request_routing:
  fixture: fixture-owner
"""


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


class SkillHooksTests(unittest.TestCase):
    def test_registered_source_workflow(self):
        with tempfile.TemporaryDirectory(prefix="skill-hooks-") as directory:
            asyncio.run(self.scenario(Path(directory)))

    async def scenario(self, root):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_control_workflow_contract_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(document["aliases"], ["control:workflow-contract"])
        self.assertIn(SOURCE, [s["path"] for s in document["provenance"]["sources"]])
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            document,
            json.loads(
                (
                    ROOT
                    / "skills/control/workflow-contract-validator/references/skill-hooks.workflow.json"
                ).read_text()
            ),
        )
        # The actual service registration is used; importing it does not run its
        # config/credential-loading main or launch any production workflow.
        server = f'import sys;sys.path.insert(0,{str(ROOT/"scripts")!r});from mcp_server import mcp;mcp.run(transport="stdio")'
        manager = SessionManager()
        failure = None
        async with manager.open(
            "skill-hooks",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(root)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    selected = workflow_documents([DESCRIPTOR], assets)[0]
                    return (
                        compile_workflow("mcp:skill-hooks", selected, inventory),
                        assets,
                    )

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(
                    compile(
                        document, [t for t in tools if t["name"] != PREFIX + "parse"]
                    )[0]["runnable"]
                )

                async def authorize():
                    pass

                async def run(doc=document):
                    c, a = (compiled, assets) if doc is document else compile(doc)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c, a, {"repo_root": str(root)}, remote, authorize
                    )

                async def call(name, **kwargs):
                    return await remote.call(PREFIX + name, kwargs)

                skills = root / "skills"
                owner = skills / "control/fixture-owner/SKILL.md"
                owner.parent.mkdir(parents=True)
                owner.write_text("fixture owner")
                (root / "runtime.py").write_text(
                    "# fixture runtime exists; never executed\n"
                )
                hooks = skills / "SKILL_HOOKS.yaml"
                prompt = skills / "ALL_AGENT_SKILL_PROMPTS.md"
                prompt.write_text(
                    "`skills/control/fixture-owner/SKILL.md`\n`skills/`\n`skills/*/agents/openai.yaml`\n"
                )
                oracle = ROOT / "tests/mcp/fixtures/skill_hooks_original.py.txt"

                def oracle_run(source=oracle, text=False):
                    return subprocess.run(
                        [
                            sys.executable,
                            str(source),
                            "--strict",
                            *([] if text else ["--json"]),
                        ],
                        cwd=root,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                async def compare(expected_calls, expected_code):
                    result = await run()
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(len(result["calls"]), expected_calls)
                    self.assertTrue(
                        all(c["status"] == "accepted" for c in result["calls"])
                    )
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    original = oracle_run()
                    current = oracle_run(ROOT / SOURCE)
                    self.assertEqual(
                        (current.returncode, current.stdout, current.stderr),
                        (original.returncode, original.stdout, original.stderr),
                    )
                    outputs = result["outputs"]
                    self.assertEqual(outputs["exit_code"], expected_code)
                    self.assertEqual(outputs["exit_code"], original.returncode)
                    self.assertEqual(outputs["stdout"], original.stdout)
                    self.assertEqual(outputs["report"], json.loads(original.stdout))
                    return outputs["report"]

                # Missing branch stops before parsing and omits normal report fields.
                report = await compare(3, 3)
                self.assertNotIn("strict", report)
                self.assertEqual(
                    report["summary"], {"finding_count": 1, "blocking_findings": 1}
                )
                self.assertEqual(report["findings"][0]["code"], "hooks_file_missing")
                hooks.write_text(BASE)
                report = await compare(5, 0)
                self.assertEqual(report["findings"], [])
                self.assertEqual(
                    (
                        report["hook_count"],
                        report["direct_route_count"],
                        report["shared_runtime_script_count"],
                    ),
                    (1, 1, 1),
                )
                resolved = await call("resolve", repo_root=str(root))
                paths = resolved["paths"]
                parsed = await call("parse", paths=paths)
                self.assertEqual(len(parsed["manifest"]["hooks"]), 1)
                self.assertEqual(
                    parsed["manifest"]["runtime_contract"]["shared_runtime_scripts"],
                    ["runtime.py"],
                )
                self.assertNotIn("loop_contracts", parsed["manifest"])
                # Medium and low severities do not block; Unicode is retained.
                hooks.write_text(
                    BASE.replace("fixture.first", "Nonstandard雪").replace(
                        "    reasoning_log_steps:\n      - start",
                        "    reasoning_log_steps: []",
                    )
                )
                prompt.unlink()
                report = await compare(5, 0)
                self.assertEqual(
                    [f["code"] for f in report["findings"]],
                    [
                        "nonstandard_hook_id",
                        "empty_reasoning_log_steps",
                        "prompt_index_missing",
                    ],
                )
                self.assertEqual(report["summary"]["severity_counts"]["high"], 0)
                # Direct-route insertion order survives the canonicalizing transport.
                hooks.write_text(BASE + "  zzz: missing-z\n  aaa: missing-a\n")
                report = await compare(5, 3)
                self.assertIn("missing-z", report["findings"][0]["message"])
                self.assertIn("missing-a", report["findings"][1]["message"])
                # Empty collections still run native runtime requirements and prompt checks.
                hooks.write_text("")
                report = await compare(5, 3)
                self.assertEqual(report["hook_count"], 0)
                self.assertEqual(
                    [f["code"] for f in report["findings"]],
                    [
                        "missing_orchestrator_skill",
                        "missing_required_payload_skill",
                        "prompt_index_missing",
                    ],
                )
                # Exhaust the finite scans, accumulating well beyond text cap 60.
                hooks.write_text(
                    "runtime_contract:\nhooks:\n"
                    + "".join(f"  - id: fixture.h{i}\n" for i in range(25))
                    + "direct_request_routing:\n  invalid: missing-owner\n"
                )
                prompt.write_text("`skills/missing/file`\n")
                report = await compare(5, 3)
                self.assertGreater(len(report["findings"]), 100)
                self.assertEqual(
                    report["findings"][-1]["code"], "missing_prompt_index_reference"
                )
                self.assertEqual(
                    report["summary"]["finding_count"], len(report["findings"])
                )
                self.assertIn("more findings", oracle_run(text=True).stdout)
                # The validator's continue skips remaining checks only for invalid IDs.
                manifest = deepcopy(parsed["manifest"])
                manifest["hooks"] = [
                    {},
                    {"id": None},
                    {"id": 7},
                    {"id": ""},
                    deepcopy(parsed["manifest"]["hooks"][0]),
                    deepcopy(parsed["manifest"]["hooks"][0]),
                ]
                findings = (
                    await call(
                        "validate",
                        paths=paths,
                        manifest=manifest,
                        serialized_manifest=json.dumps(manifest),
                    )
                )["findings"]
                self.assertEqual(
                    [f["code"] for f in findings[:5]],
                    ["missing_hook_id"] * 4 + ["duplicate_hook_id"],
                )
                # Recheck after parsing catches a disappearing manifest without
                # suppressing later prompt-index findings.
                hooks.unlink()
                findings = (
                    await call(
                        "validate",
                        paths=paths,
                        manifest=parsed["manifest"],
                        serialized_manifest=parsed["serialized_manifest"],
                    )
                )["findings"]
                self.assertEqual(
                    [f["code"] for f in findings],
                    ["hooks_file_missing", "missing_prompt_index_reference"],
                )
                hooks.write_text(BASE)
                # A source exception is a failed operation; no retry or emit.
                hooks.unlink()
                hooks.mkdir()
                failed = await run()
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(
                    [c["status"] for c in failed["calls"]], ["accepted", "rejected"]
                )
                hooks.rmdir()
                hooks.write_text(BASE)
                # Enforced call-budget exhaustion stops before validation dispatch.
                limited = deepcopy(document)
                limited["policy"]["limits"]["max_operation_calls"] = 2
                failed = await run(limited)
                self.assertEqual(failed["status"], "failed", failed)
                self.assertIsNone(failed["outputs"])
                self.assertEqual(
                    [c["status"] for c in failed["calls"]],
                    ["accepted", "accepted", "rejected"],
                )
                self.assertIn("budget", failed["calls"][-1]["error"])
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure is not None:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)

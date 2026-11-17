#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native fixture subprocesses, registered MCP tools and real Lunar/PRISM.

No provider/model or external compiler exists in this workflow. Nothing at those
boundaries needs substitution. Fixture mounts contain byte-identical native
scripts and deterministic local inputs; production artifacts are never used.
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
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import asdict
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
import mathformer as hub
from paper_claim_audit_rfde_tools import ACTION
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_claim_audit_rfde_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
BUILD = "paper_skills/framework-repository-cartographer/scripts/build_paper_evidence_packet.py"
AUDIT = "paper_skills/paper-claim-evidence-auditor/scripts/audit_paper_claims.py"
PAPER = "paper/REFERENCE_FREE_REFINEMENT_DYNAMICS.tex"
PACKET = "artifacts/paper_skills/new_functionality_evidence_packet.json"
REPORT = "artifacts/paper_skills/rfde_paper_claim_audit.json"
PREFIX = "mathformer_paper_claim_audit_rfde_"
SERVER = """import sys
sys.path.insert(0, 'scripts')
import mcp_server as server
from pathlib import Path
server.hub.REPO_ROOT = Path(sys.argv[1])
server.CALL_LOG_PATH = server.hub.REPO_ROOT / 'artifacts/mcp/calls.jsonl'
server._READONLY = sys.argv[2] == 'readonly'
if sys.argv[2] == 'restricted':
    server._ALLOWED_WRITE_ROOTS = [server.hub.REPO_ROOT / 'elsewhere']
server.mcp.run(transport='stdio')
"""


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    paths = dict.fromkeys(
        [SCHEMA, *(r["path"] for r in document["provenance"]["sources"])]
    )
    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(p, (ROOT / p).read_text()) for p in paths
    ]


class PaperClaimAuditTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="paper-audit-fixture-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.document = yaml.safe_load(
            Path(
                os.environ.get("WORKFLOW_CONTRACT_PATH", ROOT / DESCRIPTOR)
            ).read_text()
        )
        self.mount()

    def mount(self):
        # Byte-identical native programs run only against this isolated fixture.
        for name in (BUILD, AUDIT):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)
        (self.root / PAPER).parent.mkdir(parents=True, exist_ok=True)
        (self.root / PAPER).write_text(
            "Dashboard inspection and workflow hub reasoning log.\n"
        )

    def clean(self):
        shutil.rmtree(self.root / "artifacts", ignore_errors=True)

    def native(self, context, extra_args=(), seen=()):
        code = """import sys,json
sys.path.insert(0,'scripts')
import mathformer as hub
from pathlib import Path
hub.REPO_ROOT=Path(sys.argv[1])
request=json.loads(sys.argv[2])
print(json.dumps(hub.run_action('paper:claim-audit-rfde',hub.build_registry(),hub.RunContext(**request['context']),extra_args=request['extra_args'],seen=set(request['seen']))))
"""
        process = subprocess.run(
            [
                str(ROOT / ".venv/bin/python"),
                "-c",
                code,
                str(self.root),
                json.dumps(
                    dict(context=context, extra_args=list(extra_args), seen=list(seen))
                ),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(process.stdout)

    def test_provenance_and_authored_generator(self):
        self.assertEqual(self.document["lifecycle"], "active")
        for row in self.document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        path = (
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py"
        )
        spec = importlib.util.spec_from_file_location("paper_audit_generator", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            [d for d in module.inventory() if d["id"] == self.document["id"]],
            [self.document],
        )

    def test_native_write_and_launch_failures(self):
        actions = hub.build_registry()
        self.assertEqual(
            hub.admit_action("missing", actions, ["x"], {"missing"})["status"],
            "unknown_action",
        )
        with patch.object(hub, "REPO_ROOT", self.root):
            item = actions[ACTION]
            boundary = hub.prepare_leaf_boundary(item, hub.RunContext(), ())
            (self.root / "undeclared.txt").write_text("fixture")
            result = hub.finish_leaf_boundary(
                item, boundary, dict(boundary["payload"], ok=True)
            )
            self.assertEqual(result["status"], "undeclared_writes")
            self.assertFalse(result["ok"])
            with self.assertRaises(FileNotFoundError):
                hub.launch_leaf_boundary(
                    item, {"argv": [str(self.root / "missing-executable")]}
                )

    def test_native_audit_categories_figures_and_global_path_rule(self):
        from contextlib import redirect_stdout
        import io

        spec = importlib.util.spec_from_file_location(
            "fixture_paper_audit", ROOT / AUDIT
        )
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        audit.REPO_ROOT = self.root
        text = "Observability dashboard controlled action reasoning log reference-free monitor\n"
        # Exercise all three native figure search locations and one missing target.
        for directory, name in [
            ("", "root.pdf"),
            ("paper", "paper.pdf"),
            ("paper/figures", "figure.pdf"),
        ]:
            path = self.root / directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
            text += "\\includegraphics{" + name + "}\n"
        text += "\\includegraphics{missing.pdf}\n"
        (self.root / PAPER).write_text(text)
        packet = self.root / PACKET
        packet.parent.mkdir(parents=True, exist_ok=True)
        packet.write_text(
            json.dumps(
                {
                    "features": [{"feature_id": "one"}, {"feature_id": "two"}],
                    "missing_paths": ["absent"],
                }
            )
        )

        def invoke():
            with (
                patch.object(
                    sys,
                    "argv",
                    [
                        "audit",
                        "--paper",
                        PAPER,
                        "--evidence-packet",
                        PACKET,
                        "--output",
                        REPORT,
                        "--json",
                    ],
                ),
                redirect_stdout(io.StringIO()) as output,
            ):
                code = audit.main()
            report = json.loads(output.getvalue())
            self.assertEqual(report, json.loads((self.root / REPORT).read_text()))
            return code, report

        code, report = invoke()
        self.assertEqual(code, 0)  # Medium and low findings do not fail the audit.
        self.assertEqual(report["feature_count"], 2)
        self.assertEqual(report["finding_count"], 8)
        self.assertEqual(
            sum(f["id"] == "claim_without_artifact_path" for f in report["findings"]), 5
        )
        self.assertEqual(report["findings"][-1]["id"], "unknown_packet_schema")
        self.assertEqual(
            [
                f["path"]
                for f in report["findings"]
                if f["id"] == "missing_figure_source"
            ],
            ["missing.pdf"],
        )
        self.assertTrue(
            all(count > 0 for count in report["claim_surface_counts"].values())
        )
        (self.root / PAPER).write_text(text + "`one/global/path`")
        code, report = invoke()
        self.assertEqual(code, 0)
        self.assertEqual(report["finding_count"], 3)
        packet.write_text("{")
        with self.assertRaises(json.JSONDecodeError):
            invoke()
        packet.unlink()
        with self.assertRaises(FileNotFoundError):
            invoke()

    def test_frozen_original_entrypoint_and_optional_cli_branches(self):
        from contextlib import redirect_stdout
        import io

        modules = []
        for path in (
            ROOT / "tests/mcp/fixtures/paper_claim_audit_original.py",
            ROOT / AUDIT,
        ):
            spec = importlib.util.spec_from_file_location("audit_comparison", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            module.REPO_ROOT = self.root
            modules.append(module)
        packet = self.root / PACKET
        packet.parent.mkdir(parents=True)
        packet.write_text(
            json.dumps({"features": [{}, {}], "missing_paths": ["absent"]})
        )
        for text in (
            "No audit claims.",
            "Dashboard inspection.",
            "Dashboard proves safety.\nRFDE guarantees correctness.\ncorrect by construction\n"
            * 250,
        ):
            (self.root / PAPER).write_text(text)
            for flags in (
                [],
                ["--json"],
                ["--evidence-packet", PACKET, "--output", REPORT, "--json"],
            ):
                values = []
                for module in modules:
                    with (
                        patch.object(sys, "argv", ["audit", "--paper", PAPER, *flags]),
                        redirect_stdout(io.StringIO()) as output,
                    ):
                        code = module.main()
                    values.append(
                        (
                            code,
                            output.getvalue(),
                            (
                                (self.root / REPORT).read_text()
                                if "--output" in flags
                                else None
                            ),
                        )
                    )
                self.assertEqual(values[0], values[1])
                if "--json" in flags and text.count("Dashboard proves"):
                    self.assertEqual(
                        sum(
                            f["severity"] == "high"
                            for f in json.loads(values[1][1])["findings"]
                        ),
                        750,
                    )
        self.assertEqual(
            modules[1].packet_features(modules[1].load_packet(packet)), [{}, {}]
        )

    def test_registered_tools_and_lunar(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        manager = SessionManager()

        @asynccontextmanager
        async def opened(mode):
            config = StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=["-c", SERVER, str(self.root), mode],
                cwd=str(ROOT),
            )
            error = None
            async with manager.open("paper-audit-" + mode, config, {}) as remote:
                try:
                    yield remote
                except Exception as caught:
                    error = caught
            if error:
                raise error

        async with opened("normal") as remote:
            tools = [
                t.model_dump(by_alias=True, exclude_none=True)
                for t in await remote.tools()
            ]

            def compile(doc, inventory=None):
                assets = snapshot(doc)
                w = compile_workflow(
                    "mcp:paper-audit",
                    workflow_documents([DESCRIPTOR], assets)[0],
                    tools if inventory is None else inventory,
                )
                return w, assets

            workflow, assets = compile(self.document)
            self.assertTrue(workflow["runnable"], workflow["diagnostics"])
            self.assertTrue(workflow["runtime_source"])
            self.assertEqual(
                set(workflow["bindings"]), set(self.document["operations"])
            )
            self.assertFalse(compile(self.document, [])[0]["runnable"])
            malformed = deepcopy(self.document)
            malformed["operations"]["scan_main"]["execution"]["binding"][
                "target"
            ] = "missing_audit_tool"
            malformed["operations"]["scan_main"]["execution"]["binding"][
                "operation"
            ] = "missing_audit_tool"
            self.assertFalse(compile(malformed)[0]["runnable"])

            async def allow():
                pass

            async def run(context=None, extra_args=(), seen=(), document=None):
                w, a = compile(document) if document else (workflow, assets)
                self.assertTrue(w["runnable"], w["diagnostics"])
                return await execute(
                    w,
                    a,
                    dict(
                        context=context or asdict(hub.RunContext()),
                        extra_args=list(extra_args),
                        ancestry=list(seen),
                    ),
                    remote,
                    allow,
                )

            for dry_run in (True, False):
                for keep_going in (True, False):
                    self.clean()
                    context = asdict(
                        hub.RunContext(dry_run=dry_run, keep_going=keep_going)
                    )
                    expected = self.native(context)
                    self.clean()
                    result = await run(context)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(
                        [c["tool"] for c in result["calls"]],
                        [
                            PREFIX + n
                            for n in (
                                (
                                    "admit",
                                    "initialize",
                                    "visit",
                                    "advance",
                                    "guard",
                                    "prepare",
                                    "unlaunched",
                                    "aggregate",
                                )
                                if dry_run
                                else (
                                    "admit",
                                    "initialize",
                                    "visit",
                                    "advance",
                                    "guard",
                                    "prepare",
                                    "scan_main",
                                    "emit_main",
                                    "finish_leaf",
                                    "aggregate",
                                )
                            )
                        ],
                    )
                    self.assertTrue(expected["ok"])
                    self.assertEqual(len(expected["children"]), 1)
                    self.assertIsNone(expected["leaf"]["action"]["timeout_seconds"])
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(result["replay_artifacts"])
                    if dry_run:
                        self.assertFalse((self.root / REPORT).exists())
                    else:
                        report = json.loads((self.root / REPORT).read_text())
                        self.assertEqual(report["feature_count"], 4)
                        self.assertTrue(report["ok"])
                        self.assertEqual(
                            report["finding_count"], len(report["findings"])
                        )
                        self.assertIn(
                            "missing_packet_path", {f["id"] for f in report["findings"]}
                        )
                        self.assertEqual(json.loads(expected["leaf"]["stdout"]), report)
            for args, seen, status in [
                (["extra"], [], "extra_args_for_sequence"),
                (["extra"], [ACTION], "dependency_cycle"),
            ]:
                self.clean()
                result = await run(extra_args=args, seen=seen)
                self.assertEqual(
                    result["outputs"],
                    {"result": self.native(asdict(hub.RunContext()), args, seen)},
                )
                self.assertEqual(result["outputs"]["result"]["status"], status)
                self.assertEqual(len(result["calls"]), 2)
                self.assertFalse((self.root / REPORT).exists())
            # Fixed patterns accumulate all finite matches; high severity alone fails.
            (self.root / PAPER).write_text(
                "Dashboard proves safety.\nRFDE guarantees correctness.\ncorrect by construction\n\\includegraphics{missing.pdf}\n"
            )
            result = await run()
            envelope = result["outputs"]["result"]
            self.assertEqual(envelope["status"], "failed_with_dependencies")
            self.assertEqual(envelope["leaf"]["returncode"], 1)
            report = json.loads((self.root / REPORT).read_text())
            self.assertEqual([f["line"] for f in report["findings"][:3]], [1, 2, 3])
            self.assertEqual(
                [f["severity"] for f in report["findings"][:3]], ["high"] * 3
            )
            self.assertIn(
                "missing_figure_source", {f["id"] for f in report["findings"]}
            )
            # Failure skips the leaf, or keeps going without recovering aggregate ok.
            self.mount()
            self.clean()
            self.native(asdict(hub.RunContext()))
            (self.root / BUILD).unlink()
            for keep_going in (False, True):
                context = asdict(hub.RunContext(keep_going=keep_going))
                expected = self.native(context)
                result = await run(context)
                actual = result["outputs"]["result"]
                self.assertEqual(actual, expected)
                self.assertFalse(actual["ok"])
                self.assertEqual(len(actual["children"]), 1)
                self.assertIn(
                    "missing required path",
                    str(actual["children"][0]["preflight_errors"]),
                )
                if keep_going:
                    self.assertTrue(actual["leaf"]["ok"])
                    self.assertEqual(actual["status"], "failed_with_dependencies")
                else:
                    self.assertNotIn("leaf", actual)
                    self.assertEqual(actual["status"], "sequence_failed")
            # Child read/parse errors retain native stderr and exit status.
            (self.root / PACKET).write_text("invalid json")
            result = await run(asdict(hub.RunContext(keep_going=True)))
            leaf = result["outputs"]["result"]["leaf"]
            self.assertNotEqual(leaf["returncode"], 0)
            self.assertIn("JSONDecodeError", leaf["stderr"])
            self.assertIn(
                PREFIX + "captured_failure", [c["tool"] for c in result["calls"]]
            )
            self.assertNotIn(PREFIX + "emit_main", [c["tool"] for c in result["calls"]])

            # Real preflight prevents scan launch even when keep-going is set.
            self.mount()
            self.clean()
            (self.root / PAPER).unlink()
            result = await run(asdict(hub.RunContext(keep_going=True)))
            self.assertFalse(result["outputs"]["result"]["leaf"]["ok"])
            self.assertIn(PREFIX + "unlaunched", [c["tool"] for c in result["calls"]])
            self.assertNotIn(PREFIX + "scan_main", [c["tool"] for c in result["calls"]])

            # The scan/emission boundary holds the native text, packet and all
            # findings on one process stack. Changing inputs cannot rescan them.
            self.mount()
            self.clean()
            await run(asdict(hub.RunContext()))
            (self.root / REPORT).unlink()
            (self.root / PAPER).write_text("RFDE guarantees correctness.\n" * 250)
            context = asdict(hub.RunContext())
            boundary = (await remote.call(PREFIX + "prepare", dict(context=context)))[
                "boundary"
            ]
            attempt = (
                await remote.call(PREFIX + "scan_main", dict(boundary=boundary))
            )["attempt"]
            self.assertTrue(attempt["ready"])
            self.assertFalse((self.root / REPORT).exists())
            with self.assertRaises(MCPConnectionError):
                await remote.call(PREFIX + "scan_main", dict(boundary=boundary))
            (self.root / PAPER).write_text("No audit claims now.")
            (self.root / PACKET).write_text("invalid json after scan")
            leaf = (await remote.call(PREFIX + "emit_main", dict(attempt=attempt)))[
                "result"
            ]
            report = json.loads(leaf["stdout"])
            self.assertEqual(leaf["returncode"], 1)
            self.assertEqual(report["feature_count"], 4)
            self.assertEqual(
                sum(f["severity"] == "high" for f in report["findings"]), 250
            )
            self.assertEqual(
                [f["line"] for f in report["findings"][:250]], list(range(1, 251))
            )
            self.assertEqual(report, json.loads((self.root / REPORT).read_text()))
            finished = (
                await remote.call(
                    PREFIX + "finish_leaf", dict(boundary=boundary, leaf=leaf)
                )
            )["result"]
            self.assertEqual(finished["status"], "undeclared_writes")
            self.assertIn(PAPER, finished["write_audit"]["unexpected_paths"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(PREFIX + "emit_main", dict(attempt=attempt))
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "scan_main",
                    dict(
                        boundary={
                            "execute": True,
                            "payload": {"argv": ["untrusted"]},
                            "continuation": "unknown",
                        }
                    ),
                )

            # Missing packet is a captured read failure; output-directory errors
            # occur after scan, so they flow through emit_main, without a report.
            self.mount()
            self.clean()
            for failure in ("missing_packet", "emit_directory"):
                if failure == "emit_directory":
                    packet = self.root / PACKET
                    packet.parent.mkdir(parents=True, exist_ok=True)
                    packet.write_text("{}")
                    (self.root / REPORT).mkdir()
                boundary = (
                    await remote.call(PREFIX + "prepare", dict(context=context))
                )["boundary"]
                attempt = (
                    await remote.call(PREFIX + "scan_main", dict(boundary=boundary))
                )["attempt"]
                self.assertEqual(attempt["ready"], failure == "emit_directory")
                operation = "emit_main" if attempt["ready"] else "captured_failure"
                leaf = (await remote.call(PREFIX + operation, dict(attempt=attempt)))[
                    "result"
                ]
                self.assertFalse(leaf["ok"])
                self.assertIn(
                    "IsADirectoryError" if attempt["ready"] else "FileNotFoundError",
                    leaf["stderr"],
                )
                self.assertEqual(leaf["stdout"], "")
                await remote.call(
                    PREFIX + "finish_leaf", dict(boundary=boundary, leaf=leaf)
                )
            self.mount()
            self.clean()
            capped = deepcopy(self.document)
            capped["policy"]["limits"]["max_operation_calls"] = 2
            result = await run(document=capped)
            self.assertEqual(result["status"], "failed")
            self.assertIsNone(result["outputs"])
            self.assertFalse((self.root / PACKET).exists())
            admission = (
                await remote.call(PREFIX + "admit", dict(extra_args=[], ancestry=[]))
            )["admission"]
            state = (
                await remote.call(PREFIX + "initialize", dict(admission=admission))
            )["state"]
            self.assertEqual(
                state,
                dict(index=0, children=[], dependencies_ok=True, ancestry=[ACTION]),
            )
            output = await remote.call(
                PREFIX + "advance",
                dict(
                    state=state,
                    child={"ok": False},
                    context=asdict(hub.RunContext(keep_going=True)),
                ),
            )
            self.assertTrue(output["done"])
            self.assertEqual(output["state"]["index"], 1)
            self.assertEqual(output["state"]["children"], [{"ok": False}])
            self.assertFalse(output["state"]["dependencies_ok"])
            with self.assertRaises(MCPConnectionError):
                await remote.call(
                    PREFIX + "visit",
                    dict(state=output["state"], context=asdict(hub.RunContext())),
                )
        for mode in ("readonly", "restricted"):
            async with opened(mode) as remote:
                state = dict(
                    index=0, children=[], dependencies_ok=True, ancestry=[ACTION]
                )
                for name, args in [("visit", dict(state=state)), ("prepare", {})]:
                    with self.assertRaises(MCPConnectionError):
                        await remote.call(
                            PREFIX + name, dict(args, context=asdict(hub.RunContext()))
                        )
                    output = await remote.call(
                        PREFIX + name,
                        dict(args, context=asdict(hub.RunContext(dry_run=True))),
                    )
                    value = next(iter(output.values()))
                    self.assertEqual(
                        value.get("status", value.get("payload", {}).get("status")),
                        "dry_run",
                    )
        self.assertFalse(manager.active)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PaperClaimAuditTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )

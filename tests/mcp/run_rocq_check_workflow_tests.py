#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Rocq / registered MCP / real Lunar PRISM deterministic execution."""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(ROOT),
    str(ROOT / "tests/mcp/fixtures"),
]
import asyncio
from copy import deepcopy
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
import yaml
from rocq_check_tools import source
from rocq_compiler_server import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_rocq_check_generated_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
CONTEXT = dict(
    dry_run=False,
    json_output=False,
    keep_going=False,
    allow_mutating=False,
    write_report=False,
)
GOOD = """(* SPDX-License-Identifier: MIT
File Documentation
Source theorem: fixture *)
Theorem fixture : True.
Proof.
 exact I.
Qed.
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
        asset(p, (ROOT / p).read_text())
        for p in sorted(
            {SCHEMA} | {s["path"] for s in document["provenance"]["sources"]}
        )
    ]


def stable(value):
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in ("generated_at_utc", "duration_ms", "path")
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


class RocqTests(unittest.TestCase):
    def test_native_original_parity_and_compiler_policy(self):
        original = type(sys)("_rocq_original")
        original.__file__ = str(
            ROOT / "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py"
        )
        exec(
            compile(
                (ROOT / "tests/mcp/fixtures/rocq_check_original.py.txt").read_text(),
                original.__file__,
                "exec",
            ),
            original.__dict__,
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / "b.v").write_text("Admitted.\n(* REJECT *)")
            (path / "a.v").write_text(GOOD)
            (path / "c.v").write_text(GOOD + "(* TIMEOUT *)")
            (path / "nested").mkdir()
            (path / "nested/ignored.v").write_text(GOOD)
            for mode in ("missing", "coqc", "rocq"):
                install(mode)
                for required in (False, True):
                    args = dict(
                        path=path,
                        compiler_bin=None,
                        timeout_sec=120,
                        require_compiler=required,
                    )
                    actual = source().run_validation(**args)
                    self.assertEqual(
                        stable(actual), stable(original.run_validation(**args))
                    )
                    self.assertEqual(actual["file_count"], 3)
                    self.assertEqual(
                        [v["ok"] for v in actual["validations"]], [True, False, True]
                    )
                    self.assertEqual(
                        actual["external_checks"][1]["skipped"], mode == "missing"
                    )
                    if mode != "missing":
                        self.assertFalse(actual["external_checks"][1]["ok"])
                        self.assertTrue(actual["external_checks"][2]["timeout"])
            single = path / "single.txt"
            single.write_text(GOOD)
            self.assertEqual(source().collect_files(single), [single])
            install("missing")
            self.assertTrue(
                source().run_validation(
                    path=single,
                    compiler_bin=None,
                    timeout_sec=120,
                    require_compiler=False,
                )["ok"]
            )
            self.assertFalse(
                source().run_validation(
                    path=single,
                    compiler_bin=None,
                    timeout_sec=120,
                    require_compiler=True,
                )["ok"]
            )
            empty = source().run_validation(
                path=path / "absent",
                compiler_bin=None,
                timeout_sec=120,
                require_compiler=False,
            )
            self.assertEqual(empty["structural_ok"], [])
            self.assertFalse(empty["ok"])
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = source().main(["--path", str(single), "--json"])
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(stream.getvalue())["ok"])

    def test_real_lunar_registered_tools(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        doc = yaml.safe_load(Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text())
        self.assertEqual(doc["lifecycle"], "active")
        for row in doc["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        for mode in ("missing", "coqc", "rocq"):
            manager = SessionManager()
            with tempfile.TemporaryDirectory() as tmp:
                mount = Path(tmp)
                runner = (
                    mount
                    / "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py"
                )
                runner.parent.mkdir(parents=True)
                runner.write_bytes(
                    (
                        ROOT
                        / "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py"
                    ).read_bytes()
                )
                (mount / "backends/rocq/MathformerRocq").mkdir(parents=True)
                failure = None
                async with manager.open(
                    "rocq",
                    StdioConfig(
                        command=sys.executable,
                        args=["-B", "tests/mcp/fixtures/rocq_compiler_server.py", mode],
                        cwd=str(ROOT),
                    ),
                    {},
                ) as remote:
                    try:
                        inventory = [
                            t.model_dump(by_alias=True, exclude_none=True)
                            for t in await remote.tools()
                        ]

                        def compiled(document):
                            assets = snapshot(document)
                            w = compile_workflow(
                                "mcp:rocq",
                                workflow_documents([DESCRIPTOR], assets)[0],
                                inventory,
                            )
                            self.assertTrue(w["runnable"], w["diagnostics"])
                            self.assertTrue(w["runtime_source"])
                            self.assertEqual(
                                set(w["bindings"]), set(document["operations"])
                            )
                            return w, assets

                        workflow, assets = compiled(doc)
                        rejected = compile_workflow(
                            "mcp:rocq", workflow_documents([DESCRIPTOR], assets)[0], []
                        )
                        self.assertFalse(rejected["runnable"])

                        async def authorize():
                            pass

                        async def run(document=doc, dry=False, extra=None):
                            w, a = compiled(document)
                            return await execute(
                                w,
                                a,
                                dict(
                                    context={**CONTEXT, "dry_run": dry},
                                    repository_root=str(mount),
                                    extra_args=extra or [],
                                ),
                                remote,
                                authorize,
                            )

                        for options in ({"dry": True}, {"extra": ["unexpected"]}):
                            result = await run(**options)
                            self.assertEqual(result["status"], "accepted", result)
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                ["prepare", "early_return"],
                            )
                            payload = result["outputs"]["result"]
                            if options.get("dry"):
                                self.assertEqual(payload["status"], "dry_run")
                            else:
                                self.assertTrue(payload["preflight_errors"])
                                self.assertFalse(payload["ok"])
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        report = json.loads(result["outputs"]["result"]["stdout"])
                        self.assertEqual(report["file_count"], 0)
                        self.assertEqual(report["structural_ok"], [])
                        self.assertFalse(report["ok"])
                        self.assertEqual(len(result["calls"]), 6)
                        target = mount / "MathformerRocq"
                        target.mkdir()
                        for name, text in [
                            ("a", GOOD),
                            ("b", "Admitted.\n(* REJECT *)"),
                            ("c", GOOD + "(* TIMEOUT *)"),
                            ("d", GOOD),
                        ]:
                            (target / (name + ".v")).write_text(text)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        report = json.loads(payload["stdout"])
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            ["prepare", "collect"]
                            + ["structural", "external"]
                            + ["aggregate", "complete"],
                        )
                        self.assertFalse(payload["ok"])
                        self.assertEqual(payload["returncode"], 1)
                        self.assertTrue(payload["write_audit"]["ok"])
                        install(mode)
                        expected = source().run_validation(
                            path=target,
                            compiler_bin=None,
                            timeout_sec=120,
                            require_compiler=False,
                        )
                        self.assertEqual(stable(report), stable(expected))
                        self.assertTrue(result["runtime"]["provenance"])
                        self.assertTrue(result["replay_artifacts"])
                        # No retry after a budget interruption; aggregate/complete cannot run.
                        bounded = deepcopy(doc)
                        bounded["policy"]["limits"]["max_operation_calls"] = 3
                        result = await run(bounded)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse(
                            any(c["operation"] == "complete" for c in result["calls"])
                        )
                        self.assertIn("budget", json.dumps(result).lower())
                        for file in target.glob("*.v"):
                            file.write_text(GOOD)
                        result = await run()
                        self.assertEqual(result["status"], "accepted", result)
                        payload = result["outputs"]["result"]
                        self.assertTrue(payload["ok"], payload)
                        self.assertEqual(payload["returncode"], 0)
                        report = json.loads(payload["stdout"])
                        self.assertEqual(report["file_count"], 4)
                        self.assertTrue(all(v["ok"] for v in report["validations"]))
                        self.assertEqual(
                            [v["skipped"] for v in report["external_checks"]],
                            [mode == "missing"] * 4,
                        )
                        # A structural exception aborts before the entire compiler pass.
                        (target / "c.v").write_bytes(b"\xff")
                        result = await run()
                        self.assertEqual(result["status"], "failed", result)
                        self.assertIsNone(result["outputs"])
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]],
                            ["prepare", "collect", "structural"],
                        )
                        (target / "c.v").write_text(GOOD)
                        if mode != "missing":
                            (target / "a.v").write_text(GOOD + "(* WRITE *)")
                            result = await run()
                            payload = result["outputs"]["result"]
                            self.assertEqual(payload["status"], "undeclared_writes")
                            self.assertFalse(payload["write_audit"]["ok"])
                            (target / "a.vo").unlink()
                            (target / "a.v").write_text(GOOD + "(* RAISE *)")
                            result = await run()
                            self.assertEqual(result["status"], "failed", result)
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]],
                                ["prepare", "collect"] + ["structural", "external"],
                            )
                    except Exception as error:
                        failure = error
                if failure:
                    raise failure
            self.assertFalse(manager.active)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RocqTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )

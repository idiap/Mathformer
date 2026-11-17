#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real native/MCP/PRISM fixtures. This renderer has no model/provider or
external compiler boundary: deterministic filesystem inputs exercise the real
PRISM parser, checker, compiler and runtime, without scientific workflow runs.
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
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import tempfile
import unittest
from unittest.mock import patch
import yaml
import render_workflow_graphs as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_docs_workflow_graph_render_workflow/workflow.yaml"


def snapshot(document):
    def asset(path, text):
        return dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class RenderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="graph-render-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.output = self.root / "artifacts/workflow_graphs"
        hooks = self.root / "skills/SKILL_HOOKS.yaml"
        hooks.parent.mkdir()
        hooks.write_text("""# parser ignores comments and blank lines
hooks:
  - id: one
    owner_skill: first
    trigger: hook fallback
    outputs:
      - evidence
loop_contracts:
  - id: sympy_physics_derivation_trace_loop
    required_hooks:
      - one
    required_owner_skills:
      - first
      - second
      - first
  - id: ignored
    description: no owners
  - id: other_loop
    description: custom description
    required_owner_skills:
      - first
      - missing
shared_runtime_scripts:
  - skills/runtime/run.py
 direct_request_routing:
  request: route
""".replace(" direct_request_routing:", "direct_request_routing:"))
        for name, text in [
            ("first", "name: first\ndescription: explicit description 雪\n"),
            ("second", ""),
            ("route", ""),
            ("runtime", ""),
            ("z-local", ""),
        ]:
            p = self.root / f"skills/test/{name}/SKILL.md"
            p.parent.mkdir(parents=True)
            p.write_text(text)
        spec = importlib.util.spec_from_loader(
            "_render_oracle",
            SourceFileLoader(
                "_render_oracle",
                str(ROOT / "tests/mcp/fixtures/workflow_graph_render_original.py.txt"),
            ),
        )
        self.oracle = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.oracle
        spec.loader.exec_module(self.oracle)
        self.oracle.REPO_ROOT = self.root
        self.oracle.DEFAULT_OUTPUT_DIR = self.output
        self.oracle.parse_hooks_manifest.__defaults__ = (hooks,)

    def cli(self, module, args):
        stream = io.StringIO()
        with redirect_stdout(stream), patch.object(sys, "argv", ["render", *args]):
            code = module.main()
        return code, stream.getvalue()

    def test_native_parity_and_catalogue_branches(self):
        catalogue = native.load_catalogue(self.root)
        expected = self.oracle.build_model()
        self.assertEqual(native.assemble_model(catalogue), expected)
        workflows = catalogue["workflows"]
        self.assertEqual(
            workflows[0]["stack_id"], "sympy-physics-derivation-trace-loop"
        )
        self.assertEqual(
            [s["skill"] for s in workflows[0]["steps"]], ["first", "second"]
        )
        self.assertEqual(
            sum(w["stack_id"] == workflows[0]["stack_id"] for w in workflows), 1
        )
        self.assertNotIn("ignored", [w["stack_id"] for w in workflows])
        self.assertEqual(
            workflows[0]["steps"][0]["description"], "explicit description 雪"
        )
        self.assertEqual(workflows[0]["steps"][1]["description"], "Run Second.")
        integration = workflows[-1]
        self.assertEqual(
            [s["skill"] for s in integration["steps"]], ["route", "runtime", "z-local"]
        )
        self.assertEqual(
            [s["trigger"] for s in integration["steps"]],
            ["direct route", "shared runtime", "project-local reporting"],
        )
        for args in [[], ["--json"], ["--output-dir", "nested/out", "--json"]]:
            expected_cli = self.cli(self.oracle, args)
            output = self.root / (
                "nested/out" if "--output-dir" in args else "artifacts/workflow_graphs"
            )
            expected_bytes = [
                (output / n).read_bytes()
                for n in ["workflow_graphs.json", "workflow_graphs.html"]
            ]
            with (
                patch.object(native, "REPO_ROOT", self.root),
                patch.object(native, "DEFAULT_OUTPUT_DIR", self.output),
            ):
                self.assertEqual(self.cli(native, args), expected_cli)
            self.assertEqual(
                [
                    (output / n).read_bytes()
                    for n in ["workflow_graphs.json", "workflow_graphs.html"]
                ],
                expected_bytes,
            )
        empty = {
            "descriptions": {},
            "inventory": {"skills": [], "total": 0},
            "workflows": [],
        }
        m = native.assemble_model(empty)
        self.assertEqual(m["summary"]["total_hooks"], 0)
        self.assertEqual(m["graph"]["elements"], {"nodes": [], "edges": []})
        manifest = native.parse_hooks_manifest(self.root / "skills/SKILL_HOOKS.yaml")
        self.assertIsNone(
            native.integration_surface_workflow(
                set(catalogue["descriptions"])
                | {"first", "second", "route", "runtime", "z-local"},
                catalogue["inventory"],
                manifest,
                {},
            )
        )
        loop = {
            "id": "fallback",
            "required_owner_skills": ["absent"],
            "required_hooks": ["one"],
        }
        self.assertEqual(
            native.workflow_from_loop(loop, manifest["hooks"], {}).steps[0].description,
            "hook fallback",
        )
        # All reflection endpoint branches and last duplicate node/step lookup.
        row = deepcopy(workflows[0])
        row["steps"] = list(row["steps"]) + [deepcopy(row["steps"][0])]
        row["reflective_edges"] = [
            {"from": a, "to": b, "output": "finding"}
            for a, b in [
                ("first", "second"),
                ("outside", "first"),
                ("first", "outside"),
                ("outside", "other"),
            ]
        ]
        custom = {**empty, "workflows": [row, {**row, "stack_id": "reset"}]}
        m = native.assemble_model(custom)
        edges = [e["data"] for e in m["graph"]["elements"]["edges"]]
        self.assertEqual(sum(e["edge_type"] == "workflow_entry" for e in edges), 2)
        self.assertTrue(
            any(
                e["edge_type"] == "workflow_reflective_loop"
                and e["source"].endswith(":03")
                for e in edges
            )
        )
        self.assertEqual(
            sum(e["edge_type"] == "reflective_external_reference" for e in edges), 6
        )
        ids = [n["data"]["id"] for n in m["graph"]["elements"]["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for flag in [True, False]:
            stream = io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(
                    native.emit_report(
                        {"ok": False, "json_path": "j", "html_path": "h"}, flag
                    ),
                    3,
                )

    def test_registered_mcp_lunar_and_stopping(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_docs_workflow_graph_render_workflow")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        manager = SessionManager()
        failure = None
        server = 'import sys;sys.path.insert(0,"scripts");from mcp_server import mcp;mcp.run(transport="stdio")'
        async with manager.open(
            "render",
            StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
            {},
        ) as remote:
            try:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, inventory=tools):
                    assets = snapshot(doc)
                    c = compile_workflow(
                        "mcp:render",
                        workflow_documents([DESCRIPTOR], assets)[0],
                        inventory,
                    )
                    return c, assets

                c, a = compile(document)
                self.assertTrue(c["runnable"], c["diagnostics"])
                self.assertTrue(c["runtime_source"])
                self.assertEqual(set(c["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def allow():
                    pass

                async def run(doc=document, options=None):
                    c, a = compile(doc)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    return await execute(
                        c,
                        a,
                        {
                            "options": options
                            or {
                                "output_dir": "artifacts/workflow_graphs",
                                "json": True,
                            },
                            "context": {"repository_root": str(self.root)},
                        },
                        remote,
                        allow,
                    )

                for flag in [True, False]:
                    self.cli(self.oracle, ["--json"] if flag else [])
                    expected = [
                        (self.output / n).read_bytes()
                        for n in ["workflow_graphs.json", "workflow_graphs.html"]
                    ]
                    for n in ["workflow_graphs.json", "workflow_graphs.html"]:
                        (self.output / n).unlink()
                    r = await run(
                        options={
                            "output_dir": "artifacts/workflow_graphs",
                            "json": flag,
                        }
                    )
                    self.assertEqual(r["status"], "accepted", r)
                    self.assertEqual(r["outputs"]["exit_code"], 0)
                    self.assertEqual(
                        r["outputs"]["report"]["summary"],
                        self.oracle.build_model()["summary"],
                    )
                    self.assertEqual(
                        [
                            (self.output / n).read_bytes()
                            for n in ["workflow_graphs.json", "workflow_graphs.html"]
                        ],
                        expected,
                    )
                    self.assertEqual(
                        [v["tool"] for v in r["calls"]],
                        [
                            "mathformer_graph_render_" + s
                            for s in [
                                "prepare_directory",
                                "load_catalogue",
                                "assemble_model",
                                "publish",
                            ]
                        ],
                    )
                    self.assertTrue(r["runtime"]["effect_records"])
                    self.assertTrue(r["runtime"]["provenance"])
                    self.assertTrue(r["replay_artifacts"])
                # Call exhaustion is a host budget, not a fabricated source loop.
                for n in ["workflow_graphs.json", "workflow_graphs.html"]:
                    (self.output / n).unlink()
                bounded = deepcopy(document)
                bounded["policy"]["limits"]["max_operation_calls"] = 3
                r = await run(bounded)
                self.assertEqual(r["status"], "failed", r)
                self.assertEqual(
                    sum(bool(v.get("transport_call_performed")) for v in r["calls"]), 3
                )
                self.assertFalse((self.output / "workflow_graphs.json").exists())
                # Missing manifest stops after mkdir and load: no retries or publication.
                hooks = self.root / "skills/SKILL_HOOKS.yaml"
                text = hooks.read_text()
                hooks.unlink()
                r = await run()
                self.assertEqual(r["status"], "failed")
                self.assertEqual(len(r["calls"]), 2)
                self.assertTrue(self.output.is_dir())
                self.assertFalse((self.output / "workflow_graphs.json").exists())
                hooks.write_text(text)
                malformed = deepcopy(document)
                malformed["flow"]["steps"][2]["arguments"]["catalogue"] = {
                    "literal": "{}"
                }
                r = await run(malformed)
                self.assertEqual(r["status"], "failed")
                self.assertEqual(len(r["calls"]), 3)
                self.assertFalse((self.output / "workflow_graphs.json").exists())
                # HTML write failure retains the earlier JSON write.
                html = self.output / "workflow_graphs.html"
                html.mkdir()
                r = await run()
                self.assertEqual(r["status"], "failed")
                self.assertEqual(len(r["calls"]), 4)
                self.assertEqual(
                    json.loads((self.output / "workflow_graphs.json").read_text()),
                    self.oracle.build_model(),
                )
                html.rmdir()
                # Native relative_to fails only after both outside files are written.
                outside_tmp = tempfile.TemporaryDirectory(
                    prefix="graph-render-outside-"
                )
                self.addCleanup(outside_tmp.cleanup)
                outside = Path(outside_tmp.name)
                r = await run(options={"output_dir": str(outside), "json": True})
                self.assertEqual(r["status"], "failed")
                self.assertEqual(len(r["calls"]), 4)
                self.assertEqual(
                    json.loads((outside / "workflow_graphs.json").read_text()),
                    self.oracle.build_model(),
                )
                self.assertEqual(
                    (outside / "workflow_graphs.html").read_text(),
                    self.oracle.render_html(self.oracle.build_model()),
                )
                occupied = self.root / "occupied"
                occupied.write_text("keep")
                r = await run(options={"output_dir": "occupied/subdir", "json": True})
                self.assertEqual(r["status"], "failed")
                self.assertEqual(len(r["calls"]), 1)
                self.assertEqual(occupied.read_text(), "keep")
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                c, a = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        c,
                        a,
                        {
                            "options": {
                                "output_dir": "artifacts/workflow_graphs",
                                "json": True,
                            },
                            "context": {"repository_root": str(self.root)},
                        },
                        remote,
                        pending,
                    )
            except Exception as error:
                failure = error
        self.assertFalse(manager.active)
        if failure:
            raise failure


if __name__ == "__main__":
    unittest.main(verbosity=2)

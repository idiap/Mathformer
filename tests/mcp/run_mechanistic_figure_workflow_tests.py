#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native/MCP/PRISM equivalence fixtures. Only tectonic lookup/process is replaced.

The renderer has no model/provider calls. Its JSON input fixture is actual data.
The test server imports aggregate production registration unchanged, then patches
only the external compiler boundary; it never starts a compiler or reads config.
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
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import yaml
from mechanistic_figure_tools import source, native_context
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_paper_mechanistic_figure_render_workflow/workflow.yaml"


sys.path.insert(0, str(ROOT / "tests/mcp/fixtures"))
from mechanistic_figure_server import compiler_fixture


def model():
    return {
        "title": "Fixture & <math>",
        "layers": [{"x": 20, "label": "Input"}],
        "nodes": [
            {
                "id": "a",
                "x": 20,
                "y": 110,
                "role": "state",
                "label": "many words " * 20,
                "label_tex": r"\alpha",
                "equation": "x_1",
                "equation_tex": r"x_{1}^2",
            },
            {
                "id": "b",
                "x": 400,
                "y": 110,
                "role": "unknown",
                "label": "B & #_%",
                "equation_svg": "x_{i}^2_^{oops",
            },
            {
                "id": "c",
                "x": 20,
                "y": 300,
                "role": "criterion",
                "label": "C",
                "equation": "~\\{}^",
            },
        ],
        "edges": [
            {"source": a, "target": b, "kind": k, "label": text}
            for a, b, k, text in [
                ("a", "b", "forward", "x"),
                ("b", "a", "feedback", "long label " * 25),
                ("a", "c", "generative", "down"),
                ("c", "a", "other", "up"),
            ]
        ],
        "gates": [{"label": "legacy & criterion"}],
    }


def oracle():
    spec = importlib.util.spec_from_loader(
        "figure_original",
        SourceFileLoader(
            "figure_original",
            str(ROOT / "tests/mcp/fixtures/mechanistic_figure_original.py.txt"),
        ),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def invoke(module, argv):
    output, errors = io.StringIO(), io.StringIO()
    with (
        patch.object(sys, "argv", ["figure", *argv]),
        redirect_stdout(output),
        redirect_stderr(errors),
    ):
        try:
            code = module.main()
        except SystemExit as error:
            code = error.code
    return code, output.getvalue(), errors.getvalue()


def snapshot(document):
    def asset(path, text):
        return {
            "path": path,
            "content": text,
            "encoding": "text",
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(r["path"], (ROOT / r["path"]).read_text())
        for r in document["provenance"]["sources"]
    ]


class FigureTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="figure-fixture-")
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)
        self.model_path = self.directory / "model.json"
        self.model_path.write_text(json.dumps(model()))
        self.ledger = self.directory / "compiler.jsonl"

    def test_native_equivalence_and_render_bounds(self):
        old, native = oracle(), source()
        which, run = compiler_fixture("success", self.ledger)
        with (
            native_context(self.directory),
            patch.object(native.shutil, "which", which),
            patch.object(native.subprocess, "run", run),
        ):
            for flags in [
                [],
                ["--svg", "out/a.svg"],
                ["--tex", "out/a.tex"],
                ["--compile-pdf"],
                ["--svg", "out/b.svg", "--tex", "out/b.tex", "--compile-pdf"],
            ]:
                for json_report in [False, True]:
                    argv = ["--model", "model.json", *flags] + (
                        ["--json"] if json_report else []
                    )
                    expected = invoke(old, argv)
                    before = {
                        str(p.relative_to(self.directory)): p.read_bytes()
                        for p in self.directory.rglob("*")
                        if p.suffix in {".svg", ".tex", ".pdf"}
                    }
                    self.assertEqual(invoke(native, argv), expected)
                    self.assertEqual(
                        {
                            str(p.relative_to(self.directory)): p.read_bytes()
                            for p in self.directory.rglob("*")
                            if p.suffix in {".svg", ".tex", ".pdf"}
                        },
                        before,
                    )
            for argv in [[], ["--help"], ["--model", "model.json", "--bogus"]]:
                self.assertEqual(invoke(native, argv), invoke(old, argv))
            self.assertTrue(
                all(
                    row["kwargs"] == {"check": True}
                    for row in map(json.loads, self.ledger.read_text().splitlines())
                )
            )
        data = model()
        svg = native.render_svg(data)
        tex = native.render_tikz(data)
        self.assertEqual(svg, old.render_svg(data))
        self.assertEqual(tex, old.render_tikz(data))
        self.assertIn('width="1200" height="630"', svg)
        self.assertIn('width="200" height="92"', svg)
        self.assertIn('width="76" height="22"', svg)
        self.assertIn('width="172" height="22"', svg)
        self.assertEqual(len(native.split_label("many words " * 100, 22)), 3)
        self.assertIn('baseline-shift="sub"', svg)
        self.assertIn('baseline-shift="super"', svg)
        self.assertIn('marker-end="url(#arrow-red)"', svg)
        self.assertIn(r"\textbf{\alpha}", tex)
        self.assertIn(r"B \& \#\_\%", tex)
        self.assertIn("legacy &amp; criterion", svg)
        data["validation_criteria"] = [{"label": "new"}]
        self.assertIn("Validation criteria: new", native.render_svg(data))
        self.assertNotIn("legacy", native.render_tikz(data))
        empty = {"nodes": [], "edges": []}
        self.assertEqual(native.render_svg(empty), old.render_svg(empty))
        for mode, exception in [
            ("missing", RuntimeError),
            ("fail", subprocess.CalledProcessError),
        ]:
            which, run = compiler_fixture(mode, self.ledger)
            with (
                native_context(self.directory),
                patch.object(native.shutil, "which", which),
                patch.object(native.subprocess, "run", run),
            ):
                for module in [old, native]:
                    with self.assertRaises(exception):
                        invoke(module, ["--model", "model.json", "--compile-pdf"])

    def test_registered_tools_and_lunar_runtime(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_paper_mechanistic_figure_render_workflow")
        self.assertEqual(document["lifecycle"], "active")
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertIn(
            "paper_skills/mechanistic-figure-renderer/scripts/render_mechanistic_figure.py",
            [r["path"] for r in document["provenance"]["sources"]],
        )
        manager = SessionManager()
        for mode in ["success", "missing", "fail"]:
            failure = None
            config = StdioConfig(
                command=str(ROOT / ".venv/bin/python"),
                args=[
                    str(ROOT / "tests/mcp/fixtures/mechanistic_figure_server.py"),
                    mode,
                    str(self.ledger),
                ],
                cwd=str(ROOT),
            )
            async with manager.open("figure-" + mode, config, {}) as remote:
                try:
                    tools = [
                        t.model_dump(by_alias=True, exclude_none=True)
                        for t in await remote.tools()
                    ]

                    def compile(doc, inventory=tools):
                        assets = snapshot(doc)
                        c = compile_workflow(
                            "mcp:figure",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            inventory,
                        )
                        return c, assets

                    c, assets = compile(document)
                    self.assertTrue(c["runnable"], c["diagnostics"])
                    self.assertTrue(c["runtime_source"])
                    self.assertEqual(set(c["bindings"]), set(document["operations"]))
                    self.assertFalse(compile(document, [])[0]["runnable"])

                    async def allow():
                        pass

                    async def run(argv, doc=document):
                        c, a = compile(doc)
                        self.assertTrue(c["runnable"], c["diagnostics"])
                        return await execute(
                            c,
                            a,
                            {
                                "argv": argv,
                                "context": {"working_directory": str(self.directory)},
                            },
                            remote,
                            allow,
                        )

                    if mode != "success":
                        pdf = self.directory / "failure.pdf"
                        pdf.unlink(missing_ok=True)
                        r = await run(
                            [
                                "--model",
                                "model.json",
                                "--svg",
                                "failure.svg",
                                "--tex",
                                "failure.tex",
                                "--compile-pdf",
                            ]
                        )
                        self.assertEqual(r["status"], "failed", r)
                        self.assertIsNone(r["outputs"])
                        self.assertEqual(
                            [v["tool"] for v in r["calls"]],
                            [
                                "mathformer_figure_" + s
                                for s in ["load", "svg", "tex", "pdf"]
                            ],
                        )
                        self.assertEqual(r["calls"][-1]["status"], "rejected")
                        self.assertTrue((self.directory / "failure.svg").exists())
                        self.assertTrue((self.directory / "failure.tex").exists())
                        self.assertFalse(pdf.exists())
                        continue
                    # Exercise registered tools' state ports directly as well as via PRISM.
                    loaded = await remote.call(
                        "mathformer_figure_load",
                        {
                            "argv": [
                                "--model",
                                "model.json",
                                "--svg",
                                "state.svg",
                                "--tex",
                                "state.tex",
                                "--compile-pdf",
                            ],
                            "context": {"working_directory": str(self.directory)},
                        },
                    )
                    state = loaded["state"]
                    self.assertEqual(state["model"], model())
                    self.assertEqual(state["model_path"], "model.json")
                    self.assertEqual(state["outputs"], {})
                    self.assertEqual(state["output_order"], [])
                    self.assertIsNone(state["tex_path"])
                    self.assertEqual(
                        [
                            loaded[k]
                            for k in ["want_svg", "want_tex", "want_pdf", "halted"]
                        ],
                        [True, True, True, False],
                    )
                    for index, stage in enumerate(["svg", "tex", "pdf"]):
                        state = (
                            await remote.call(
                                "mathformer_figure_" + stage, {"state": state}
                            )
                        )["state"]
                        self.assertEqual(
                            state["output_order"], ["svg", "tex", "pdf"][: index + 1]
                        )
                        self.assertEqual(
                            set(state["outputs"]), set(state["output_order"])
                        )
                        self.assertEqual(state["model"], model())
                    self.assertEqual(state["tex_path"], "state.tex")
                    carried = (
                        await remote.call("mathformer_figure_carry", {"state": state})
                    )["state"]
                    self.assertEqual(carried, state)
                    # Actual canonical transport reordered maps, but source observability
                    # still follows the recorded native insertion order.
                    state["args"]["json"] = False
                    stream = io.StringIO()
                    with redirect_stdout(stream):
                        report = source().report_step(state)
                    self.assertEqual(
                        list(report["result"]["outputs"]), ["svg", "tex", "pdf"]
                    )
                    self.assertLess(
                        stream.getvalue().index("'svg':"),
                        stream.getvalue().index("'tex':"),
                    )
                    self.assertLess(
                        stream.getvalue().index("'tex':"),
                        stream.getvalue().index("'pdf':"),
                    )
                    for flags, stages in [
                        ([], []),
                        (["--svg", "lunar/a.svg"], ["svg"]),
                        (["--tex", "lunar/a.tex"], ["tex"]),
                        (["--compile-pdf"], ["tex", "pdf"]),
                        (
                            [
                                "--svg",
                                "lunar/all.svg",
                                "--tex",
                                "lunar/all.tex",
                                "--compile-pdf",
                            ],
                            ["svg", "tex", "pdf"],
                        ),
                    ]:
                        for json_report in [True, False]:
                            argv = ["--model", "model.json", *flags] + (
                                ["--json"] if json_report else []
                            )
                            which, boundary = compiler_fixture("success", self.ledger)
                            # Independent old CLI oracle on identical native paths.
                            with (
                                native_context(self.directory),
                                patch.object(source().shutil, "which", which),
                                patch.object(source().subprocess, "run", boundary),
                            ):
                                old = invoke(oracle(), argv)
                            r = await run(argv)
                            self.assertEqual(r["status"], "accepted", r)
                            result = r["outputs"]["result"]
                            self.assertEqual(
                                result,
                                (
                                    json.loads(old[1])
                                    if json_report
                                    else __import__("ast").literal_eval(old[1])
                                ),
                            )
                            self.assertEqual(r["outputs"]["exit_code"], 0)
                            self.assertEqual(
                                (result["node_count"], result["edge_count"]), (3, 4)
                            )
                            self.assertEqual(
                                [v["tool"] for v in r["calls"]],
                                [
                                    "mathformer_figure_" + s
                                    for s in [
                                        "load",
                                        *[
                                            (stage if stage in stages else "carry")
                                            for stage in ["svg", "tex", "pdf"]
                                        ],
                                        "report",
                                    ]
                                ],
                            )
                            self.assertEqual(set(result["outputs"]), set(stages))
                            for kind, path in result["outputs"].items():
                                p = self.directory / path
                                if kind == "svg":
                                    self.assertEqual(
                                        p.read_text(), oracle().render_svg(model())
                                    )
                                if kind == "tex":
                                    self.assertEqual(
                                        p.read_text(), oracle().render_tikz(model())
                                    )
                                if kind == "pdf":
                                    self.assertEqual(
                                        p.read_bytes(),
                                        b"%PDF-fixture\n"
                                        + hashlib.sha256(
                                            p.with_suffix(".tex").read_bytes()
                                        )
                                        .hexdigest()
                                        .encode(),
                                    )
                            self.assertTrue(r["runtime"]["effect_records"])
                            self.assertTrue(r["runtime"]["provenance"])
                            self.assertTrue(r["replay_artifacts"])
                    # Help succeeds before model lookup and writes.
                    r = await run(
                        [
                            "--help",
                            "--model",
                            "absent.json",
                            "--svg",
                            "must-not-exist.svg",
                        ]
                    )
                    self.assertEqual(r["status"], "accepted", r)
                    self.assertEqual(len(r["calls"]), 2)
                    self.assertEqual(
                        [v["tool"] for v in r["calls"]],
                        ["mathformer_figure_load", "mathformer_figure_help"],
                    )
                    self.assertIn("--compile-pdf", r["outputs"]["result"])
                    self.assertFalse((self.directory / "must-not-exist.svg").exists())
                    for argv in [
                        [],
                        ["--model", "absent.json"],
                        ["--model", "model.json", "--unknown"],
                    ]:
                        r = await run(argv)
                        self.assertEqual(r["status"], "failed", r)
                        self.assertEqual(len(r["calls"]), 1)
                    malformed = self.directory / "bad.json"
                    malformed.write_text("{")
                    r = await run(["--model", "bad.json"])
                    self.assertEqual(r["status"], "failed")
                    self.assertEqual(len(r["calls"]), 1)
                    # Source lookup failure stops before SVG completes; no TeX stage.
                    broken = model()
                    broken["edges"][0]["target"] = "missing"
                    malformed.write_text(json.dumps(broken))
                    r = await run(
                        [
                            "--model",
                            "bad.json",
                            "--svg",
                            "bad.svg",
                            "--tex",
                            "never.tex",
                        ]
                    )
                    self.assertEqual(r["status"], "failed")
                    self.assertEqual(len(r["calls"]), 2)
                    self.assertFalse((self.directory / "bad.svg").exists())
                    self.assertFalse((self.directory / "never.tex").exists())
                    # Later filesystem failure keeps completed SVG and prevents report.
                    blocker = self.directory / "blocker"
                    blocker.write_text("keep")
                    r = await run(
                        [
                            "--model",
                            "model.json",
                            "--svg",
                            "retained.svg",
                            "--tex",
                            "blocker/f.tex",
                        ]
                    )
                    self.assertEqual(r["status"], "failed")
                    self.assertEqual(len(r["calls"]), 3)
                    self.assertTrue((self.directory / "retained.svg").exists())
                    self.assertEqual(blocker.read_text(), "keep")
                    # Host call exhaustion halts before TeX; no invented source loop.
                    bounded = deepcopy(document)
                    bounded["policy"]["limits"]["max_operation_calls"] = 2
                    r = await run(
                        [
                            "--model",
                            "model.json",
                            "--svg",
                            "bounded.svg",
                            "--tex",
                            "bounded.tex",
                            "--compile-pdf",
                        ],
                        bounded,
                    )
                    self.assertEqual(r["status"], "failed", r)
                    self.assertIn("budget", str(r).lower())
                    self.assertEqual(
                        sum(
                            bool(v.get("transport_call_performed")) for v in r["calls"]
                        ),
                        2,
                    )
                    self.assertTrue((self.directory / "bounded.svg").exists())
                    self.assertFalse((self.directory / "bounded.tex").exists())
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
                                "argv": ["--model", "model.json"],
                                "context": {"working_directory": str(self.directory)},
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

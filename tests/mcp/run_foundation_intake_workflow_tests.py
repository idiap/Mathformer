#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic source differential and registered MCP/Lunar/PRISM fixtures.

Intake has no external provider/model/compiler boundary, so none is substituted.
The real PRISM parser/checker/compiler/runtime executes only temporary inputs.
Explicit WORKFLOW_CONTRACT_PATH supports both candidate and installed contracts.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT)]
sys.path.extend(str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages"))

import asyncio
from contextlib import (
    contextmanager,
    asynccontextmanager,
    redirect_stdout,
    redirect_stderr,
)
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
from foundation_intake_tools import native
from mcp_connections.client import SessionManager, MCPConnectionError
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_physics_lean_foundation_intake_workflow/workflow.yaml"
PREFIX = "mathformer_foundation_intake_"
ORIGINAL = ROOT / "tests/mcp/fixtures/foundation_intake_original.py.txt"


def oracle():
    loader = SourceFileLoader("_foundation_intake_original", str(ORIGINAL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def cwd(root):
    before = Path.cwd()
    os.chdir(root)
    try:
        yield
    finally:
        os.chdir(before)


def cli(module, root, argv, process_argv=()):
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        cwd(root),
        patch.object(sys, "argv", ["intake.py", *process_argv]),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            outcome = ("return", module.main(argv))
        except SystemExit as error:
            outcome = ("exit", error.code)
        except Exception as error:
            outcome = ("raise", type(error).__name__, str(error))
    return outcome, stdout.getvalue(), stderr.getvalue()


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def snapshot(document):
    def asset(path, content):
        return dict(
            path=path,
            content=content,
            encoding="text",
            sha256=hashlib.sha256(content.encode()).hexdigest(),
        )

    return [asset(DESCRIPTOR, json.dumps(document))] + [
        asset(s["path"], (ROOT / s["path"]).read_text())
        for s in document["provenance"]["sources"]
    ]


@asynccontextmanager
async def diagnosed_session(manager, *args):
    async with manager.open(*args) as remote:
        try:
            yield remote
        except Exception:
            import traceback

            traceback.print_exc()
            raise


class IntakeTests(unittest.TestCase):
    def test_original_cli_equivalence(self):
        old = oracle()
        self.assertEqual(
            hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
            "da394dd5d899a94c262ce07d20e68da9820a0c802647c4dba03533ae28fe4f56",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixtures = {
                "list.json": [
                    "electric field",
                    7,
                    "dimension equality",
                    "electric field",
                ],
                "object.json": {"concepts": ["curl vector field", "unknown α"]},
                "lines.txt": " electric field \n\n dimension equality \n",
                "bad.json": "{",
                "shape.json": 7,
                "detected.json": {
                    "objects": [
                        None,
                        3,
                        {
                            "object_class": "vector_field",
                            "display_name": "B",
                            "source_examples": ["z", "a", "z"],
                        },
                        {
                            "object_class": "vector_field",
                            "display_name": "A",
                            "source_examples": ["b", "a"],
                        },
                        {
                            "object_class": "unrecognized",
                            "display_name": "unknown α",
                            "source_examples": [3, False],
                        },
                    ]
                },
                "bad_packet.json": [],
            }
            for name, value in fixtures.items():
                (root / name).write_text(
                    value if isinstance(value, str) else json.dumps(value)
                )
            cases = [
                [],
                None,
                ["--help"],
                ["--unknown"],
                ["--concept"],
                [
                    "--concept",
                    "curl vector field",
                    "--concept",
                    "electric field",
                    "--concept",
                    "unmatched α",
                ],
                ["--detected-object-packet", "detected.json"],
                ["--detected-object-packet", "bad_packet.json"],
            ]
            cases += [
                ["--concept-file", name]
                for name in (
                    "list.json",
                    "object.json",
                    "lines.txt",
                    "bad.json",
                    "shape.json",
                    "missing.json",
                )
            ]
            cases += [
                [
                    "--self-test",
                    "--concept-file",
                    "missing.json",
                    "--detected-object-packet",
                    "bad_packet.json",
                    "--concept",
                    "ignored",
                ]
            ]
            for argv in cases:
                for output, print_json in ((False, False), (True, False), (True, True)):
                    with self.subTest(argv=argv, output=output, json=print_json):
                        flags = (
                            None
                            if argv is None
                            else argv
                            + (["--output", "nested/out.json"] if output else [])
                            + (["--json"] if print_json else [])
                        )
                        outcomes = []
                        for module in (old, native):
                            target = root / "nested/out.json"
                            if target.exists():
                                target.unlink()
                            outcome = cli(module, root, flags, ["--self-test"])
                            outcomes.append(
                                (
                                    outcome,
                                    target.read_bytes() if target.exists() else None,
                                )
                            )
                        self.assertEqual(*outcomes)
            # Native mkdir survives a write failure; no implicit rollback.
            (root / "blocked").write_text("block")
            (root / "directory.json").mkdir()
            for path in ("blocked/out.json", "directory.json"):
                self.assertEqual(
                    cli(old, root, ["--output", path]),
                    cli(native, root, ["--output", path]),
                )

    def test_registered_tools_compile_and_execute(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(
            Path(os.environ["WORKFLOW_CONTRACT_PATH"]).read_text()
        )
        self.assertEqual(document["id"], "hub_physics_lean_foundation_intake_workflow")
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            dict(wall_time_seconds=3600, max_operation_calls=5),
        )
        self.assertIn(
            str(Path(native.__file__).relative_to(ROOT)),
            [s["path"] for s in document["provenance"]["sources"]],
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        spec = importlib.util.spec_from_file_location(
            "_intake_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        self.assertEqual(
            next(d for d in normalizer.inventory() if d["id"] == document["id"]),
            document,
        )
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "mount"
            root.mkdir()
            context = dict(
                working_directory=str(root),
                allow_mutating=True,
                process_argv=["--self-test"],
                program_name="intake.py",
            )
            manager = SessionManager()
            config = StdioConfig(
                command=sys.executable,
                args=[str(Path(__file__).resolve()), "--serve", str(root)],
                cwd=str(ROOT),
            )
            async with diagnosed_session(
                manager, "intake", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
            ) as remote:
                tools = [
                    t.model_dump(by_alias=True, exclude_none=True)
                    for t in await remote.tools()
                ]

                def compile(doc, advertised=tools):
                    assets = snapshot(doc)
                    return (
                        compile_workflow(
                            "mcp:intake",
                            workflow_documents([DESCRIPTOR], assets)[0],
                            advertised,
                        ),
                        assets,
                    )

                compiled, assets = compile(document)
                self.assertTrue(compiled["runnable"], compiled["diagnostics"])
                self.assertTrue(compiled["runtime_source"])
                self.assertTrue(compiled["prism_source"])
                self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
                self.assertFalse(compile(document, [])[0]["runnable"])

                async def authorize():
                    pass

                async def run(argv=(), doc=document, ctx=context):
                    selected, received = (
                        (compiled, assets) if doc is document else compile(doc)
                    )
                    self.assertTrue(selected["runnable"], selected["diagnostics"])
                    return await execute(
                        selected,
                        received,
                        dict(argv=None if argv is None else list(argv), context=ctx),
                        remote,
                        authorize,
                    )

                def names(result):
                    return [
                        c.get("tool", "").removeprefix(PREFIX) for c in result["calls"]
                    ]

                async def success(argv=(), ctx=context):
                    result = await run(argv, ctx=ctx)
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"]["exit_code"], 0)
                    self.assertTrue(result["execution_performed"])
                    self.assertTrue(result["replay_artifacts"])
                    self.assertTrue(result["runtime"]["effect_records"])
                    self.assertTrue(result["runtime"]["provenance"])
                    self.assertTrue(
                        all(c["status"] == "accepted" for c in result["calls"])
                    )
                    return result

                async def compare(argv):
                    expected = cli(oracle(), root, argv, context["process_argv"])
                    self.assertEqual(expected[0], ("return", 0))
                    before = files(root)
                    result = await success(argv)
                    self.assertEqual(result["outputs"]["stdout"], expected[1])
                    self.assertEqual(files(root), before)
                    text = result["outputs"]["json_text"]
                    self.assertEqual(json.loads(text), result["outputs"]["packet"])
                    return result

                result = await compare([])
                self.assertEqual(
                    names(result),
                    ["parse", "load_inputs", "normalize", "serialize", "emit"],
                )
                self.assertEqual(
                    result["outputs"]["packet"]["terminal_state"], "no_objects"
                )
                result = await success(ctx={**context, "allow_mutating": False})
                self.assertEqual(result["outputs"]["packet"]["object_count"], 0)
                result = await compare(None)
                self.assertEqual(
                    names(result),
                    ["parse", "self_test_inputs", "normalize", "serialize", "emit"],
                )
                self.assertEqual(result["outputs"]["packet"]["object_count"], 3)
                await compare(
                    [
                        "--self-test",
                        "--concept-file",
                        "missing.json",
                        "--detected-object-packet",
                        "missing.json",
                    ]
                )
                # Priority/first-match rules, fallback class, duplicate metadata and examples.
                detected = {
                    "objects": [
                        False,
                        None,
                        {
                            "object_class": "vector_field",
                            "display_name": "z field",
                            "source_examples": ["z", "a", "z"],
                        },
                        {
                            "object_class": "vector_field",
                            "display_name": "a field",
                            "source_examples": ["b", "a"],
                        },
                        {
                            "object_class": "novel_class",
                            "display_name": "novel",
                            "source_examples": ["u", "u", 7],
                        },
                        {"object_class": "commutator", "display_name": "C"},
                    ]
                }
                (root / "detected.json").write_text(json.dumps(detected))
                (root / "concepts.json").write_text(
                    json.dumps(
                        {
                            "concepts": [
                                "electric field",
                                "unmatched α",
                                "curl vector field",
                            ]
                        }
                    )
                )
                result = await compare(
                    [
                        "--concept",
                        "magnetic field",
                        "--concept-file",
                        "concepts.json",
                        "--detected-object-packet",
                        "detected.json",
                        "--source",
                        "Unicode α",
                        "--packet-id",
                        "β",
                        "--output",
                        "nested/out.json",
                        "--json",
                    ]
                )
                packet = result["outputs"]["packet"]
                by_id = {o["object_id"]: o for o in packet["objects"]}
                field = by_id["vector_field.real.euclidean3"]
                self.assertEqual(field["source"], "Unicode α")
                self.assertEqual(field["source_examples"], ["a", "b", "z"])
                self.assertEqual(
                    field["source_concepts"],
                    ["a field", "electric field", "magnetic field", "z field"],
                )
                self.assertEqual(
                    native.classify("curl vector field"), "gradient_divergence_curl"
                )
                self.assertEqual(
                    [o["priority"] for o in packet["objects"]],
                    sorted([o["priority"] for o in packet["objects"]]),
                )
                self.assertEqual(
                    (root / "nested/out.json").read_text(),
                    result["outputs"]["json_text"] + "\n",
                )
                # An unknown class keeps first metadata when canonical IDs collide.
                (root / "novel.json").write_text(
                    json.dumps(
                        {
                            "objects": [
                                {
                                    "object_class": "novel_class",
                                    "source_examples": ["u", "u", 7],
                                }
                            ]
                        }
                    )
                )
                result = await compare(["--detected-object-packet", "novel.json"])
                item = result["outputs"]["packet"]["objects"][0]
                self.assertEqual(item["object_class"], "novel_class")
                self.assertEqual(item["source_examples"], ["u", "u", "7"])
                for name, data in [
                    ("list.json", ["electric field", 7]),
                    ("lines.txt", " electric field \n \n dimension equality \n"),
                ]:
                    (root / name).write_text(
                        data if isinstance(data, str) else json.dumps(data)
                    )
                    await compare(
                        ["--concept-file", name, "--output", "quiet/out.json"]
                    )
                # Finite native traversal is not capped at the number of operations.
                (root / "many.json").write_text(json.dumps(["electric field"] * 257))
                result = await compare(["--concept-file", "many.json"])
                self.assertEqual(result["outputs"]["packet"]["object_count"], 1)
                self.assertEqual(len(result["calls"]), 5)
                # Help is a successful terminal path with no load/write/normalization.
                result = await success(["--help", "--output", "help/out.json"])
                self.assertEqual(names(result), ["parse", "help"])
                self.assertIsNone(result["outputs"]["packet"])
                self.assertEqual(
                    result["outputs"]["stdout"], cli(oracle(), root, ["--help"])[1]
                )
                self.assertFalse((root / "help").exists())
                # Real parser failures retain transport availability and stop immediately.
                for argv in (["--unknown"], ["--concept"]):
                    result = await run(argv)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(names(result), ["parse"])
                    self.assertEqual(result["calls"][0]["status"], "rejected")
                    self.assertEqual(cli(oracle(), root, argv)[0], ("exit", 2))
                for filename, data in [
                    ("invalid.json", "{"),
                    ("shape.json", "7"),
                    ("bad_packet.json", "[]"),
                    ("bad_objects.json", '{"objects":null}'),
                    ("bad_examples.json", '{"objects":[{"source_examples":null}]}'),
                ]:
                    (root / filename).write_text(data)
                for flag, filename, stop in [
                    ("--concept-file", "missing.json", "load_inputs"),
                    ("--concept-file", "invalid.json", "load_inputs"),
                    ("--concept-file", "shape.json", "load_inputs"),
                    ("--detected-object-packet", "bad_packet.json", "normalize"),
                    ("--detected-object-packet", "bad_objects.json", "normalize"),
                    ("--detected-object-packet", "bad_examples.json", "normalize"),
                ]:
                    result = await run([flag, filename, "--output", "failed/out.json"])
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(names(result)[-1], stop)
                    self.assertFalse((root / "failed").exists())
                # Assertions in serialize are real; invalid self-test packets never emit.
                args = native.parse_options(["--self-test"])
                empty = native.build_packet(
                    concepts=[], detected_packet={}, packet_id="x", source="x"
                )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "serialize",
                        dict(args=args, packet=empty, packet_json=json.dumps(empty)),
                    )
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "serialize",
                        dict(args=args, packet=empty, packet_json="{}"),
                    )
                (root / "blocker").write_text("block")
                (root / "out_directory").mkdir()
                for path in ("blocker/out.json", "out_directory"):
                    result = await run(["--output", path])
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(names(result)[-1], "emit")
                    self.assertIsNone(result["outputs"])
                # Caller opt-in, service roots, symlink resolution and read-only policy.
                denied = {**context, "allow_mutating": False}
                result = await run(["--output", "denied/out.json"], ctx=denied)
                self.assertEqual(result["status"], "failed")
                self.assertFalse((root / "denied").exists())
                outside = base / "outside"
                outside.mkdir()
                (root / "escape").symlink_to(outside, target_is_directory=True)
                for path in (str(outside / "out.json"), "escape/out.json"):
                    result = await run(["--output", path])
                    self.assertEqual(result["status"], "failed")
                self.assertEqual(files(outside), {})
                budget = deepcopy(document)
                budget["policy"]["limits"]["max_operation_calls"] = 3
                result = await run(["--output", "budget/out.json"], doc=budget)
                self.assertEqual(result["status"], "failed")
                self.assertIn("budget", str(result).lower())
                self.assertEqual(
                    sum(
                        bool(c.get("transport_call_performed")) for c in result["calls"]
                    ),
                    3,
                )
                self.assertFalse((root / "budget").exists())
                timed = deepcopy(document)
                timed["policy"]["limits"]["wall_time_seconds"] = 1
                selected, received = compile(timed)

                async def pending():
                    await asyncio.Event().wait()

                with self.assertRaises(TimeoutError):
                    await execute(
                        selected,
                        received,
                        dict(argv=[], context=context),
                        remote,
                        pending,
                    )
                await success(["--self-test"])
            self.assertFalse(manager.active)
            config.args.append("--readonly")
            async with diagnosed_session(
                manager, "intake-readonly", config, {"LUNAR_PLATFORM_ROOT": str(LUNAR)}
            ) as remote:
                with self.assertRaises(MCPConnectionError):
                    await remote.call(
                        PREFIX + "emit",
                        dict(
                            args=native.parse_options(
                                ["--output", "readonly/out.json"]
                            ),
                            text="{}",
                            context=context,
                        ),
                    )
                self.assertFalse((root / "readonly").exists())
            self.assertFalse(manager.active)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import mcp_server

        mcp_server.apply_runtime_config(
            allowed_write_roots=[sys.argv[sys.argv.index("--serve") + 1]]
        )
        mcp_server._READONLY = "--readonly" in sys.argv
        mcp_server.mcp.run(transport="stdio")
    else:
        unittest.main(verbosity=2)

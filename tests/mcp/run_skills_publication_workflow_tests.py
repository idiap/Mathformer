#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native CLI parity and real registered MCP/Lunar/PRISM fixtures.

Publication touches synthetic repositories only. This workflow has no provider
or external compiler boundary to substitute. The PRISM parser, checker,
compiler and runtime are real, including rejected and exhausted fixtures.
"""

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
LUNAR = Path(os.environ["LUNAR_PLATFORM_ROOT"])
python = LUNAR / ".venv/bin/python"
if python.exists() and Path(sys.prefix).resolve() != (LUNAR / ".venv").resolve():
    os.execv(str(python), [str(python), str(Path(__file__).resolve()), *sys.argv[1:]])
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [str(LUNAR / "app/backend"), str(ROOT / "scripts"), str(ROOT), *SITES]

import asyncio
from copy import deepcopy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
import yaml

import link_agent_skills as native
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/hub/hub_skills_link_workflow/workflow.yaml"
AUTHORED = "skills/control/workflow-contract-validator/references/skills-publication.workflow.json"
TARGETS = (".agents/skills", ".claude/skills", ".opencode/skills")
OPTIONS = dict(
    source="skills/",
    profile="all-repo",
    mode="auto",
    replace=True,
    dry_run=False,
    json=False,
    max_discovered_skills=1024,
)


def populate(root, count=2, occupied=False):
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    for index in reversed(range(count)):
        path = root / "skills" / "fixture" / f"skill-{index:04d}" / "SKILL.md"
        path.parent.mkdir(parents=True)
        path.write_text(f"# Deterministic skill {index}\n")
    if occupied:
        for target in TARGETS:
            path = root / target / "skill-0000"
            path.mkdir(parents=True)
            (path / "old.txt").write_text("old\n")


def assets(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=path,
            content=text,
            encoding="text",
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        for path, text in values.items()
    ]


def cli(root, options, original=False):
    # Real CLI process, frozen source oracle, identical input paths and argv.
    script = ROOT / (
        "tests/mcp/fixtures/skills_publication_original.py.txt"
        if original
        else "scripts/link_agent_skills.py"
    )
    command = [
        sys.executable,
        str(script),
        "--source",
        str(root / "skills"),
        "--mode",
        options["mode"],
    ]
    for target in TARGETS:
        command += ["--target", str(root / target)]
    for key, flag in [
        ("replace", "--replace"),
        ("dry_run", "--dry-run"),
        ("json", "--json"),
    ]:
        if options[key]:
            command.append(flag)
    return subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=30)


class PublicationTests(unittest.TestCase):
    maxDiff = None

    def test_contract_identity_generator_provenance(self):
        document = yaml.safe_load(CONTRACT.read_text())
        self.assertEqual(document, json.loads((ROOT / AUTHORED).read_text()))
        spec = importlib.util.spec_from_file_location(
            "publication_generator",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(document, module.skills_publication_descriptor())
        self.assertEqual(document["id"], "hub_skills_link_workflow")
        self.assertEqual(document["aliases"], ["skills:link"])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 3081},
        )
        self.assertEqual(document["policy"]["failure"]["retry"]["max_attempts"], 1)
        self.assertEqual(document["flow"]["steps"][2]["max_iterations"], 3)
        self.assertEqual(
            document["flow"]["steps"][2]["body"]["steps"][1]["max_iterations"], 1024
        )
        self.assertTrue(
            any(
                row["path"] == "scripts/link_agent_skills.py"
                and row["selector"] == "main"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )

    def test_native_failure_and_bound_without_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            populate(root, 1024)
            skills = native.discover_skills(root / "skills")
            self.assertEqual(len(skills), 1024)
            results = native.publish_skills(
                skills, [root / p for p in TARGETS], "auto", True, True
            )
            self.assertEqual(len(results), 3072)
            self.assertEqual(
                [r.skill for r in results[:1024]], [s.name for s in skills]
            )
            self.assertFalse((root / ".agents").exists())
            # Real I/O failure after a completed target: no rollback or later target.
            populate(root)
            (root / ".claude").write_text("blocks mkdir\n")
            for original in (True, False):
                if (root / ".agents").exists():
                    shutil.rmtree(root / ".agents")
                result = cli(root, OPTIONS, original)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NotADirectoryError", result.stderr)
                self.assertTrue((root / ".agents/skills/skill-0000").is_symlink())
                self.assertFalse((root / ".opencode").exists())
            # Exercise actual auto fallback failure using filesystem permissions.
            # No native function or OS call is replaced by a test implementation.
            target = root / "readonly"
            target.mkdir(mode=0o555)
            try:
                with self.assertRaises(PermissionError) as caught:
                    native.publish_one(skills[0], target, "auto", True, False)
                # Exception context records failed symlinking before copying.
                self.assertIsInstance(caught.exception.__context__, PermissionError)
                self.assertFalse((target / skills[0].name).exists())
            finally:
                target.chmod(0o755)
            # Existing same-source links stay unchanged, even in explicit copy
            # mode with replacement requested.
            target = root / "same-source"
            target.mkdir()
            source = skills[0].resolve()
            (target / source.name).symlink_to(source, target_is_directory=True)
            row = native.publish_one(source, target, "copy", True, False)
            self.assertEqual((row.status, row.mode), ("unchanged", "symlink"))

    def test_real_registered_mcp_lunar_prism(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        document = yaml.safe_load(CONTRACT.read_text())
        with tempfile.TemporaryDirectory() as directory:
            allowed = Path(directory).resolve()
            root = allowed / "repo"
            manager = SessionManager()
            server = (
                'import sys;sys.path.insert(0,"scripts");import mcp_server as s;'
                f"s.apply_runtime_config(allowed_write_roots=[{str(allowed)!r}]);"
                's.mcp.run(transport="stdio")'
            )
            failure = None
            async with manager.open(
                "skills-publication",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    tools = [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in await remote.tools()
                    ]

                    def compiled(doc, inventory=None):
                        snapshot = assets(doc)
                        loaded = workflow_documents([DESCRIPTOR], snapshot)[0]
                        self.assertTrue(loaded["validation"]["valid"], loaded)
                        workflow = compile_workflow(
                            "mcp:skills-publication",
                            loaded,
                            tools if inventory is None else inventory,
                        )
                        return workflow, snapshot

                    workflow, snapshot = compiled(document)
                    self.assertTrue(workflow["runnable"], workflow["diagnostics"])
                    self.assertEqual(workflow["runtime_status"], "ready")
                    self.assertTrue(workflow["prism_source"])
                    self.assertTrue(workflow["runtime_source"])
                    self.assertEqual(
                        set(workflow["bindings"]), set(document["operations"])
                    )
                    # Deterministic compiler rejection fixture: a missing real
                    # interface must prevent qualification, with no model call.
                    rejected, _ = compiled(
                        document,
                        [
                            t
                            for t in tools
                            if t["name"]
                            != "mathformer_skills_publication_publish_and_advance"
                        ],
                    )
                    self.assertFalse(rejected["runnable"])
                    self.assertTrue(rejected["diagnostics"])

                    async def authorize():
                        pass

                    async def run(options=None, doc=None, repository=None):
                        current, files = (
                            compiled(doc) if doc is not None else (workflow, snapshot)
                        )
                        return await execute(
                            current,
                            files,
                            {
                                "options": options or OPTIONS,
                                "repository_root": str(repository or root),
                            },
                            remote,
                            authorize,
                        )

                    # Exact admitted upper boundary through real registered
                    # ports, including immutable state and the last transition.
                    # Intermediate publications are exercised in the graph below.
                    populate(root, 1024)
                    dry = {**OPTIONS, "dry_run": True}
                    discovered = await remote.call(
                        "mathformer_skills_publication_discover",
                        {"options": dry, "repository_root": str(root)},
                    )
                    self.assertEqual(len(discovered["skills"]), 1024)
                    packed = await remote.call(
                        "mathformer_skills_publication_resolve_and_pack",
                        {
                            "options": dry,
                            "repository_root": str(root),
                            "skills": discovered["skills"],
                        },
                    )
                    state = packed["state"]
                    self.assertEqual(state["target_index"], 0)
                    self.assertEqual(state["skill_index"], 0)
                    self.assertEqual(state["results"], [])
                    self.assertEqual(
                        state["targets"], [str(root / path) for path in TARGETS]
                    )
                    state["skill_index"] = 1023
                    before = deepcopy(state)
                    advanced = await remote.call(
                        "mathformer_skills_publication_publish_and_advance",
                        {"state": state, "options": dry},
                    )
                    self.assertEqual(state, before)
                    self.assertTrue(advanced["done"])
                    self.assertEqual(advanced["state"]["skill_index"], 1024)
                    self.assertEqual(
                        advanced["state"]["results"][0]["skill"], "skill-1023"
                    )
                    self.assertFalse((root / ".agents").exists())
                    order = (
                        ["discover", "resolve_and_pack"]
                        + (
                            ["prepare_target"]
                            + ["publish_and_advance"] * 2
                            + ["advance_target"]
                        )
                        * 3
                        + ["finish"]
                    )
                    for mode, replace, dry, json_output, occupied in [
                        ("auto", True, False, False, False),
                        ("symlink", True, False, True, False),
                        ("copy", True, False, True, True),
                        ("auto", False, False, False, True),
                        ("copy", True, True, True, True),
                        ("auto", True, True, False, False),
                    ]:
                        options = {
                            **OPTIONS,
                            "mode": mode,
                            "replace": replace,
                            "dry_run": dry,
                            "json": json_output,
                        }
                        populate(root, occupied=occupied)
                        # Frozen CLI and current CLI must render identical output.
                        expected = cli(root, options, original=True)
                        self.assertEqual(expected.returncode, 0, expected.stderr)
                        populate(root, occupied=occupied)
                        current = cli(root, options)
                        self.assertEqual(
                            (current.returncode, current.stdout), (0, expected.stdout)
                        )
                        populate(root, occupied=occupied)
                        result = await run(options)
                        self.assertEqual(result["status"], "accepted", result)
                        output = result["outputs"]
                        self.assertEqual(output["returncode"], 0)
                        self.assertEqual(output["stdout"], expected.stdout)
                        self.assertEqual(
                            [call["operation"] for call in result["calls"]], order
                        )
                        rows = output["results"]
                        self.assertEqual(len(rows), 6)
                        self.assertEqual(
                            [row["target"] for row in rows],
                            [
                                str(root / p / f"skill-{i:04d}")
                                for p in TARGETS
                                for i in range(2)
                            ],
                        )
                        if json_output:
                            self.assertEqual(json.loads(output["stdout"]), rows)
                        if occupied and not replace:
                            self.assertEqual(
                                [row["status"] for row in rows],
                                ["skipped", "created"] * 3,
                            )
                        if not dry and mode in ("auto", "symlink") and not occupied:
                            again = await run(options)
                            self.assertTrue(
                                all(
                                    row["status"] == "unchanged"
                                    for row in again["outputs"]["results"]
                                )
                            )
                        if dry and not occupied:
                            self.assertFalse((root / ".agents").exists())
                    # Admission errors propagate and MCP remains usable.
                    for count in (0, 1025):
                        populate(root, count)
                        result = await run()
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(len(result["calls"]), 1)
                        self.assertIsNone(result["outputs"])
                        self.assertFalse((root / ".agents").exists())
                    populate(root)
                    shutil.rmtree(root / "skills")
                    result = await run()
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(len(result["calls"]), 1)
                    # Stop at the real second-target failure, retain first pass.
                    populate(root)
                    (root / ".claude").write_text("blocks mkdir")
                    result = await run()
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:7]
                    )
                    self.assertTrue((root / ".agents/skills/skill-0001").exists())
                    self.assertFalse((root / ".opencode").exists())
                    # Copy failure within a skill pass stops immediately; the
                    # previous skill's completed copy remains on disk.
                    populate(root)
                    bad = root / "skills/fixture/skill-0001/broken"
                    bad.symlink_to(root / "missing-copy-input")
                    result = await run({**OPTIONS, "mode": "copy"})
                    self.assertEqual(result["status"], "failed", result)
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:5]
                    )
                    self.assertTrue(
                        (root / ".agents/skills/skill-0000/SKILL.md").is_file()
                    )
                    self.assertFalse((root / ".claude").exists())
                    # Last-permitted-iteration success and explicit exhaustion
                    # run through the real PRISM compiler and Lunar runtime.
                    dry = {**OPTIONS, "dry_run": True}
                    for limit, expected in [(2, "accepted"), (1, "failed")]:
                        populate(root)
                        bounded = deepcopy(document)
                        bounded["flow"]["steps"][2]["body"]["steps"][1][
                            "max_iterations"
                        ] = limit
                        result = await run(dry, bounded)
                        self.assertEqual(result["status"], expected, result)
                        if limit == 1:
                            self.assertIsNone(result["outputs"])
                            self.assertEqual(
                                [c["operation"] for c in result["calls"]], order[:4]
                            )
                    exhausted = deepcopy(document)
                    exhausted["flow"]["steps"][2]["until"] = {"literal": False}
                    result = await run(dry, exhausted)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        [c["operation"] for c in result["calls"]], order[:-1]
                    )
                    budget = deepcopy(document)
                    budget["policy"]["limits"]["max_operation_calls"] = 4
                    result = await run(dry, budget)
                    self.assertEqual(result["status"], "failed")
                    self.assertEqual(
                        sum(
                            bool(c.get("transport_call_performed"))
                            for c in result["calls"]
                        ),
                        4,
                    )
                    # Service write admission fails before any target mutation.
                    with tempfile.TemporaryDirectory() as other:
                        outside = Path(other).resolve() / "repo"
                        populate(outside)
                        result = await run(repository=outside)
                        self.assertEqual(result["status"], "failed", result)
                        self.assertEqual(
                            [c["operation"] for c in result["calls"]], order[:3]
                        )
                        self.assertFalse((outside / ".agents").exists())
                except Exception as error:
                    failure = error
            self.assertFalse(manager.active)
            if failure:
                raise failure


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False).result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )

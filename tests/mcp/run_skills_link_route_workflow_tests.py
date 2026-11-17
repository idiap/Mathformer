#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Offline native skills.link parity and registered MCP/Lunar/PRISM execution.

Unmodified publication/discovery scripts execute only in synthetic repositories.
Only a separate external compiler boundary is substituted; no production tree
publication, provider, credentials, or theorem prover is involved.
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
FIXTURES = ROOT / "tests/mcp/fixtures"
SITES = [str(p) for p in (ROOT / ".venv/lib").glob("python*/site-packages")]
sys.path[:0] = [
    str(LUNAR / "app/backend"),
    str(ROOT / "scripts"),
    str(FIXTURES),
    *SITES,
]

import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib.util
import json
import shutil
import tempfile
from types import SimpleNamespace
import unittest
import yaml

import mathformer as hub
import link_agent_skills as publication
from skills_link_route_tools import (
    ACTIONS,
    ROUTE,
    WRITES,
    selected_match,
    checked_registry,
    check_state,
)
from reasoning_route_compiler import install
from mcp_connections.client import SessionManager
from mcp_connections.models import StdioConfig
from mcp_connections.contracts import workflow_documents
from mcp_connections.workflow_compiler import compile_workflow
from mcp_connections.execution import execute

spec = importlib.util.spec_from_file_location(
    "skills_discovery", ROOT / "tests/agent_clients/run_skill_client_discovery.py"
)
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)
DESCRIPTOR = "skills/control/workflow-contract-validator/references/normalized-workflows/route/route_skills_link_workflow/workflow.yaml"
SCHEMA = "skills/control/workflow-contract-validator/references/normalized-workflows/hub-interface.schema.json"
AUTHORED = "skills/control/workflow-contract-validator/references/skills-link-route.workflow.json"
CONTRACT = Path(os.environ["WORKFLOW_CONTRACT_PATH"])
MATCH = {
    "route": {"route_id": ROUTE, "action_ids": list(ACTIONS)},
    "score": 23,
    "matched_terms": ["publish", "skills"],
}
REGISTRY = {key: hub.action_to_dict(hub.build_registry()[key]) for key in ACTIONS}
ORDER = [
    "initialize",
    "select",
    "link",
    "advance",
    "select",
    "discovery",
    "advance",
    "finish",
]


def original():
    scope = dict(vars(hub))
    exec((FIXTURES / "skills_link_route_original.py.txt").read_text(), scope)
    return SimpleNamespace(**scope)


def populate(root, mode="success"):
    root.mkdir(parents=True, exist_ok=True)
    for path in WRITES:
        dest = root / path
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.exists():
            shutil.rmtree(dest)
    for path in [
        "scripts/link_agent_skills.py",
        "tests/agent_clients/run_skill_client_discovery.py",
    ]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)
    shutil.rmtree(root / "skills", ignore_errors=True)
    (root / "skills").mkdir()
    if mode != "empty":
        for name in sorted(
            discovery.REQUIRED_SMOKE_SKILLS | {"zeta-test", "alpha-test"}
        ):
            if mode == "missing_smoke" and name == "workflow-contract-validator":
                continue
            target = root / "skills" / "test" / name / "SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text(
                "---\nname: " + name + "\n---\nSynthetic skill fixture.\n"
            )
    if mode == "missing_link":
        (root / "scripts/link_agent_skills.py").unlink()
    if mode == "missing_discovery":
        (root / "tests/agent_clients/run_skill_client_discovery.py").unlink()
    if mode == "occupied":
        (root / ".agents").mkdir(exist_ok=True)
        (root / ".agents/skills").write_text("occupied destination")
    if mode == "published":
        publication.publish_skills(
            publication.discover_skills(root / "skills"),
            [root / path for path in WRITES],
            "auto",
            True,
            False,
        )


def snapshot(document):
    values = {
        row["path"]: (ROOT / row["path"]).read_text()
        for row in document["provenance"]["sources"]
    }
    values[SCHEMA] = (ROOT / SCHEMA).read_text()
    values[DESCRIPTOR] = json.dumps(document)
    return [
        dict(
            path=p,
            content=s,
            encoding="text",
            sha256=hashlib.sha256(s.encode()).hexdigest(),
        )
        for p, s in values.items()
    ]


class SkillsLinkTests(unittest.TestCase):
    maxDiff = None

    def test_generator_contract_and_provenance(self):
        document = yaml.safe_load(CONTRACT.read_text())
        spec = importlib.util.spec_from_file_location(
            "skills_normalizer",
            ROOT
            / "skills/control/workflow-contract-validator/scripts/normalize_workflows.py",
        )
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        self.assertEqual(generator.skills_link_route_descriptor(), document)
        self.assertEqual(json.loads((ROOT / AUTHORED).read_text()), document)
        self.assertEqual(document["id"], "route_skills_link_workflow")
        self.assertEqual(document["aliases"], [ROUTE])
        self.assertEqual(document["lifecycle"], "active")
        self.assertEqual(
            document["policy"]["limits"],
            {"wall_time_seconds": 3600, "max_operation_calls": 8},
        )
        self.assertEqual(
            document["policy"]["effects"]["filesystem"]["write"], list(WRITES)
        )
        self.assertEqual(
            document["policy"]["failure"],
            {"default": "fail", "retry": {"max_attempts": 1, "retryable_codes": []}},
        )
        self.assertEqual(document["flow"]["steps"][1]["max_iterations"], 2)
        self.assertTrue(
            any(
                row["path"] == "scripts/mathformer.py"
                and row["selector"] == "run_intent_match"
                for row in document["provenance"]["sources"]
            )
        )
        for row in document["provenance"]["sources"]:
            self.assertEqual(
                row["digest"],
                "sha256:"
                + hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(),
            )
        self.assertEqual(selected_match(MATCH).route.action_ids, ACTIONS)
        for item in checked_registry(REGISTRY).values():
            self.assertIsNone(item.timeout_seconds)
            self.assertFalse(item.depends_on)
        self.assertEqual(checked_registry({}), {})

    def test_native_state_sticky_failure_and_exact_bound(self):
        for keep in [False, True]:
            for first_ok in [False, True]:
                state = hub.initialize_intent_state()
                child = {"ok": first_ok, "stdout": "unchanged observation"}
                updated, done = hub.advance_intent_state(
                    state, child, hub.RunContext(keep_going=keep), 2
                )
                self.assertEqual(state, {"ok": True, "children": []})
                self.assertIs(updated["children"][0], child)
                self.assertEqual(done, not first_ok and not keep)
                self.assertEqual(
                    hub.select_intent_action(updated, selected_match(MATCH)), ACTIONS[1]
                )
                final, done = hub.advance_intent_state(
                    updated, {"ok": True}, hub.RunContext(keep_going=keep), 2
                )
                self.assertTrue(done)
                self.assertEqual(final["ok"], first_ok)
                check_state(final)
                with self.assertRaisesRegex(ValueError, "out of bounds"):
                    check_state(final, selecting=True)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            check_state({"ok": False, "children": []})

    def test_real_publication_and_discovery_traversals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            populate(root)
            skills = publication.discover_skills(root / "skills")
            targets = [root / path for path in WRITES]
            planned = publication.publish_skills(skills, targets, "auto", True, True)
            self.assertEqual(len(planned), 3 * len(skills))
            self.assertTrue(all(row.status == "created" for row in planned))
            self.assertFalse(any(target.exists() for target in targets))
            created = publication.publish_skills(skills, targets, "auto", True, False)
            self.assertEqual(
                [(r.target, r.skill) for r in created],
                [
                    (str(target / skill.name), skill.name)
                    for target in targets
                    for skill in skills
                ],
            )
            self.assertTrue(
                all(r.status == "created" and r.mode == "symlink" for r in created)
            )
            unchanged = publication.publish_skills(skills, targets, "auto", True, False)
            self.assertTrue(all(r.status == "unchanged" for r in unchanged))
            target = targets[0] / skills[0].name
            target.unlink()
            target.mkdir()
            (target / "stale").write_text("replace me")
            skipped = publication.publish_one(
                skills[0], targets[0], "auto", False, False
            )
            self.assertEqual(skipped.status, "skipped")
            copied = publication.publish_one(skills[0], targets[0], "copy", True, False)
            self.assertEqual(copied.mode, "copy")
            self.assertFalse((target / "stale").exists())
            self.assertTrue(discovery.build_report(root)["ok"])
            # Accumulate failures over every client, never stop at the first.
            (targets[1] / skills[0].name).unlink()
            (targets[1] / "unexpected").mkdir()
            bad = targets[2] / skills[1].name
            bad.unlink()
            bad.symlink_to(root / "absent")
            state = discovery.initialize_discovery(
                {p.name: str(p) for p in skills}, root
            )
            for cursor in range(3):
                self.assertEqual(state["cursor"], cursor)
                state, done = discovery.advance_discovery(
                    state, discovery.inspect_discovery_client(state)
                )
                self.assertEqual(done, cursor == 2)
            report = discovery.aggregate_discovery(state)
            self.assertEqual(report, discovery.build_report(root))
            self.assertFalse(report["ok"])
            self.assertEqual([r["ok"] for r in report["clients"]], [True, False, False])
            self.assertEqual(report["clients"][1]["missing"], [skills[0].name])
            self.assertEqual(report["clients"][1]["extra"], ["unexpected"])
            self.assertEqual(report["clients"][2]["broken_links"], [skills[1].name])
            # A noncanonical symlink is warning-only if its SKILL.md exists.
            bad.unlink()
            bad.symlink_to(skills[0])
            warning = discovery.build_report(root)["clients"][2]
            self.assertTrue(warning["ok"])
            self.assertEqual(warning["warnings"], ["noncanonical_symlink_targets"])
            bad.unlink()
            bad.mkdir()
            self.assertIn(
                "missing_skill_md",
                discovery.build_report(root)["clients"][2]["blockers"],
            )
            with self.assertRaises(SystemExit):
                publication.discover_skills(root / "absent")
            empty = root / "empty"
            empty.mkdir()
            with self.assertRaises(SystemExit):
                publication.discover_skills(empty)

    def test_deterministic_external_compiler_capture_audit_and_propagation(self):
        # This selected route has no provider/compiler dependency. A separate
        # compiler action qualifies the shared native process boundary offline.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            saved = hub.subprocess
            try:
                for mode in ["success", "reject", "write", "timeout", "launch_error"]:
                    item = replace(
                        hub.build_registry()[ACTIONS[1]],
                        command=("fixture-reasoning-compiler", mode),
                        required_paths=(),
                        timeout_seconds=3 if mode == "timeout" else None,
                    )
                    calls = install(hub, root)
                    if mode == "launch_error":
                        with self.assertRaisesRegex(OSError, "compiler launch failed"):
                            hub.run_leaf_action(
                                item, hub.RunContext(), (), repository_root=root
                            )
                    else:
                        result = hub.run_leaf_action(
                            item, hub.RunContext(), (), repository_root=root
                        )
                        self.assertEqual(result["ok"], mode == "success")
                        self.assertEqual(
                            result["status"],
                            {"write": "undeclared_writes", "timeout": "timeout"}.get(
                                mode, "completed"
                            ),
                        )
                        if mode == "success":
                            self.assertFalse(json.loads(result["stdout"])["ok"])
                        elif mode == "reject":
                            self.assertEqual(result["returncode"], 7)
                        elif mode == "write":
                            self.assertEqual(
                                result["write_audit"]["unexpected_paths"],
                                ["undeclared.txt"],
                            )
                        elif mode == "timeout":
                            self.assertEqual(
                                (
                                    result["returncode"],
                                    result["stdout"],
                                    result["stderr"],
                                ),
                                (None, "partial", "deadline"),
                            )
                    self.assertEqual(
                        calls,
                        [{"argv": list(item.command), "timeout": item.timeout_seconds}],
                    )
                    (root / "undeclared.txt").unlink(missing_ok=True)
            finally:
                hub.subprocess = saved

    def test_registered_mcp_lunar_compile_execute_and_failure_paths(self):
        asyncio.run(self.scenario())

    async def scenario(self):
        with tempfile.TemporaryDirectory() as directory:
            allowed = Path(directory).resolve()
            manager = SessionManager()
            # Real server registrations and runtime config; no provider config
            # or credential lookup. Every mutating call is confined to allowed.
            server = (
                'import sys;sys.path.insert(0,"scripts");import mcp_server as s;'
                "s.apply_runtime_config(allowed_write_roots=["
                + repr(str(allowed))
                + "]);"
                's.mcp.run(transport="stdio")'
            )
            error = None
            async with manager.open(
                "skills-link",
                StdioConfig(command=sys.executable, args=["-c", server], cwd=str(ROOT)),
                {"PYTHONPATH": os.pathsep.join(SITES), "PYTHONDONTWRITEBYTECODE": "1"},
            ) as remote:
                try:
                    await self.connected_scenario(remote, allowed)
                except Exception as exc:
                    error = exc
            self.assertFalse(manager.active)
            if error:
                raise error

    async def connected_scenario(self, remote, allowed):
        document = yaml.safe_load(CONTRACT.read_text())
        tools = [
            tool.model_dump(by_alias=True, exclude_none=True)
            for tool in await remote.tools()
        ]

        def compile(doc):
            assets = snapshot(doc)
            documents = workflow_documents([DESCRIPTOR], assets)
            self.assertTrue(documents[0]["validation"]["valid"], documents[0])
            compiled = compile_workflow("mcp:skills-link", documents[0], tools)
            self.assertTrue(compiled["runnable"], compiled["diagnostics"])
            self.assertEqual(compiled["runtime_status"], "ready")
            self.assertTrue(compiled["prism_source"])
            self.assertTrue(compiled["runtime_source"])
            self.assertEqual(set(compiled["bindings"]), set(document["operations"]))
            return compiled, assets

        compiled, assets = compile(document)
        missing = [
            tool
            for tool in tools
            if tool["name"] != "mathformer_skills_link_route_link"
        ]
        rejected = compile_workflow(
            "mcp:skills-link", workflow_documents([DESCRIPTOR], assets)[0], missing
        )
        self.assertFalse(rejected["runnable"])
        self.assertTrue(rejected["diagnostics"])

        async def authorize():
            pass

        async def run(inputs, changed=None):
            workflow, received = compile(changed) if changed else (compiled, assets)
            return await execute(workflow, received, inputs, remote, authorize)

        root = allowed / "repository"
        base = {
            "context": vars(hub.RunContext(allow_mutating=True)),
            "match": MATCH,
            "registry": REGISTRY,
            "repository_root": str(root),
        }
        for mode in [
            "success",
            "published",
            "missing_link",
            "missing_discovery",
            "empty",
            "occupied",
            "missing_smoke",
        ]:
            for keep in [False, True]:
                populate(root, mode)
                inputs = deepcopy(base)
                inputs["context"]["keep_going"] = keep
                result = await run(inputs)
                self.assertEqual(result["status"], "accepted", result)
                actual = result["outputs"]["result"]
                # Recreate identical initial data for the frozen native oracle.
                populate(root, mode)
                expected = original().run_intent_match(
                    selected_match(MATCH),
                    checked_registry(REGISTRY),
                    hub.RunContext(**inputs["context"]),
                    repository_root=root,
                )
                self.assertEqual(actual, expected)
                count = len(actual["children"])
                self.assertEqual(
                    count,
                    (
                        1
                        if mode in ["missing_link", "empty", "occupied"] and not keep
                        else 2
                    ),
                )
                self.assertEqual(actual["ok"], mode in ["success", "published"])
                order = ORDER if count == 2 else ORDER[:4] + ["finish"]
                self.assertEqual([call["operation"] for call in result["calls"]], order)
                self.assertEqual(
                    [call["tool"] for call in result["calls"]],
                    ["mathformer_skills_link_route_" + name for name in order],
                )
                self.assertEqual(actual["route"]["score"], MATCH["score"])
                self.assertEqual(
                    actual["route"]["matched_terms"], MATCH["matched_terms"]
                )
                self.assertEqual(
                    actual["status"],
                    "intent_run_completed" if actual["ok"] else "intent_run_failed",
                )
                if mode in ["success", "published"]:
                    first, second = actual["children"]
                    self.assertEqual(
                        first["argv"],
                        [
                            sys.executable,
                            "scripts/link_agent_skills.py",
                            "--profile",
                            "all-repo",
                            "--mode",
                            "auto",
                            "--replace",
                        ],
                    )
                    self.assertEqual(
                        second["argv"],
                        [
                            sys.executable,
                            "tests/agent_clients/run_skill_client_discovery.py",
                            "--json",
                        ],
                    )
                    self.assertEqual(first["returncode"], 0)
                    self.assertTrue(first["write_audit"]["ok"])
                    self.assertEqual(
                        json.loads(second["stdout"]), discovery.build_report(root)
                    )
                    self.assertIn("skills processed: 27", first["stdout"])
                    self.assertIn(
                        "unchanged=27" if mode == "published" else "created=27",
                        first["stdout"],
                    )
                    self.assertTrue(
                        all(
                            (root / target / name).resolve() == path.resolve()
                            for target in WRITES
                            for name, path in discovery.canonical_skills(
                                root / "skills"
                            ).items()
                        )
                    )
                if mode == "empty":
                    self.assertNotEqual(actual["children"][0]["returncode"], 0)
                    self.assertIn("no skills found", actual["children"][0]["stderr"])
                if mode == "missing_smoke":
                    self.assertEqual(actual["children"][0]["returncode"], 0)
                    self.assertEqual(actual["children"][1]["returncode"], 1)
                    self.assertTrue(
                        all(
                            "missing_required_smoke_skill:workflow-contract-validator"
                            in item["blockers"]
                            for item in json.loads(actual["children"][1]["stdout"])[
                                "clients"
                            ]
                        )
                    )
                self.assertTrue(result["runtime"]["effect_records"])
                self.assertTrue(result["runtime"]["provenance"])
                self.assertTrue(result["replay_artifacts"])
        # Admission, dry-run, mutation denial and sticky failure followed by a
        # successful discovery all run through the actual registered tools.
        for dry in [False, True]:
            for allow in [False, True]:
                if allow and not dry:
                    continue
                for keep in [False, True]:
                    populate(root, "published")
                    inputs = deepcopy(base)
                    inputs["context"].update(
                        dry_run=dry, allow_mutating=allow, keep_going=keep
                    )
                    before = hub.snapshot_repository(root)
                    result = await run(inputs)
                    expected = original().run_intent_match(
                        selected_match(MATCH),
                        checked_registry(REGISTRY),
                        hub.RunContext(**inputs["context"]),
                        repository_root=root,
                    )
                    self.assertEqual(result["status"], "accepted", result)
                    self.assertEqual(result["outputs"], {"result": expected})
                    self.assertEqual(hub.snapshot_repository(root), before)
                    if not dry and keep:
                        self.assertFalse(expected["ok"])
                        self.assertTrue(expected["children"][1]["ok"])
                    if dry:
                        self.assertTrue(
                            all(c["status"] == "dry_run" for c in expected["children"])
                        )
        for keep in [False, True]:
            inputs = deepcopy(base)
            inputs["registry"] = {}
            inputs["context"]["keep_going"] = keep
            result = await run(inputs)
            # Admission returns negative children, but source-owned route
            # metadata indexing then raises for the incomplete registry.
            with self.assertRaises(KeyError):
                original().run_intent_match(
                    selected_match(MATCH),
                    {},
                    hub.RunContext(allow_mutating=True, keep_going=keep),
                    repository_root=root,
                )
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                [c["operation"] for c in result["calls"]],
                ORDER if keep else ORDER[:4] + ["finish"],
            )
            unknown = await remote.call(
                "mathformer_skills_link_route_link",
                {
                    "context": vars(hub.RunContext()),
                    "registry": {},
                    "repository_root": str(root),
                },
            )
            self.assertEqual(
                unknown,
                {
                    "child": {
                        "ok": False,
                        "status": "unknown_action",
                        "action_id": ACTIONS[0],
                    }
                },
            )
        for forged in ["registry", "match", "cursor"]:
            inputs, changed = deepcopy(base), None
            inputs["context"]["dry_run"] = True
            if forged == "registry":
                inputs["registry"][ACTIONS[0]]["command"] = ["untrusted-command"]
            elif forged == "match":
                inputs["match"]["route"]["title"] = "untrusted title"
            else:
                changed = deepcopy(document)
                changed["flow"]["steps"][1]["body"]["steps"][0]["arguments"][
                    "state"
                ] = {"literal": {"ok": True, "children": [{}, {}]}}
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
        inputs = deepcopy(base)
        inputs["context"]["dry_run"] = True
        for limit in [1, 4, 7]:
            changed = deepcopy(document)
            changed["policy"]["limits"]["max_operation_calls"] = limit
            result = await run(inputs, changed)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertEqual(
                sum(bool(c.get("transport_call_performed")) for c in result["calls"]),
                limit,
            )
        changed = deepcopy(document)
        changed["flow"]["steps"][1]["until"] = {"literal": False}
        result = await run(inputs, changed)
        self.assertEqual(result["status"], "failed", result)
        self.assertIsNone(result["outputs"])
        self.assertEqual([c["operation"] for c in result["calls"]], ORDER[:-1])
        # A real service mount rejection fails before native publication.
        with tempfile.TemporaryDirectory() as directory:
            denied = Path(directory).resolve()
            populate(denied)
            inputs = deepcopy(base)
            inputs["repository_root"] = str(denied)
            result = await run(inputs)
            self.assertEqual(result["status"], "failed", result)
            self.assertIsNone(result["outputs"])
            self.assertFalse((denied / ".agents/skills").exists())
        # Only dry-run may refer to the production tree. Omitted/null mounts
        # must preserve the source default rather than inventing a new root.
        inputs = deepcopy(base)
        inputs["context"]["dry_run"] = True
        for omitted in [False, True]:
            inputs["repository_root"] = None
            if omitted:
                inputs.pop("repository_root")
            result = await run(inputs)
            expected = original().run_intent_match(
                selected_match(MATCH),
                checked_registry(REGISTRY),
                hub.RunContext(dry_run=True, allow_mutating=True),
            )
            self.assertEqual(result["outputs"], {"result": expected})


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False)
    result = program.result
    raise SystemExit(
        0 if result.wasSuccessful() and result.testsRun > len(result.skipped) else 1
    )

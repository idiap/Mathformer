# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Live native unittest cursor behind the normalized-contract workflow ports.

JSON carries a checked session reference and progress; unittest owns fixtures,
case objects, result tracebacks and cleanup in the server process.
"""

from dataclasses import asdict
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
import uuid
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context
from scripts.workflow_write_audit import FileState

ACTION = "control:normalized-workflows-tests"
SOURCE = (
    Path(__file__).resolve().parents[1] / "tests/control/test_normalized_workflows.py"
)


def source_suite():
    name = "_mathformer_normalized_workflow_tests"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, SOURCE)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class State(TypedDict):
    shared: dict
    remaining: list[str]
    results: list[dict]


class Prepared(TypedDict):
    boundary: dict
    execute: bool
    payload: dict


class Initialized(TypedDict):
    state: State
    runnable: bool


class Advanced(TypedDict):
    state: State
    done: bool


class Retained(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


class NormalizedTestTools:
    def __init__(self):
        self.sessions = {}

    def prepare(self, context, extra_args):
        b = hub.prepare_leaf_boundary(
            hub.build_registry()[ACTION], hub.RunContext(**context), extra_args
        )
        b["snapshot"] = {key: asdict(value) for key, value in b["snapshot"].items()}
        return {"boundary": b, "execute": b["execute"], "payload": b["payload"]}

    def initialize(self, boundary):
        if not boundary["execute"]:
            return {
                "state": {
                    "shared": {"session": "", "ready": False},
                    "remaining": [],
                    "results": [],
                },
                "runnable": False,
            }
        stdout, stderr = io.StringIO(), io.StringIO()
        runner = unittest.TextTestRunner(stream=stderr)
        result = runner._makeResult()
        result.startTestRun()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            cursor = source_suite().NormalizedCursor(result)
        if len(cursor.cases) > 12:
            cursor.close()
            raise ValueError("source discovery exceeds the declared twelve-test bound")
        token = uuid.uuid4().hex
        shared = {"session": token, "ready": cursor.ready}
        self.sessions[token] = dict(
            cursor=cursor,
            runner=runner,
            result=result,
            stdout=stdout,
            stderr=stderr,
            shared=shared,
        )
        return {
            "state": cursor.state(shared),
            "runnable": cursor.ready and bool(cursor.cases),
        }

    def current(self, state):
        session = self.sessions[state["shared"]["session"]]
        if state != session["cursor"].state(session["shared"]):
            raise ValueError("stale or modified suite state")
        return session

    def visit(self, state):
        session = self.current(state)
        with (
            contextlib.redirect_stdout(session["stdout"]),
            contextlib.redirect_stderr(session["stderr"]),
        ):
            cursor = session["cursor"]
            case = cursor.run_test()
            done = cursor.advance(case)
        return {
            "state": cursor.state(state["shared"]),
            "done": done or session["result"].shouldStop,
        }

    def retain(self, state):
        if state == {
            "shared": {"session": "", "ready": False},
            "remaining": [],
            "results": [],
        }:
            return {"state": state, "done": True}
        if self.current(state)["cursor"].ready:
            raise ValueError("suite is runnable")
        return {"state": state, "done": True}

    def finish(self, state, boundary):
        session = self.current(state)
        cursor, result = session["cursor"], session["result"]
        if cursor.ready and state["remaining"] and not result.shouldStop:
            raise ValueError("unconsumed tests")
        with (
            contextlib.redirect_stdout(session["stdout"]),
            contextlib.redirect_stderr(session["stderr"]),
        ):
            cursor.close()
            runner = session["runner"]
            runner._makeResult = lambda: result
            runner.run(lambda result: result)
        payload = dict(
            boundary["payload"],
            status="completed",
            returncode=0 if result.wasSuccessful() else 1,
            stdout=session["stdout"].getvalue(),
            stderr=session["stderr"].getvalue(),
            ok=result.wasSuccessful(),
        )
        del self.sessions[state["shared"]["session"]]
        b = {
            **boundary,
            "snapshot": {k: FileState(**v) for k, v in boundary["snapshot"].items()},
        }
        return {
            "result": hub.finish_leaf_boundary(hub.build_registry()[ACTION], b, payload)
        }


def register_normalized_test_tools(mcp):
    service = NormalizedTestTools()

    @mcp.tool()
    def mathformer_normalized_tests_prepare(
        context: Context, extra_args: list[str]
    ) -> Prepared:
        return service.prepare(context, extra_args)

    @mcp.tool()
    def mathformer_normalized_tests_early(payload: dict) -> Finished:
        return {"result": payload}

    @mcp.tool()
    def mathformer_normalized_tests_initialize(boundary: dict) -> Initialized:
        return service.initialize(boundary)

    @mcp.tool()
    def mathformer_normalized_tests_visit(state: State) -> Advanced:
        return service.visit(state)

    @mcp.tool()
    def mathformer_normalized_tests_retain(state: State) -> Retained:
        return service.retain(state)

    @mcp.tool()
    def mathformer_normalized_tests_finish(state: State, boundary: dict) -> Finished:
        return service.finish(state, boundary)

    return service

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged native adoption unittest tools. Sessions retain unittest's live fixture state."""

from dataclasses import asdict
from scripts.workflow_write_audit import FileState
import contextlib
import importlib.util
import io
import sys
import unittest
import uuid
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context

ACTION = "adoption:test-contracts"


def source_suite():
    name = "_mathformer_adoption_tests"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, hub.REPO_ROOT / "tests/control/test_portable_adoption.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


class Boundary(TypedDict):
    execute: bool
    payload: dict
    snapshot: dict


class State(TypedDict):
    shared: dict
    remaining: list[str]
    results: list[dict]


class Prepared(TypedDict):
    boundary: Boundary


class Initialized(TypedDict):
    state: State
    ready: bool


class Tested(TypedDict):
    test: dict


class Advanced(TypedDict):
    state: State
    done: bool


class Stateful(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


class AdoptionTestTools:
    def __init__(self):
        self.sessions = {}

    def current(self, state):
        session = self.sessions[state["shared"]["session"]]
        if session["cursor"].state(state["shared"]) != state:
            raise ValueError("stale or modified suite state")
        return session

    def prepare(self, context):
        boundary = hub.prepare_leaf_boundary(
            hub.build_registry()[ACTION], hub.RunContext(**context), ()
        )
        boundary["snapshot"] = {
            key: asdict(value) for key, value in boundary["snapshot"].items()
        }
        return {"boundary": boundary}

    def initialize(self, boundary):
        if not boundary["execute"]:
            return {
                "state": {
                    "shared": {"session": "", "ready": False},
                    "remaining": [],
                    "results": [],
                },
                "ready": False,
            }
        stdout, stderr = io.StringIO(), io.StringIO()
        runner = unittest.TextTestRunner(stream=stderr)
        result = runner._makeResult()
        result.startTestRun()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            cursor = source_suite().AdoptionCursor(result)
        token = uuid.uuid4().hex
        self.sessions[token] = dict(
            cursor=cursor, runner=runner, result=result, stdout=stdout, stderr=stderr
        )
        return {
            "state": cursor.state({"session": token, "ready": cursor.ready}),
            "ready": cursor.ready,
        }

    def run(self, state):
        session = self.current(state)
        if "pending" in session:
            raise ValueError("current test already executed")
        with (
            contextlib.redirect_stdout(session["stdout"]),
            contextlib.redirect_stderr(session["stderr"]),
        ):
            test = session["cursor"].run_test()
        session["pending"] = test
        return {"test": test}

    def advance(self, state, test):
        session = self.current(state)
        if test != session.pop("pending"):
            raise ValueError("test result mismatch")
        done = session["cursor"].advance(test)
        return {"state": session["cursor"].state(state["shared"]), "done": done}

    def setup_failed(self, state):
        if state["shared"]["session"] == "":
            if state != {
                "shared": {"session": "", "ready": False},
                "remaining": [],
                "results": [],
            }:
                raise ValueError("invalid early state")
            return {"state": state, "done": True}
        if self.current(state)["cursor"].ready:
            raise ValueError("class setup succeeded")
        return {"state": state, "done": True}

    def finish(self, boundary, state):
        session = self.current(state)
        cursor = session["cursor"]
        if cursor.ready and state["remaining"]:
            raise ValueError("suite still has unconsumed tests")
        with (
            contextlib.redirect_stdout(session["stdout"]),
            contextlib.redirect_stderr(session["stderr"]),
        ):
            cursor.close()
            # Native runner renders the accumulated TestResult and its summary.
            runner = session["runner"]
            runner._makeResult = lambda: session["result"]
            runner.run(lambda result: result)
        payload = dict(
            boundary["payload"],
            status="completed",
            returncode=0 if session["result"].wasSuccessful() else 1,
            stdout=session["stdout"].getvalue(),
            stderr=session["stderr"].getvalue(),
            ok=session["result"].wasSuccessful(),
        )
        del self.sessions[state["shared"]["session"]]
        native_boundary = {
            **boundary,
            "snapshot": {
                key: FileState(**value) for key, value in boundary["snapshot"].items()
            },
        }
        return {
            "result": hub.finish_leaf_boundary(
                hub.build_registry()[ACTION], native_boundary, payload
            )
        }


def register_adoption_test_contracts_tools(mcp):
    service = AdoptionTestTools()

    @mcp.tool()
    def mathformer_adoption_tests_prepare(context: Context) -> Prepared:
        return service.prepare(context)

    @mcp.tool()
    def mathformer_adoption_tests_early(boundary: Boundary) -> Finished:
        if boundary["execute"]:
            raise ValueError("boundary requires execution")
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_adoption_tests_initialize(boundary: Boundary) -> Initialized:
        return service.initialize(boundary)

    @mcp.tool()
    def mathformer_adoption_tests_run(state: State) -> Tested:
        return service.run(state)

    @mcp.tool()
    def mathformer_adoption_tests_advance(state: State, test: dict) -> Advanced:
        return service.advance(state, test)

    @mcp.tool()
    def mathformer_adoption_tests_setup_failed(state: State) -> Stateful:
        return service.setup_failed(state)

    @mcp.tool()
    def mathformer_adoption_tests_finish(boundary: Boundary, state: State) -> Finished:
        return service.finish(boundary, state)

    return service

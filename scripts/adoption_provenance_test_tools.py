# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Real staged provenance suite subprocess, retaining native hub boundaries."""

import atexit
from copy import deepcopy
from dataclasses import asdict
import json
import subprocess
import tempfile
import uuid
from typing import Literal
from typing_extensions import TypedDict
import mathformer as hub
from adoption_check_tools import Context

ACTION = "adoption:test-provenance"


class Boundary(TypedDict):
    session: str
    execute: bool
    payload: dict
    snapshot: dict


class State(TypedDict):
    session: str
    index: int
    tests: list[str]
    tests_run: int
    failures: int
    errors: int


class Observation(TypedDict):
    status: Literal["passed", "failure", "error"]
    diagnostics: list[str]


class Prepared(TypedDict):
    boundary: Boundary
    execute: bool


class Initialized(TypedDict):
    state: State


class Tested(TypedDict):
    observation: Observation


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    result: dict


class ProvenanceTestTools:
    def __init__(self):
        self.sessions = {}
        atexit.register(self.close)

    def close(self):
        for session in self.sessions.values():
            process = session.get("process")
            if process:
                if process.poll() is None:
                    process.terminate()
                process.wait()
                process.stdin.close()
                process.stdout.close()
                session["stderr"].close()
        self.sessions.clear()

    def prepare(self, context, extra_args=()):
        item = hub.build_registry()[ACTION]
        boundary = hub.prepare_leaf_boundary(
            item, hub.RunContext(**context), extra_args
        )
        token = uuid.uuid4().hex
        public = {
            **boundary,
            "session": token,
            "snapshot": {
                key: asdict(value) for key, value in boundary["snapshot"].items()
            },
        }
        self.sessions[token] = {
            "boundary": deepcopy(public),
            "native": boundary,
            "item": item,
        }
        return {"boundary": public, "execute": boundary["execute"]}

    def boundary_session(self, boundary):
        session = self.sessions[boundary["session"]]
        if session["boundary"] != boundary:
            raise ValueError("modified boundary")
        return session

    def early(self, boundary):
        self.boundary_session(boundary)
        if boundary["execute"]:
            raise ValueError("boundary requires execution")
        del self.sessions[boundary["session"]]
        return {"result": boundary["payload"]}

    def receive(self, session):
        line = session["process"].stdout.readline()
        if not line:
            raise RuntimeError(
                "native provenance subprocess stopped before protocol completion"
            )
        return json.loads(line)

    def initialize(self, boundary):
        session = self.boundary_session(boundary)
        if "state" in session:
            raise ValueError("suite already initialized")
        if not boundary["execute"]:
            state = {
                "session": boundary["session"],
                "index": 0,
                "tests": [],
                "tests_run": 0,
                "failures": 0,
                "errors": 0,
            }
            session["state"] = deepcopy(state)
            return {"state": state}
        stderr = tempfile.TemporaryFile(mode="w+t")
        session["stderr"] = stderr
        session["process"] = subprocess.Popen(
            boundary["payload"]["argv"] + ["--workflow-protocol"],
            cwd=hub.REPO_ROOT,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        state = {**self.receive(session)["state"], "session": boundary["session"]}
        session["state"] = deepcopy(state)
        return {"state": state}

    def current(self, state):
        session = self.sessions[state["session"]]
        if session.get("state") != state:
            raise ValueError("stale or modified suite state")
        return session

    def send(self, session, value):
        session["process"].stdin.write(json.dumps(value) + "\n")
        session["process"].stdin.flush()
        return self.receive(session)

    def run_case(self, state):
        session = self.current(state)
        if "pending" in session or state["index"] >= len(state["tests"]):
            raise ValueError("case already executed or suite complete")
        response = self.send(session, {"operation": "run_case"})
        session["pending"] = deepcopy(response["observation"])
        return response

    def advance(self, state, observation):
        session = self.current(state)
        if session.get("pending") != observation:
            raise ValueError("missing or mismatched observation")
        response = self.send(
            session, {"operation": "advance", "observation": observation}
        )
        del session["pending"]
        response["state"]["session"] = state["session"]
        session["state"] = deepcopy(response["state"])
        return response

    def inactive(self, state):
        session = self.current(state)
        if session["boundary"]["execute"]:
            raise ValueError("suite requires execution")
        return {"state": state, "done": True}

    def finish(self, boundary, state):
        session = self.current(state)
        if session is not self.boundary_session(boundary):
            raise ValueError("cross-invocation boundary")
        if state["index"] != len(state["tests"]) or "pending" in session:
            raise ValueError("suite incomplete")
        completion = self.receive(session)
        process = session["process"]
        returncode = process.wait()
        process.stdin.close()
        process.stdout.close()
        session["stderr"].seek(0)
        stderr = session["stderr"].read()
        session["stderr"].close()
        payload = dict(
            boundary["payload"],
            status="completed",
            returncode=returncode,
            stdout=completion["stdout"],
            stderr=stderr,
            ok=returncode == 0,
        )
        del self.sessions[state["session"]]
        return {
            "result": hub.finish_leaf_boundary(
                session["item"], session["native"], payload
            )
        }


def register_provenance_test_tools(mcp):
    service = ProvenanceTestTools()

    @mcp.tool()
    def mathformer_provenance_tests_prepare(
        context: Context, extra_args: list[str] = []
    ) -> Prepared:
        return service.prepare(context, extra_args)

    @mcp.tool()
    def mathformer_provenance_tests_initialize(boundary: Boundary) -> Initialized:
        return service.initialize(boundary)

    @mcp.tool()
    def mathformer_provenance_tests_run_case(state: State) -> Tested:
        return service.run_case(state)

    @mcp.tool()
    def mathformer_provenance_tests_advance(
        state: State, observation: Observation
    ) -> Advanced:
        return service.advance(state, observation)

    @mcp.tool()
    def mathformer_provenance_tests_inactive(state: State) -> Advanced:
        return service.inactive(state)

    @mcp.tool()
    def mathformer_provenance_tests_finish(
        boundary: Boundary, state: State
    ) -> Finished:
        return service.finish(boundary, state)

    @mcp.tool()
    def mathformer_provenance_tests_early(boundary: Boundary) -> Finished:
        return service.early(boundary)

    return service

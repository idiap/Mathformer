# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Private staged transport for the native controlled SymPy subprocess.

The native command, interpreter, CLI, case functions, output streams, exit code,
preflight and write audit are retained. A channel lifetime is one admitted
attempt, not a checkpoint. Native workflow definitions are not interpreted here.
"""

import json
import atexit
import os
from pathlib import Path
import secrets
import socket
import subprocess
from typing_extensions import TypedDict, NotRequired

import mathformer as hub
from adoption_check_tools import Context

ROUTE = "formalize.physics.sympy"
ACTION = "physics-sympy:controlled"
OUTPUT = "artifacts/physics_sympy/controlled_suite"
PREFIX = "mathformer_sympy_controlled_"


class State(TypedDict):
    ok: bool
    children: list[dict]


class Suite(TypedDict):
    cases: list[dict]
    token: str


class ProcessError(TypedDict):
    kind: str
    message: NotRequired[str]


class Initialized(TypedDict):
    state: State


class Prepared(TypedDict):
    boundary: dict
    suite: Suite
    entered: bool


class Processed(TypedDict):
    suite: Suite
    done: bool
    error: ProcessError


class Finished(TypedDict):
    result: dict


class Advanced(TypedDict):
    state: State
    done: bool


def selected_match(metadata):
    route = next(r for r in hub.build_intent_routes() if r.route_id == ROUTE)
    if route.action_ids != (ACTION,):
        raise ValueError("native route changed; requalify controlled binding")
    return hub.IntentMatch(route, metadata["score"], tuple(metadata["matched_terms"]))


def item():
    action = hub.build_registry()[ACTION]
    if (
        action.depends_on
        or action.timeout_seconds is not None
        or tuple(action.command)[1:]
        != ("tests/physics_sympy/run_controlled_suite.py", "--json")
    ):
        raise ValueError("native action changed; requalify controlled binding")
    return action


def check_state(state, *, finishing=False):
    count = len(state["children"])
    if count != int(finishing):
        raise ValueError("route already exhausted" if count else "unconsumed route")
    if state["ok"] != all(bool(c.get("ok", False)) for c in state["children"]):
        raise ValueError("inconsistent sticky route success")


class Attempt:
    """One native process and one private control channel, with no retry."""

    def __init__(self, root, boundary):
        self.root, self.boundary, self.cases = root, boundary, []
        self.error = {"kind": "none"}
        parent, child = socket.socketpair()
        environment = dict(
            os.environ, MATHFORMER_CONTROLLED_STAGE_FD=str(child.fileno())
        )
        try:
            self.process = subprocess.Popen(
                boundary["payload"]["argv"],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                pass_fds=(child.fileno(),),
            )
        except BaseException:
            parent.close()
            raise
        finally:
            child.close()
        self.socket = parent
        self.channel = parent.makefile("rw", encoding="utf-8")
        # Drain native output while the process waits between stages. Keeping
        # stdout separate from protocol messages preserves arbitrary diagnostics.
        from threading import Thread

        self.captured = {}

        def drain(name, stream):
            self.captured[name] = stream.read()
            stream.close()

        self.readers = [
            Thread(target=drain, args=(name, stream), daemon=True)
            for name, stream in [
                ("stdout", self.process.stdout),
                ("stderr", self.process.stderr),
            ]
        ]
        for reader in self.readers:
            reader.start()

    def receive(self):
        line = self.channel.readline()
        if not line:
            self.error = {
                "kind": "unhandled_exception",
                "message": "native process ended before stage response",
            }
            return {"error": self.error}
        result = json.loads(line)
        self.error = result.get("error", {"kind": "none"})
        if "cases" in result:
            self.cases = result["cases"]
        return result

    def send(self, command):
        self.channel.write(json.dumps(command) + "\n")
        self.channel.flush()

    def complete(self):
        try:
            self.process.wait()  # Native action has no configured timeout.
            for reader in self.readers:
                reader.join()
            payload = hub.complete_leaf_boundary(
                dict(self.boundary["payload"]),
                self.process.returncode,
                self.captured["stdout"],
                self.captured["stderr"],
            )
            return hub.finish_leaf_boundary(
                item(), self.boundary, payload, repository_root=self.root
            )
        finally:
            self.channel.close()
            self.socket.close()


def register_physics_sympy_controlled_route_tools(mcp, authorize, path_allowed):
    attempts = {}

    def close_pending():
        # Closing the private channel tells the native CLI to abort. Incomplete
        # runs never finalize the suite. There is no durable continuation token.
        for attempt in list(attempts.values()):
            attempt.channel.close()
            attempt.socket.close()
            attempt.complete()
        attempts.clear()

    atexit.register(close_pending)

    def early(boundary):
        # Required transport sentinel: entered=false prevents its consumption.
        # It does not claim that native suite initialization ran.
        return {
            "boundary": boundary,
            "suite": {"cases": [], "token": ""},
            "entered": False,
        }

    def root_for(repository_root, writing=False):
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        if writing:
            authorize()
            if not path_allowed(root / OUTPUT):
                raise ValueError("controlled suite outside configured service roots")
        return root

    def active(suite, repository_root):
        root = root_for(repository_root, writing=True)
        attempt = attempts[suite["token"]]
        if attempt.root != root or attempt.cases != suite["cases"]:
            raise ValueError(
                "suite state differs from native process history or repository context"
            )
        return attempt

    @mcp.tool()
    def mathformer_sympy_controlled_initialize_route() -> Initialized:
        return {"state": hub.initialize_intent_state()}

    @mcp.tool()
    def mathformer_sympy_controlled_prepare_attempt(
        state: State, context: Context, repository_root: str | None
    ) -> Prepared:
        check_state(state)
        selected_match({"score": 0, "matched_terms": []})
        root = root_for(repository_root, writing=not context["dry_run"])
        admission = hub.prepare_action(
            ACTION,
            hub.build_registry(),
            hub.RunContext(**context),
            repository_root=root,
        )
        if admission:
            raise ValueError("unexpected dependency or admission state")
        boundary = hub.prepare_leaf_boundary(
            item(), hub.RunContext(**context), (), repository_root=root
        )
        if not boundary["execute"]:
            return early(boundary)
        attempt = Attempt(root, boundary)
        response = attempt.receive()
        if "error" in response:
            return early({"execute": False, "payload": attempt.complete()})
        token = secrets.token_hex(24)
        attempts[token] = attempt
        return {
            "boundary": {"execute": True, "token": token},
            "suite": {"cases": attempt.cases, "token": token},
            "entered": True,
        }

    @mcp.tool()
    def mathformer_sympy_controlled_process_case(
        suite: Suite, repository_root: str | None
    ) -> Processed:
        attempt = active(suite, repository_root)
        if len(suite["cases"]) >= 8 or attempt.error["kind"] != "none":
            raise ValueError("controlled case traversal exhausted or aborted")
        attempt.send("step")
        response = attempt.receive()
        return {
            "suite": {"cases": attempt.cases, "token": suite["token"]},
            "done": response.get("done", True),
            "error": attempt.error,
        }

    @mcp.tool()
    def mathformer_sympy_controlled_finish_suite(
        suite: Suite, error: ProcessError, boundary: dict, repository_root: str | None
    ) -> Finished:
        attempt = active(suite, repository_root)
        if (
            boundary != {"execute": True, "token": suite["token"]}
            or error != attempt.error
        ):
            raise ValueError("boundary or error differs from native process")
        if error["kind"] == "none":
            if len(suite["cases"]) != 8:
                raise ValueError("unconsumed controlled cases")
            attempt.send("finish")
        try:
            return {"result": attempt.complete()}
        finally:
            attempts.pop(suite["token"])

    @mcp.tool()
    def mathformer_sympy_controlled_return_early(boundary: dict) -> Finished:
        if boundary["execute"]:
            raise ValueError("suite has not completed")
        return {"result": boundary["payload"]}

    @mcp.tool()
    def mathformer_sympy_controlled_advance_route(
        state: State, child: dict, context: Context
    ) -> Advanced:
        check_state(state)
        state, done = hub.advance_intent_state(
            state, child, hub.RunContext(**context), 1
        )
        return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_sympy_controlled_finish_route(state: State, match: dict) -> Finished:
        check_state(state, finishing=True)
        return {
            "result": hub.finish_intent_state(
                state, selected_match(match), hub.build_registry()
            )
        }

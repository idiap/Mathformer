# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned native physics_lean continuations with the hub's process deadline.

The worker calls the same functions as run/main. Transported states, reports and
boundaries are assertions only. Neither matrix commands nor CLI arguments can
be supplied through the staged ports.
"""

import atexit
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import inspect
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
import traceback
from uuid import uuid4
from typing_extensions import TypedDict

import mathformer as hub
from comprehensive_strict_tools import source_runner

ACTION = "test:family:physics-lean"
SCOPE = dict(
    matrix="tests/test_matrix.json",
    sha256="17b2fc38f51c7711873b68dc5f630cfc0eb06351160ad6401ea67a6044ace322",
    selected_count=11,
)
PORTS = {
    "prepare_boundary": (
        ["context", "extra_args"],
        {"boundary": dict, "execute": bool, "runtime": dict},
    ),
    "return_boundary": (["boundary", "runtime"], {"result": dict}),
    "prepare_checks": (["scope", "boundary", "runtime"], {"progress": dict}),
    "checks_pending": (["progress", "runtime"], {"progress": dict, "pending": bool}),
    "retain_state": (["progress", "runtime"], {"progress": dict, "pending": bool}),
    "bypass_progress": (["boundary", "runtime"], {"progress": dict}),
    "advance_check": (["progress", "runtime"], {"progress": dict}),
    "finalize_checks": (["progress", "runtime"], {"report": dict, "terminated": bool}),
    "publish_and_audit": (["report", "boundary", "runtime"], {"result": dict}),
    "complete_failure": (["boundary", "runtime"], {"result": dict}),
}


def _worker(pipe, stdout_path, stderr_path):
    """Native source steps in one isolated process; exceptions end that process."""
    with (
        open(stdout_path, "w", buffering=1) as output,
        open(stderr_path, "w", buffering=1) as errors,
    ):
        try:
            with redirect_stdout(output), redirect_stderr(errors):
                native = source_runner()
                args = native.parse_args(["--module-family", "physics_lean", "--json"])
                while True:
                    operation = pipe.recv()
                    if operation == "prepare_checks":
                        if native.enter_checks(args):
                            raise ValueError(
                                "fixed invocation unexpectedly selected snapshot-only"
                            )
                        state = native.prepare_checks(args)
                        if len(state["selected"]) > 11:
                            raise ValueError(
                                "physics_lean selection exceeds contract bound of 11"
                            )
                        value = state
                    elif operation == "checks_pending":
                        value = native.checks_pending(state)
                    elif operation == "advance_check":
                        state = native.advance_check(state, args)
                        value = state
                    elif operation == "finalize_checks":
                        report = native.finalize_checks(state, args)
                        value = report
                    elif operation == "publish_and_audit":
                        code = native.publish_report(report, args)
                        output.flush()
                        errors.flush()
                        pipe.send(("finished", code))
                        return
                    else:
                        raise ValueError("unknown native physics_lean stage")
                    output.flush()
                    errors.flush()
                    pipe.send(("ok", value))
        except BaseException:
            traceback.print_exc(file=errors)
            errors.flush()
            output.flush()
            pipe.send(("finished", 1))
            raise SystemExit(1)
        finally:
            pipe.close()


class PhysicsLeanFamilyTools:
    def __init__(self, authorize=lambda: None, path_allowed=lambda path: True):
        self.authorize, self.path_allowed = authorize, path_allowed
        self.sessions = {}
        self.lock = threading.RLock()
        atexit.register(self.close)

    def drop(self, token):
        scope = self.sessions.pop(token, None)
        if scope and "process" in scope:
            scope["timer"].cancel()
            if scope["process"].is_alive():
                scope["process"].terminate()
            scope["process"].join(timeout=2)
            scope["pipe"].close()
            scope["scratch"].cleanup()

    def close(self):
        for token in list(self.sessions):
            self.drop(token)

    def start(self, scope):
        """Start the native cumulative 900-second deadline, including pauses."""
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe()
        scratch = tempfile.TemporaryDirectory(prefix="mathformer-physics-lean-")
        out, err = Path(scratch.name) / "stdout", Path(scratch.name) / "stderr"
        out.touch()
        err.touch()
        process = ctx.Process(
            target=_worker, args=(child, str(out), str(err)), daemon=True
        )
        deadline = time.monotonic() + scope["item"].timeout_seconds
        scope.update(
            process=process,
            pipe=parent,
            scratch=scratch,
            stdout=out,
            stderr=err,
            deadline=deadline,
            timed_out=False,
        )

        def interrupt():
            scope["timed_out"] = True
            if process.is_alive():
                process.terminate()

        timer = threading.Timer(max(0, deadline - time.monotonic()), interrupt)
        timer.daemon = True
        scope["timer"] = timer
        process.start()
        child.close()
        timer.start()

    def receive(self, scope, operation):
        """Capture process exits/timeouts as native hub outcomes, not fake reports."""
        if "terminal" in scope:
            return None
        try:
            if scope["timed_out"] or time.monotonic() >= scope["deadline"]:
                raise TimeoutError
            scope["pipe"].send(operation)
            if not scope["pipe"].poll(max(0, scope["deadline"] - time.monotonic())):
                raise TimeoutError
            message = scope["pipe"].recv()
            if message[0] == "ok":
                return message[1]
            scope["terminal"] = dict(status="completed", returncode=message[1])
        except (TimeoutError, EOFError, BrokenPipeError, ConnectionResetError):
            timeout = scope["timed_out"] or time.monotonic() >= scope["deadline"]
            scope["terminal"] = dict(
                status="timeout" if timeout else "completed",
                returncode=None if timeout else 1,
            )
        return None

    def finish(self, token, scope):
        scope["timer"].cancel()
        process = scope["process"]
        if scope["terminal"]["status"] == "timeout" and process.is_alive():
            process.terminate()
        process.join(timeout=2)
        stdout, stderr = scope["stdout"].read_text(), scope["stderr"].read_text()
        payload = hub.complete_leaf_boundary(
            deepcopy(scope["native"]["payload"]),
            scope["terminal"]["returncode"],
            stdout,
            stderr,
        )
        if scope["terminal"]["status"] == "timeout":
            payload.update(
                status="timeout",
                ok=False,
                timeout_seconds=scope["item"].timeout_seconds,
            )
        try:
            return {
                "result": hub.finish_leaf_boundary(
                    scope["item"],
                    scope["native"],
                    payload,
                    repository_root=scope["root"],
                )
            }
        finally:
            self.drop(token)

    def call(self, operation, values):
        self.authorize()
        native = source_runner()
        if not self.path_allowed(native.ARTIFACT_ROOT):
            raise PermissionError("physics_lean artifacts outside service write roots")
        if operation == "prepare_boundary":
            item = hub.build_registry()[ACTION]
            root = native.REPO_ROOT
            boundary = hub.prepare_leaf_boundary(
                item,
                hub.RunContext(**values["context"]),
                values["extra_args"],
                repository_root=root,
            )
            # Snapshots stay server-owned (FileState objects are not JSON ports).
            public = {k: deepcopy(v) for k, v in boundary.items() if k != "snapshot"}
            public["snapshot"] = {}
            token = uuid4().hex
            self.sessions[token] = dict(
                native=boundary,
                public=deepcopy(public),
                item=item,
                root=root,
                phase="prepare_checks" if boundary["execute"] else "return_boundary",
            )
            return dict(
                boundary=public, execute=boundary["execute"], runtime={"handle": token}
            )
        token = values["runtime"].get("handle")
        scope = self.sessions.get(token)
        if scope is None or values["runtime"] != {"handle": token}:
            raise ValueError("unknown or consumed physics_lean context")
        if operation != scope["phase"] and not (
            operation == "retain_state"
            and scope["phase"]
            in ("finalize_checks", "complete_failure", "return_boundary")
            or operation == "bypass_progress"
            and scope["phase"] == "return_boundary"
        ):
            raise ValueError("out-of-order physics_lean stage")
        for name, key in [
            ("boundary", "public"),
            ("progress", "progress"),
            ("report", "report"),
        ]:
            if name in values and values[name] != scope.get(key):
                raise ValueError("modified or replayed physics_lean " + name)
        if operation == "return_boundary":
            self.sessions.pop(token)
            return {"result": deepcopy(scope["native"]["payload"])}
        if operation == "bypass_progress":
            progress = dict(
                state=dict(
                    matrix=[],
                    selected=[],
                    families=["physics_lean"],
                    index=0,
                    results=[],
                ),
                pending=False,
                terminated=False,
            )
            scope["progress"] = deepcopy(progress)
            return {"progress": progress}
        if operation == "prepare_checks":
            if values["scope"] != SCOPE:
                raise ValueError(
                    "scope must assert the registered physics_lean projection"
                )
            try:
                self.start(scope)
                state = self.receive(scope, operation)
                if state is not None:
                    for row in state["selected"]:
                        for path in row.get("write_set") or ():
                            if not self.path_allowed((scope["root"] / path).resolve()):
                                raise PermissionError(
                                    "physics_lean check writes outside service write roots"
                                )
                else:
                    state = dict(
                        matrix=[],
                        selected=[],
                        families=["physics_lean"],
                        index=0,
                        results=[],
                    )
                progress = dict(
                    state=state, pending=False, terminated="terminal" in scope
                )
                scope.update(progress=deepcopy(progress), phase="checks_pending")
                return {"progress": progress}
            except BaseException:
                self.drop(token)
                raise
        if operation == "checks_pending":
            pending = self.receive(scope, operation)
            progress = {
                **scope["progress"],
                "pending": bool(pending),
                "terminated": "terminal" in scope,
            }
            scope.update(
                progress=deepcopy(progress),
                phase=(
                    "advance_check"
                    if pending
                    else (
                        "complete_failure"
                        if progress["terminated"]
                        else "finalize_checks"
                    )
                ),
            )
            return dict(progress=progress, pending=bool(pending))
        if operation == "retain_state":
            if scope["progress"]["pending"] or (
                scope["phase"] == "finalize_checks"
                and (
                    scope["progress"]["state"]["selected"]
                    or scope["progress"]["state"]["results"]
                    or scope["progress"]["state"]["index"]
                )
            ):
                raise ValueError(
                    "retain_state requires an empty or terminated traversal"
                )
            return {"progress": deepcopy(scope["progress"]), "pending": False}
        if operation == "advance_check":
            state = self.receive(scope, operation)
            progress = dict(
                state=state if state is not None else scope["progress"]["state"],
                pending=False,
                terminated="terminal" in scope,
            )
            scope.update(progress=deepcopy(progress), phase="checks_pending")
            return {"progress": progress}
        if operation == "finalize_checks":
            report = self.receive(scope, operation)
            scope.update(
                report=deepcopy(report or {}),
                phase=(
                    "complete_failure" if "terminal" in scope else "publish_and_audit"
                ),
            )
            return dict(report=report or {}, terminated="terminal" in scope)
        if operation == "publish_and_audit":
            self.receive(scope, operation)
        return self.finish(token, scope)


def register_physics_lean_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    service = PhysicsLeanFamilyTools(authorize, path_allowed)
    for operation, (inputs, outputs) in PORTS.items():
        result_type = TypedDict("PhysicsLean_" + operation, outputs)

        def make(op, names, output):
            def invoke(**kwargs):
                with service.lock:
                    return service.call(op, kwargs)

            invoke.__name__ = "mathformer_physics_lean_family_" + op
            annotations = {
                name: list[str] if name == "extra_args" else dict for name in names
            }
            invoke.__signature__ = inspect.Signature(
                [
                    inspect.Parameter(
                        name,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                        annotation=annotations[name],
                    )
                    for name in names
                ],
                return_annotation=output,
            )
            invoke.__annotations__ = {**annotations, "return": output}
            return invoke

        mcp.tool()(make(operation, inputs, result_type))
    return service

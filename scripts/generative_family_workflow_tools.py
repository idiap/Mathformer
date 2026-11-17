# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Owned generative matrix continuations inside the native hub process boundary.

The worker invokes shared source steps, retaining parser defaults and history.
The cumulative native deadline includes pauses between MCP calls. No transported
arguments, matrix commands, or reports are used as execution authority.
"""

import atexit
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import inspect
import io
import multiprocessing
from pathlib import Path
import threading
import time
import traceback
from uuid import uuid4
from typing_extensions import TypedDict
import mathformer as hub
from comprehensive_strict_tools import source_runner

ACTION = "test:family:generative"
DOMAIN = {
    "max_selected_rows": 4096,
    "restriction": "canonical generative selection has at most 4096 rows",
}
PORTS = {
    "enter": (
        ["context", "domain"],
        {"proceed": bool, "args": dict, "result": dict, "runtime": dict},
    ),
    "prepare": (["args", "domain", "runtime"], {"state": dict, "done": bool}),
    "advance": (["state", "args", "runtime"], {"state": dict, "done": bool}),
    "retain": (["state", "runtime"], {"state": dict, "done": bool}),
    "bypass": (["runtime"], {"state": dict, "done": bool}),
    "finalize": (["state", "args", "runtime"], {"report": dict}),
    "publish": (["report", "args", "context", "runtime"], {"result": dict}),
    "stop": (["result", "runtime"], {"result": dict}),
}


def _worker(pipe):
    output, errors = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(output), redirect_stderr(errors):
            native = source_runner()
            args = native.parse_args(["--module-family", "generative", "--json"])
            projected = {
                k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
            }
            pipe.send(("ok", projected))
            while True:
                op = pipe.recv()
                if op == "prepare":
                    native.ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
                    state = native.prepare_checks(args)
                    if len(state["selected"]) > 4096:
                        raise ValueError(
                            "generative selection exceeds contract bound of 4096"
                        )
                    value = state
                elif op == "advance":
                    state = native.advance_check(state, args)
                    value = state
                elif op == "finalize":
                    report = native.finalize_checks(state, args)
                    value = report
                elif op == "publish":
                    code = native.publish_report(report, args)
                    pipe.send(("finished", code, output.getvalue(), errors.getvalue()))
                    return
                else:
                    raise ValueError("unknown native stage")
                pipe.send(("ok", value))
    except BaseException:
        pipe.send(
            ("error", traceback.format_exc(), output.getvalue(), errors.getvalue())
        )
    finally:
        pipe.close()


class GenerativeTools:
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

    def close(self):
        for token in list(self.sessions):
            self.drop(token)

    def receive(self, scope, command=None):
        if command:
            scope["pipe"].send(command)
        if not scope["pipe"].poll(max(0, scope["deadline"] - time.monotonic())):
            raise TimeoutError("native generative hub deadline exceeded (900 seconds)")
        message = scope["pipe"].recv()
        if message[0] == "error":
            raise RuntimeError(message[1])
        return message

    def call(self, op, values):
        self.authorize()
        if not self.path_allowed(source_runner().ARTIFACT_ROOT):
            raise ValueError("generative artifacts outside service write roots")
        if op == "enter":
            if values["domain"] != DOMAIN:
                raise ValueError("invalid generative domain")
            item = hub.build_registry()[ACTION]
            boundary = hub.prepare_leaf_boundary(
                item, hub.RunContext(**values["context"]), ()
            )
            token = uuid4().hex
            scope = dict(
                item=item,
                boundary=boundary,
                context=deepcopy(values["context"]),
                phase="prepare" if boundary["execute"] else "stop",
                args={},
            )
            self.sessions[token] = scope
            try:
                if boundary["execute"]:
                    ctx = multiprocessing.get_context("spawn")
                    parent, child = ctx.Pipe()
                    process = ctx.Process(target=_worker, args=(child,), daemon=True)
                    deadline = time.monotonic() + item.timeout_seconds
                    process.start()
                    child.close()
                    timer = threading.Timer(
                        max(0, deadline - time.monotonic()), process.terminate
                    )
                    timer.daemon = True
                    scope.update(
                        process=process, pipe=parent, timer=timer, deadline=deadline
                    )
                    timer.start()
                    scope["args"] = self.receive(scope)[1]
                else:
                    # All ports are required, including on the unselected execute branch.
                    parsed = source_runner().parse_args(
                        ["--module-family", "generative", "--json"]
                    )
                    scope["args"] = {
                        k: str(v) if isinstance(v, Path) else v
                        for k, v in vars(parsed).items()
                    }
                return dict(
                    proceed=boundary["execute"],
                    args=deepcopy(scope["args"]),
                    result=deepcopy(boundary["payload"]),
                    runtime={"handle": token},
                )
            except BaseException:
                self.drop(token)
                raise
        token = values["runtime"]["handle"]
        scope = self.sessions.get(token)
        try:
            if (
                scope is None
                or values["runtime"] != {"handle": token}
                or (
                    scope["phase"] != op
                    and not (op in ("bypass", "retain") and scope["phase"] == "stop")
                )
            ):
                raise ValueError("unknown, consumed or out-of-order generative context")
            for name in ("args", "state", "report", "context"):
                if name in values and values[name] != scope.get(name):
                    raise ValueError("modified or replayed generative " + name)
            if op == "bypass":
                state = dict(matrix=[], selected=[], families=[], index=0, results=[])
                scope["state"] = deepcopy(state)
                return {"state": state, "done": True}
            if op == "stop":
                if values["result"] != scope["boundary"]["payload"]:
                    raise ValueError("modified stopped result")
                result = deepcopy(values["result"])
                self.drop(token)
                return {"result": result}
            if op == "retain":
                if scope["state"]["selected"]:
                    raise ValueError("retain requires empty selection")
                if scope["phase"] != "stop":
                    scope["phase"] = "finalize"
                return {"state": deepcopy(scope["state"]), "done": True}
            if op == "prepare" and values["domain"] != DOMAIN:
                raise ValueError("modified generative domain")
            message = self.receive(scope, op)
            if op in ("prepare", "advance"):
                state = message[1]
                done = state["index"] == len(state["selected"])
                scope.update(
                    state=deepcopy(state),
                    phase=(
                        ("retain" if op == "prepare" and done else "finalize")
                        if done
                        else "advance"
                    ),
                )
                return {"state": state, "done": done}
            if op == "finalize":
                scope.update(report=deepcopy(message[1]), phase="publish")
                return {"report": message[1]}
            _, code, stdout, stderr = message
            payload = hub.complete_leaf_boundary(
                deepcopy(scope["boundary"]["payload"]), code, stdout, stderr
            )
            result = hub.finish_leaf_boundary(scope["item"], scope["boundary"], payload)
            self.drop(token)
            return {"result": result}
        except BaseException:
            self.drop(token)
            raise


def register_generative_family_tools(
    mcp, authorize=lambda: None, path_allowed=lambda path: True
):
    service = GenerativeTools(authorize, path_allowed)
    for operation, (inputs, outputs) in PORTS.items():
        result_type = TypedDict("Generative_" + operation, outputs)

        def make(op, names, output):
            def invoke(**kwargs):
                with service.lock:
                    return service.call(op, kwargs)

            invoke.__name__ = "mathformer_generative_family_" + op
            invoke.__signature__ = inspect.Signature(
                [
                    inspect.Parameter(
                        name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=dict
                    )
                    for name in names
                ],
                return_annotation=output,
            )
            invoke.__annotations__ = {
                **{name: dict for name in names},
                "return": output,
            }
            return invoke

        mcp.tool()(make(operation, inputs, result_type))
    return service

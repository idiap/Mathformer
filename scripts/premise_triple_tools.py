# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Single-use MCP continuations over the native triple regression iterator.

Scientific objects stay in a worker; public handles contain source evidence only.
The worker shares discover_proof_steps with discover_proof, never replays steps.
"""

import atexit
import contextlib
import importlib.util
import io
import multiprocessing
from pathlib import Path
import threading
import time
import traceback
from uuid import uuid4
from typing_extensions import TypedDict
import mathformer as hub

ACTION = "atp:premise-guided-triple"
ARTIFACT_ROOT = "artifacts/vampire_atp/premise_guided_triple_inverse_test"


def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "tests/atp/run_premise_guided_triple_inverse.py"
    )
    spec = importlib.util.spec_from_file_location("mathformer_triple_regression", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _worker(pipe, root, profile):
    from backends.atp.MathformerATP.vampire import discover_proof_steps

    try:
        steps = discover_proof_steps(
            profile["statement"],
            artifact_root=Path(root) / ARTIFACT_ROOT,
            time_limit=profile["seconds"],
            premise_loop=profile["premise_loop"],
            premise_budget=profile["budget"],
            generate_premises=profile["generate"],
            minimize_premises=profile["minimize"],
            workflow_stages=True,
        )
        while True:
            command = pipe.recv()
            if command == "next":
                try:
                    pipe.send(("event", *next(steps)))
                except StopIteration as done:
                    pipe.send(("report", done.value))
            elif command[0] == "check":
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    report = source().check_report(command[1])
                    code = source().emit_report(report)
                pipe.send(("finished", code, output.getvalue(), ""))
                return
    except BaseException:
        pipe.send(("error", traceback.format_exc()))
    finally:
        pipe.close()


# Native stage names and public ports. The input state nominal types are defined
# in the authored workflow; actual scientific state is owned by the iterator.
PORTS = {
    "boundary": (["context"], {"execute": bool, "payload": dict, "boundary": dict}),
    "stop": (["payload", "boundary"], {"result": dict}),
    "initialize": (["profile", "boundary"], {"state": dict}),
    "select": (["state", "profile"], {"pack": dict}),
    "generate": (["pack"], {"state": dict, "pending": bool}),
    "lemma": (["state"], {"state": dict, "done": bool}),
    "empty_helpers": (["state"], {"state": dict, "done": bool}),
    "generation_finish": (["state"], {"pack": dict}),
    "generation_bypass": (["pack"], {"pack": dict}),
    "augment": (["pack"], {"state": dict, "pending": bool}),
    "deletion": (["state"], {"state": dict, "done": bool}),
    "empty_deletions": (["state"], {"state": dict, "done": bool}),
    "minimization_finish": (["state"], {"pack": dict}),
    "minimization_bypass": (["pack"], {"pack": dict}),
    "final_proof": (["pack"], {"pack": dict}),
    "direct": (["state", "profile"], {"pack": dict}),
    "carry": (["state", "pack"], {"state": dict, "done": bool}),
    "discovery_finish": (["state", "profile"], {"report": dict}),
    "regression_finish": (
        ["report", "payload", "context", "boundary"],
        {"result": dict},
    ),
    "forward": (["state"], {"state": dict, "done": bool}),
}
EVENTS = dict(
    initialize="initialize",
    select="selection",
    generate="select_pack",
    lemma="lemma_step",
    empty_helpers="lemma_step",
    generation_finish="generation_finish",
    generation_bypass="generation_bypass",
    augment="augment_pack",
    deletion="deletion_step",
    empty_deletions="deletion_step",
    minimization_finish="minimization_finish",
    minimization_bypass="minimization_bypass",
    final_proof="final_attempt",
    direct="final_attempt",
    carry="carry_candidate",
)


class TripleTools:
    def __init__(self, guard=None):
        self.sessions = {}
        self.guard = guard or (lambda: None)
        self.lock = threading.RLock()
        atexit.register(self.close)

    def drop(self, token):
        session = self.sessions.pop(token, None)
        if session and "process" in session:
            session["timer"].cancel()
            session["process"].terminate()
            session["process"].join(timeout=2)
            session["pipe"].close()

    def close(self):
        for token in list(self.sessions):
            self.drop(token)

    def handle(self, token, evidence=None):
        return dict(
            token=token,
            revision=self.sessions[token]["revision"],
            evidence=evidence or {},
        )

    def receive(self, session, command):
        session["pipe"].send(command)
        if not session["pipe"].poll(max(0, session["deadline"] - time.monotonic())):
            raise TimeoutError("triple regression exceeded native 180 second boundary")
        message = session["pipe"].recv()
        if message[0] == "error":
            raise RuntimeError(message[1])
        return message

    def call(self, op, args):
        self.guard()
        if op == "boundary":
            item = hub.build_registry()[ACTION]
            native = hub.prepare_leaf_boundary(
                item, hub.RunContext(**args["context"]), ()
            )
            token = uuid4().hex
            self.sessions[token] = dict(
                native=native,
                item=item,
                context=args["context"],
                revision=0,
                phase="initialize" if native["execute"] else "stop",
            )
            return dict(
                execute=native["execute"],
                payload=native["payload"],
                boundary=self.handle(token),
            )
        handle = args.get("pack") or args.get("state") or args["boundary"]
        token = handle["token"]
        session = self.sessions[token]
        try:
            if op == "forward":
                if session["native"]["execute"]:
                    raise ValueError("cannot forward an executing scientific stage")
                return dict(state=handle, done=True)
            if op == "carry" and args["state"]["token"] != token:
                raise ValueError("candidate and proof belong to different invocations")
            if op in ("stop", "initialize", "regression_finish"):
                if args["boundary"]["token"] != token:
                    raise ValueError("cross-invocation boundary")
            if (
                op not in ("stop", "regression_finish")
                and handle["revision"] != session["revision"]
            ):
                raise ValueError("stale triple continuation")
            if session["phase"] != op:
                raise ValueError("unexpected triple stage: " + op)
            if "profile" in args:
                profile = args["profile"]
                expected = dict(
                    statement=source().DEFAULT_STATEMENT,
                    seconds=3,
                    budget="medium",
                    premise_loop=True,
                    generate=True,
                    minimize=True,
                )
                if profile != expected:
                    raise ValueError("registered triple profile changed")
            if "payload" in args and args["payload"] != session["native"]["payload"]:
                raise ValueError("modified hub payload")
            if op == "stop":
                result = session["native"]["payload"]
                self.drop(token)
                return dict(result=result)
            if op == "initialize":
                parent, child = multiprocessing.get_context("spawn").Pipe()
                process = multiprocessing.get_context("spawn").Process(
                    target=_worker,
                    args=(child, str(hub.REPO_ROOT), profile),
                    daemon=True,
                )
                process.start()
                child.close()
                timer = threading.Timer(
                    session["item"].timeout_seconds, process.terminate
                )
                timer.daemon = True
                session.update(
                    process=process,
                    pipe=parent,
                    timer=timer,
                    deadline=time.monotonic() + session["item"].timeout_seconds,
                )
                timer.start()
            if op == "regression_finish":
                if (
                    args["context"] != session["context"]
                    or args["report"] != session["report_handle"]
                ):
                    raise ValueError("modified regression inputs")
                _, code, stdout, stderr = self.receive(
                    session, ("check", session["report"])
                )
                payload = dict(
                    session["native"]["payload"],
                    status="completed",
                    returncode=code,
                    stdout=stdout,
                    stderr=stderr,
                    ok=code == 0,
                )
                result = hub.finish_leaf_boundary(
                    session["item"], session["native"], payload
                )
                if args["context"]["write_report"]:
                    result["report_file"] = str(hub.write_report(ACTION, result))
                self.drop(token)
                return dict(result=result)
            message = self.receive(session, "next")
            if op == "discovery_finish":
                if message[0] != "report":
                    raise ValueError("expected native discovery completion")
                session.update(report=message[1], phase="regression_finish")
                session["revision"] += 1
                session["report_handle"] = self.handle(token, message[1])
                return dict(report=session["report_handle"])
            _, event, evidence = message
            if event != EVENTS[op]:
                raise ValueError(f"native event mismatch {event} != {EVENTS[op]}")
            session["revision"] += 1
            next_phase = dict(
                initialize="select",
                select="generate",
                generate="lemma",
                generation_finish="augment",
                generation_bypass="augment",
                augment="deletion",
                minimization_finish="final_proof",
                minimization_bypass="final_proof",
                final_proof="carry",
                direct="carry",
                empty_helpers="generation_finish",
                empty_deletions="minimization_finish",
            ).get(op)
            if op in ("lemma", "deletion"):
                next_phase = (
                    ("generation_finish" if op == "lemma" else "minimization_finish")
                    if evidence["done"]
                    else op
                )
            if op == "carry":
                next_phase = "discovery_finish" if evidence["done"] else "select"
            if op == "generate" and not evidence["generated_count"]:
                next_phase = "empty_helpers"
            if op == "augment" and not evidence["initial_ids"]:
                next_phase = "empty_deletions"
            session["phase"] = next_phase
            port = (
                "pack"
                if op
                in (
                    "select",
                    "generation_finish",
                    "generation_bypass",
                    "minimization_finish",
                    "minimization_bypass",
                    "final_proof",
                    "direct",
                )
                else "state"
            )
            output = {port: self.handle(token, evidence)}
            if op in ("lemma", "deletion", "carry", "empty_helpers", "empty_deletions"):
                output["done"] = evidence["done"]
            if op in ("generate", "augment"):
                output["pending"] = bool(
                    evidence["generated_count" if op == "generate" else "initial_ids"]
                )
            return output
        except BaseException:
            self.drop(token)
            raise


def register_premise_triple_tools(mcp, guard=None):
    service = TripleTools(guard)
    for operation, (inputs, outputs) in PORTS.items():
        if operation in ("generation_bypass", "minimization_bypass", "direct"):
            continue
        # Explicit signatures let MCP advertise every named port. No descriptor
        # loading or dynamic code evaluation is involved in registration.
        import inspect

        output_type = TypedDict("Triple_" + operation, outputs)

        def make(op, names, result_type):
            def invoke(**kwargs):
                with service.lock:
                    return service.call(op, kwargs)

            invoke.__name__ = "mathformer_triple_" + op
            invoke.__signature__ = inspect.Signature(
                [
                    inspect.Parameter(
                        name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=dict
                    )
                    for name in names
                ],
                return_annotation=result_type,
            )
            invoke.__annotations__ = {
                **{name: dict for name in names},
                "return": result_type,
            }
            return invoke

        mcp.tool()(make(operation, inputs, output_type))
    return service

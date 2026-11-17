# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Controlled ATP demo continuations. Scientific state stays in a bounded worker.

Handles are process-local, single-use per stage, and cannot resume another server.
No object serialization, solver substitution, or alternate algorithm is used.
"""

from __future__ import annotations

import atexit
import contextlib
import io
import multiprocessing
from pathlib import Path
import threading
import time
import traceback
from types import SimpleNamespace
from uuid import uuid4
from typing_extensions import TypedDict
import mathformer as hub

ACTION = "atp:demo"
DEMO = dict(
    text_file="examples/vampire_group_inverse_product_input.md",
    artifact_root="artifacts/vampire_atp/atp_function_demo",
    premise_loop=True,
    premise_budget="medium",
    generate_premises=True,
    minimize_premises=True,
    time_limit=3,
)


class Handle(TypedDict):
    token: str
    revision: int
    evidence: dict


class StateOutput(TypedDict):
    state: Handle


class GuardOutput(StateOutput):
    done: bool


class BoundaryOutput(StateOutput):
    execute: bool


class AttemptOutput(TypedDict):
    attempt: Handle


class ResultOutput(TypedDict):
    result: dict


def _worker(pipe, root, demo):
    """Run source-owned stages; wait between calls without pre-executing work."""
    from backends.atp.MathformerATP.vampire import (
        discover_proof_steps,
        read_text_argument,
    )
    from run_vampire_atp import emit_result

    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            steps = discover_proof_steps(
                read_text_argument(None, Path(root) / demo["text_file"]),
                artifact_root=Path(root) / demo["artifact_root"],
                **{
                    key: demo[key]
                    for key in (
                        "premise_loop",
                        "premise_budget",
                        "generate_premises",
                        "minimize_premises",
                        "time_limit",
                    )
                },
            )
            while pipe.recv() == "next":
                try:
                    event, evidence = next(steps)
                    pipe.send(("event", event, evidence))
                except StopIteration as completed:
                    report = completed.value
                    code = emit_result(
                        report,
                        bool(report["ok"]),
                        SimpleNamespace(
                            json=False, artifact_root=demo["artifact_root"]
                        ),
                    )
                    pipe.send(
                        ("finished", code, stdout.getvalue(), stderr.getvalue(), report)
                    )
                    return
    except BaseException:
        pipe.send(("error", traceback.format_exc()))
    finally:
        pipe.close()


class DemoTools:
    def __init__(self, guard=None):
        self.sessions = {}
        self.guard = guard or (lambda: None)
        self.lock = threading.RLock()
        atexit.register(self.close)

    def close(self):
        for token in list(self.sessions):
            self.drop(token)

    def drop(self, token):
        session = self.sessions.pop(token, None)
        if session:
            if session.get("timer"):
                session["timer"].cancel()
            if session.get("process"):
                session["process"].terminate()
                session["process"].join(timeout=2)
                session["pipe"].close()

    def handle(self, token, evidence=None):
        return dict(
            token=token,
            revision=self.sessions[token]["revision"],
            evidence=evidence or {},
        )

    def session(self, handle, phase):
        self.guard()
        session = self.sessions[handle["token"]]
        if handle["revision"] != session["revision"] or session["phase"] != phase:
            raise ValueError("stale handle or invalid ATP stage order")
        return session

    def boundary(self, context, demo):
        self.guard()
        if demo != DEMO:
            raise ValueError("Only the registered atp:demo constants are accepted")
        item = hub.build_registry()[ACTION]
        boundary = hub.prepare_leaf_boundary(item, hub.RunContext(**context), [])
        token = uuid4().hex
        self.sessions[token] = dict(
            boundary=boundary,
            item=item,
            demo=dict(demo),
            revision=0,
            phase="initialize" if boundary["execute"] else "bypass",
        )
        return dict(state=self.handle(token), execute=boundary["execute"])

    def advance(self, handle, phase):
        session = self.session(handle, phase)
        token = handle["token"]
        if session.get("inert"):
            if phase == "finish":
                result = session.get("terminal_payload", session["boundary"]["payload"])
                if session.get("terminal_payload"):
                    result = hub.finish_leaf_boundary(
                        session["item"], session["boundary"], result
                    )
                self.drop(token)
                return dict(result=result)
            session["revision"] += 1
            session["phase"] = dict(
                initialize="select_pack",
                select_pack="lemma_step",
                lemma_step="augment_pack",
                augment_pack="deletion_step",
                deletion_step="final_attempt",
                final_attempt="carry_candidate",
                carry_candidate="finish",
            )[phase]
            result = {
                "attempt" if phase == "final_attempt" else "state": self.handle(token)
            }
            if phase in ("lemma_step", "deletion_step", "carry_candidate"):
                result["done"] = True
            return result
        if phase == "initialize":
            parent, child = multiprocessing.get_context("spawn").Pipe()
            process = multiprocessing.get_context("spawn").Process(
                target=_worker,
                args=(child, str(hub.REPO_ROOT), session["demo"]),
                daemon=True,
            )
            process.start()
            child.close()
            session.update(
                process=process,
                pipe=parent,
                deadline=time.monotonic() + session["item"].timeout_seconds,
            )
            timer = threading.Timer(session["item"].timeout_seconds, process.terminate)
            timer.daemon = True
            timer.start()
            session["timer"] = timer
        try:
            session["pipe"].send("next")
            if not session["pipe"].poll(max(0, session["deadline"] - time.monotonic())):
                raise TimeoutError("native ATP demo exceeded 120 seconds")
            message = session["pipe"].recv()
            if message[0] == "error":
                raise RuntimeError(message[1])
            if phase == "finish":
                if message[0] != "finished":
                    raise ValueError("unexpected native terminal event")
                _, code, stdout, stderr, report = message
                payload = dict(
                    session["boundary"]["payload"],
                    status="completed",
                    returncode=code,
                    stdout=stdout,
                    stderr=stderr,
                    ok=code == 0,
                )
                result = hub.finish_leaf_boundary(
                    session["item"], session["boundary"], payload
                )
                self.drop(token)
                return dict(result=result)
            _, event, evidence = message
            if event != phase:
                raise ValueError(f"native stage mismatch: {event} != {phase}")
            session["revision"] += 1
            next_phase = (
                dict(
                    initialize="select_pack",
                    select_pack="lemma_step",
                    augment_pack="deletion_step",
                    final_attempt="carry_candidate",
                )[phase]
                if phase
                in ("initialize", "select_pack", "augment_pack", "final_attempt")
                else None
            )
            if phase == "lemma_step":
                next_phase = "augment_pack" if evidence["done"] else phase
            elif phase == "deletion_step":
                next_phase = "final_attempt" if evidence["done"] else phase
            elif phase == "carry_candidate":
                next_phase = "finish" if evidence["done"] else "select_pack"
            session["phase"] = next_phase
            output = {
                "attempt" if phase == "final_attempt" else "state": self.handle(
                    token, evidence
                )
            }
            if phase in ("lemma_step", "deletion_step", "carry_candidate"):
                output["done"] = evidence["done"]
            return output
        except (TimeoutError, EOFError, BrokenPipeError):
            if time.monotonic() < session["deadline"]:
                self.drop(token)
                raise
            session["process"].terminate()
            session["process"].join(timeout=2)
            session["inert"] = True
            session["terminal_payload"] = dict(
                session["boundary"]["payload"],
                status="timeout",
                returncode=None,
                stdout="",
                stderr="",
                ok=False,
                timeout_seconds=session["item"].timeout_seconds,
            )
            return self.advance(handle, phase)
        except BaseException:
            self.drop(token)
            raise

    def bypass(self, state):
        session = self.session(state, "bypass")
        session["inert"] = True
        session["phase"] = "select_pack"
        session["revision"] += 1
        return dict(state=self.handle(state["token"]))


def register_atp_demo_tools(mcp, guard=None):
    tools = DemoTools(guard)

    @mcp.tool()
    def mathformer_atp_boundary(context: dict, demo: dict) -> BoundaryOutput:
        with tools.lock:
            return tools.boundary(context, demo)

    @mcp.tool()
    def mathformer_atp_initialize(boundary: Handle, demo: dict) -> StateOutput:
        if demo != DEMO:
            raise ValueError("demo changed after admission")
        with tools.lock:
            return tools.advance(boundary, "initialize")

    @mcp.tool()
    def mathformer_atp_select_pack(state: Handle) -> StateOutput:
        with tools.lock:
            return tools.advance(state, "select_pack")

    @mcp.tool()
    def mathformer_atp_lemma_step(state: Handle) -> GuardOutput:
        with tools.lock:
            return tools.advance(state, "lemma_step")

    @mcp.tool()
    def mathformer_atp_augment_pack(state: Handle) -> StateOutput:
        with tools.lock:
            return tools.advance(state, "augment_pack")

    @mcp.tool()
    def mathformer_atp_deletion_step(state: Handle) -> GuardOutput:
        with tools.lock:
            return tools.advance(state, "deletion_step")

    @mcp.tool()
    def mathformer_atp_final_attempt(state: Handle) -> AttemptOutput:
        with tools.lock:
            return tools.advance(state, "final_attempt")

    @mcp.tool()
    def mathformer_atp_carry_candidate(state: Handle, attempt: Handle) -> GuardOutput:
        if state["token"] != attempt["token"]:
            raise ValueError("candidate and attempt belong to different executions")
        with tools.lock:
            return tools.advance(attempt, "carry_candidate")

    @mcp.tool()
    def mathformer_atp_finish(state: Handle, boundary: Handle) -> ResultOutput:
        if state["token"] != boundary["token"]:
            raise ValueError("boundary belongs to another execution")
        with tools.lock:
            return tools.advance(state, "finish")

    @mcp.tool()
    def mathformer_atp_bypass(state: Handle) -> StateOutput:
        with tools.lock:
            return tools.bypass(state)

    return tools

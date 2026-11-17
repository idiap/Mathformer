# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged policy example tools over the authoritative native generator.

Continuations are single use and scoped to this service instance. Native Python
objects stay in the service; the public state contains observations and a token.
A process boundary enforces the hub's cumulative 180-second execution deadline.
"""

import contextlib
import importlib.util
import io
import multiprocessing
import os
import signal
import sys
import subprocess
import time
from functools import lru_cache
from pathlib import Path
import threading
import traceback
from uuid import uuid4
from typing_extensions import TypedDict

import mathformer as hub
from backends.atp.MathformerATP.vampire import discover_proof_steps


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1] / "examples/vampire_informal_to_proofs.py"
    )
    spec = importlib.util.spec_from_file_location("mathformer_policy_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _native_search_worker(channel, statement, artifact_root, deadline):
    """Keep the native generator and its child prover inside a timed process."""
    if hasattr(os, "setsid"):
        os.setsid()
    steps = discover_proof_steps(statement, artifact_root=artifact_root, time_limit=10)
    try:
        while channel.poll(max(0, deadline - time.monotonic())):
            if channel.recv() != "next":
                break
            try:
                channel.send(("yield", next(steps)))
            except StopIteration as done:
                channel.send(("return", done.value))
                break
            except Exception as error:
                channel.send(("error", (error, traceback.format_exc())))
                break
    except (EOFError, BrokenPipeError):
        pass
    finally:
        steps.close()
        channel.close()


class NativeSearch:
    """A process boundary with the hub's cumulative timeout, no replay or retry.

    The process owns exactly one generator. Fork preserves the current runtime
    on POSIX; spawn is used on platforms without fork. No provider or solver
    implementation is supplied by this transport.
    """

    def __init__(self, statement, artifact_root, deadline, *, start_method=None):
        context = multiprocessing.get_context(
            start_method
            or (
                "fork" if "fork" in multiprocessing.get_all_start_methods() else "spawn"
            )
        )
        self.channel, child = context.Pipe()
        self.deadline = deadline
        self.process = context.Process(
            target=_native_search_worker,
            args=(child, statement, artifact_root, deadline),
            daemon=True,
        )
        self.process.start()
        child.close()

    def __next__(self):
        self.channel.send("next")
        if not self.channel.poll(max(0, self.deadline - time.monotonic())):
            self.close()
            raise subprocess.TimeoutExpired("example:vampire-policy", 180)
        kind, value = self.channel.recv()
        if kind == "yield":
            return value
        self.close()
        if kind == "return":
            raise StopIteration(value)
        error, native_traceback = value
        error.add_note(native_traceback)
        raise error

    def close(self):
        self.channel.close()
        # After a terminal message the child normally exits immediately.
        self.process.join(timeout=0.05)
        if self.process.is_alive():
            if hasattr(os, "killpg"):
                try:
                    os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    self.process.terminate()
            else:
                self.process.terminate()
            self.process.join()


class PlanOutput(TypedDict):
    plan: dict


class StatementOutput(TypedDict):
    statement: str


class StateOutput(TypedDict):
    state: dict


class AttemptOutput(TypedDict):
    attempt: dict


class CarryOutput(TypedDict):
    state: dict
    done: bool


class ReportOutput(TypedDict):
    report: dict


class OutcomeOutput(TypedDict):
    outcome: dict


class SkipOutput(TypedDict):
    outcome: dict
    state: dict
    statement: str
    done: bool


class ResultOutput(TypedDict):
    result: dict


def register_vampire_policy_tools(mcp, guard=None):
    sessions = {}
    lock = threading.RLock()
    item = hub.build_registry()["example:vampire-policy"]

    def check():
        if guard:
            guard()

    def lookup(public, phase):
        session = sessions[public["token"]]
        if session["public"] != public or session["phase"] != phase:
            raise ValueError("stale or out-of-order policy continuation")
        return session

    def public(token, revision, evidence):
        return dict(token=token, revision=revision, evidence=evidence)

    def fail_session(token):
        """Retain the native post-process audit even when a source step raises."""
        session = sessions.pop(token)
        if "steps" in session:
            session["steps"].close()
        boundary = session["boundary"]
        payload = {
            **boundary["payload"],
            "status": "completed",
            "returncode": 1,
            "stdout": "",
            "stderr": traceback.format_exc(),
            "ok": False,
        }
        error = sys.exception()
        if isinstance(error, subprocess.TimeoutExpired):
            payload.update(
                status="timeout", returncode=None, timeout_seconds=item.timeout_seconds
            )
        payload = hub.finish_leaf_boundary(item, boundary, payload)
        if session["context"].write_report:
            hub.write_report(item.action_id, payload)

    def event_step(state, phase, expected, following):
        check()
        with lock:
            session = lookup(state, phase)
            try:
                event, evidence = next(session["steps"])
                if event != expected:
                    raise ValueError("unexpected policy stage: " + event)
                updated = public(state["token"], state["revision"] + 1, evidence)
                session.update(public=updated, phase=following)
                return updated
            except BaseException:
                fail_session(state["token"])
                raise

    @mcp.tool()
    def mathformer_policy_preflight(context: dict) -> PlanOutput:
        ctx = hub.RunContext(**context)
        if not ctx.dry_run:
            check()
        boundary = hub.prepare_leaf_boundary(item, ctx, ())
        token = uuid4().hex
        with lock:
            sessions[token] = dict(
                boundary=boundary,
                context=ctx,
                phase="plan",
                deadline=time.monotonic() + item.timeout_seconds,
            )
        return {"plan": dict(token=token, execute=boundary["execute"])}

    @mcp.tool()
    def mathformer_policy_read_statement(plan: dict) -> StatementOutput:
        with lock:
            session = sessions[plan["token"]]
            if not session["boundary"]["execute"] or session["phase"] != "plan":
                raise ValueError("policy execution was not admitted")
            session["phase"] = "read"
        try:
            return {"statement": source().INPUT_PATH.read_text(encoding="utf-8")}
        except BaseException:
            with lock:
                fail_session(plan["token"])
            raise

    @mcp.tool()
    def mathformer_policy_initialize(statement: str, plan: dict) -> StateOutput:
        check()
        with lock:
            session = sessions[plan["token"]]
            if session["phase"] != "read" or not session["boundary"]["execute"]:
                raise ValueError("policy initialization out of order")
            if statement != source().INPUT_PATH.read_text(encoding="utf-8"):
                raise ValueError("policy example requires its fixed input")
            steps = NativeSearch(statement, source().ARTIFACT_ROOT, session["deadline"])
            try:
                event, evidence = next(steps)
                if event != "initialize":
                    raise ValueError("unexpected policy initialization")
                state = public(plan["token"], 0, evidence)
                session.update(steps=steps, public=state, phase="attempt")
                return {"state": state}
            except BaseException:
                steps.close()
                fail_session(plan["token"])
                raise

    @mcp.tool()
    def mathformer_policy_direct_attempt(state: dict) -> AttemptOutput:
        return {"attempt": event_step(state, "attempt", "final_attempt", "carry")}

    @mcp.tool()
    def mathformer_policy_carry(state: dict, attempt: dict) -> CarryOutput:
        with lock:
            session = lookup(attempt, "carry")
            if (
                state["token"] != attempt["token"]
                or state["revision"] + 1 != attempt["revision"]
            ):
                raise ValueError("policy state and attempt differ")
            updated = event_step(attempt, "carry", "carry_candidate", "report")
            done = updated["evidence"]["done"]
            if not done:
                session["phase"] = "attempt"
            return {"state": updated, "done": done}

    @mcp.tool()
    def mathformer_policy_write_report(state: dict) -> ReportOutput:
        check()
        with lock:
            session = lookup(state, "report")
            try:
                next(session["steps"])
                raise ValueError("policy search has not finished")
            except StopIteration as done:
                session["phase"] = "finish"
                return {"report": done.value}
            except BaseException:
                fail_session(state["token"])
                raise
            finally:
                session["steps"].close()

    @mcp.tool()
    def mathformer_policy_finish_example(report: dict, statement: str) -> OutcomeOutput:
        stdout, stderr = io.StringIO(), io.StringIO()
        # Capture exactly the CLI's printing and failure without corrupting MCP stdout.
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = source().finish_example(statement, report)
            except Exception:
                traceback.print_exc()
                code = 1
        return {
            "outcome": dict(
                status="completed",
                returncode=code,
                stdout=stdout.getvalue(),
                stderr=stderr.getvalue(),
                ok=code == 0,
            )
        }

    @mcp.tool()
    def mathformer_policy_skip(plan: dict) -> SkipOutput:
        with lock:
            session = sessions[plan["token"]]
            if session["boundary"]["execute"]:
                raise ValueError("cannot skip admitted policy execution")
            return {
                "outcome": dict(session["boundary"]["payload"]),
                "state": public(plan["token"], 0, {"skipped": True}),
                "statement": "",
                "done": True,
            }

    @mcp.tool()
    def mathformer_policy_audit(plan: dict, outcome: dict) -> ResultOutput:
        with lock:
            session = sessions.pop(plan["token"])
        boundary = session["boundary"]
        if boundary["execute"]:
            payload = hub.finish_leaf_boundary(
                item, boundary, {**boundary["payload"], **outcome}
            )
        else:
            payload = boundary["payload"]
        if session["context"].write_report:
            payload["report_file"] = str(hub.write_report(item.action_id, payload))
        return {"result": payload}

    return sessions

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Staged route ports backed by the native, timeout-controlled verifier process."""

from concurrent.futures import Future
from contextlib import asynccontextmanager
from copy import deepcopy
from dataclasses import asdict
import atexit
import json
import os
from pathlib import Path
from threading import RLock, Thread
from tempfile import TemporaryDirectory
import time
from uuid import uuid4
from typing_extensions import TypedDict

import mathformer as hub
from adoption_check_tools import Context

ACTION = "prism:native-semantic-parallel-e2e"
ROUTE = "prism.native-semantic-parallel-e2e"
CLEANUPS = []


@asynccontextmanager
async def prism_route_lifespan(server):
    from sympy_grounded_sample_tools import sympy_grounded_sample_lifespan

    async with sympy_grounded_sample_lifespan(server) as state:
        try:
            yield state
        finally:
            for cleanup in CLEANUPS:
                cleanup()


class Updated(TypedDict):
    state: dict


class Finished(TypedDict):
    result: dict


def selected_match(match):
    route = next(r for r in hub.build_intent_routes() if r.route_id == ROUTE)
    native = json.loads(json.dumps(asdict(route)))
    projection = match["route"]
    if (
        route.action_ids != (ACTION,)
        or not {"route_id", "action_ids"} <= projection.keys()
        or any(
            key not in native or value != native[key]
            for key, value in projection.items()
        )
    ):
        raise ValueError("selected route differs from native declaration")
    return hub.IntentMatch(route, match["score"], tuple(match["matched_terms"]))


def checked_registry(projection):
    registry = hub.build_registry()
    item = registry[ACTION]
    if (
        item.depends_on
        or item.allows_extra_args
        or item.timeout_seconds != 3600
        or item.safety != "writes_repo"
        or item.writes != ("mathformer-prism/tests/native-semantic-parallel-e2e.json",)
        or item.command
        != (
            "uv",
            "run",
            "python",
            "scripts/prism/verify_mathformer_prism.py",
            "--root",
            "mathformer-prism",
            "--jobs",
            "4",
            "--handler",
            "codex",
            "--output",
            "mathformer-prism/tests/native-semantic-parallel-e2e.json",
        )
    ):
        raise ValueError("native verification capability changed; requalify binding")
    if any(
        key not in registry or value != hub.action_to_dict(registry[key])
        for key, value in projection.items()
    ):
        raise ValueError("registry differs from native declaration")
    return {key: registry[key] for key in projection}


class StepProcess:
    """One native subprocess; the shared launcher owns timeout/output capture."""

    def __init__(self, item, payload, root):
        self.temporary = TemporaryDirectory(prefix="mathformer-prism-channel-")
        self.directory = Path(self.temporary.name)
        self.index = 0
        self.future = Future()
        environment = dict(os.environ)
        environment["MATHFORMER_PRISM_STEP_CHANNEL"] = str(self.directory)

        def launch():
            try:
                self.future.set_result(
                    hub.launch_leaf_boundary(
                        item, payload, repository_root=root, environment=environment
                    )
                )
            except BaseException as exc:
                self.future.set_exception(exc)

        Thread(target=launch, daemon=True).start()

    def receive(self):
        response = self.directory / f"response-{self.index}.json"
        while not response.exists():
            if self.future.done():
                self.future.result()  # unexpected launch errors propagate
                if not response.exists():
                    return None
            time.sleep(0.02)
        return json.loads(response.read_text(encoding="utf-8"))

    def step(self, method):
        if self.future.done():
            self.future.result()
            return None
        self.index += 1
        pending = self.directory / "request.pending"
        pending.write_text(json.dumps({"method": method}), encoding="utf-8")
        pending.replace(self.directory / f"request-{self.index}.json")
        return self.receive()

    def result(self):
        return self.future.result()

    def close(self):
        try:
            (self.directory / "cancel").touch()
            return self.future.result()
        finally:
            self.temporary.cleanup()


def register_prism_native_route_tools(
    mcp, authorize=lambda: None, path_allowed=lambda p: True
):
    scopes = {}
    lock = RLock()

    def close_scope(scope):
        if scope.get("process"):
            payload = scope["process"].close()
            return hub.finish_leaf_boundary(
                scope["item"], scope["boundary"], payload, repository_root=scope["root"]
            )

    def close_all():
        with lock:
            pending = list(scopes.values())
            scopes.clear()
            errors = []
            for scope in pending:
                try:
                    close_scope(scope)
                except BaseException as exc:
                    errors.append(exc)
            if errors:
                raise errors[0]

    atexit.register(close_all)
    CLEANUPS.append(close_all)

    def pack(scope, *, scan=False, runtime=False, done=True, failed=False, cursor=0):
        state = dict(
            session_id=scope["token"],
            scan=scan,
            runtime=runtime,
            done=done,
            failed=failed,
            cursor=cursor,
            revision=scope.get("revision", 0),
        )
        scope["state"] = state
        return {"state": deepcopy(state)}

    def owned(state, phases):
        scope = scopes.get(state.get("session_id"))
        if scope is None or state != scope["state"] or scope["phase"] not in phases:
            raise ValueError("unknown, modified, stale or out-of-order route state")
        scope["revision"] = scope.get("revision", 0) + 1
        return scope

    @mcp.tool()
    def mathformer_prism_route_initialize(
        context: Context,
        catalog: dict,
        match: dict,
        registry: dict,
        repository_root: str | None = None,
    ) -> Updated:
        """Admit the selected native route, preflight, then start its real process."""
        with lock:
            native = checked_registry(registry)
            selected = selected_match(match)
            root = (
                hub.REPO_ROOT
                if repository_root is None
                else Path(repository_root).resolve()
            )
            run_context = hub.RunContext(**context)
            route = hub.initialize_intent_state()
            action = hub.select_intent_action(route, selected)
            admission = hub.admit_action(action, native)
            scope = dict(
                token=uuid4().hex,
                route=route,
                match=selected,
                registry=native,
                context=run_context,
                root=root,
                phase="static_skip",
                process=None,
            )
            if not admission["accepted"]:
                scope["payload"] = hub.reject_action(action, admission)
            else:
                scope["item"] = native[action]
                boundary = hub.prepare_leaf_boundary(
                    native[action], run_context, (), repository_root=root
                )
                scope.update(boundary=boundary, payload=boundary["payload"])
                if boundary["execute"]:
                    authorize()
                    if not path_allowed(root / native[action].writes[0]):
                        raise PermissionError(
                            "verifier output outside service write roots"
                        )
                    actual = json.loads(
                        (root / "mathformer-prism/workflow_catalog.json").read_text()
                    )
                    if catalog != actual or not 1 <= len(actual["workflows"]) <= 14:
                        raise ValueError(
                            "catalog differs from source-owned bounded catalog"
                        )
                    process = StepProcess(native[action], boundary["payload"], root)
                    scope["process"] = process
                    try:
                        response = process.receive()
                    except BaseException:
                        process.close()
                        raise
                    if response and response.get("ok"):
                        if response["catalog"] != catalog:
                            process.close()
                            raise ValueError(
                                "catalog changed during verifier initialization"
                            )
                        scope["phase"] = "static"
                    else:
                        scope["payload"] = process.result()
            scopes[scope["token"]] = scope
            return pack(
                scope,
                scan=scope["phase"] == "static",
                done=scope["phase"] != "static",
                failed=not scope["payload"].get("ok", True),
            )

    def iteration(state, static):
        with lock:
            scope = owned(state, {"static" if static else "runtime"})
            process = scope["process"]
            response = process.step("validate_entry" if static else "await_entry")
            if not response or not response.get("ok"):
                scope["payload"] = process.result()
                scope["phase"] = "runtime_skip" if static else "finalize"
                return pack(scope, failed=True, cursor=state["cursor"])
            done = response["done"]
            scope["phase"] = (
                ("runtime" if static else "finalize") if done else scope["phase"]
            )
            return pack(
                scope,
                scan=static and not done,
                runtime=(done if static else not done),
                done=done,
                failed=bool(response.get("runtime_failures")),
                cursor=response["cursor"],
            )

    @mcp.tool()
    def mathformer_prism_route_validate_entry(state: dict) -> Updated:
        """Run one source static-validation step; abort immediately on failure."""
        return iteration(state, True)

    @mcp.tool()
    def mathformer_prism_route_await_entry(state: dict) -> Updated:
        """Submit once, then await in source order including all failed futures."""
        return iteration(state, False)

    @mcp.tool()
    def mathformer_prism_route_retain_state(state: dict) -> Updated:
        """Carry a native early return or failed static phase through skipped work."""
        with lock:
            scope = owned(state, {"static_skip", "runtime_skip"})
            scope["phase"] = (
                "runtime_skip" if scope["phase"] == "static_skip" else "finalize"
            )
            return pack(scope, failed=state["failed"], cursor=state["cursor"])

    @mcp.tool()
    def mathformer_prism_route_finalize(state: dict) -> Finished:
        """Join, capture native process result, audit writes, and finish the route."""
        with lock:
            scope = owned(state, {"finalize"})
            try:
                process = scope["process"]
                if process:
                    if not process.future.done():
                        process.step("finalize")
                    payload = process.result()
                    payload = hub.finish_leaf_boundary(
                        scope["item"],
                        scope["boundary"],
                        payload,
                        repository_root=scope["root"],
                    )
                else:
                    payload = scope["payload"]
                route, done = hub.advance_intent_state(
                    scope["route"], payload, scope["context"], 1
                )
                assert done
                return {
                    "result": hub.finish_intent_state(
                        route, scope["match"], scope["registry"]
                    )
                }
            finally:
                try:
                    if scope["process"]:
                        scope["process"].close()
                finally:
                    scopes.pop(scope["token"], None)

    @mcp.tool()
    def mathformer_prism_route_close(state: dict) -> dict:
        """Cancel an interrupted graph, release native resources, and audit writes."""
        with lock:
            scope = scopes.pop(state.get("session_id"), None)
            if scope and scope["process"]:
                payload = close_scope(scope)
                return {"closed": True, "child": payload}
        return {"closed": True}

    return close_all

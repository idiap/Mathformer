# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""One native catalog subprocess, explicit cursor ports, and hub write auditing.

Continuation tokens retain trusted snapshots and child state in this server.
Transported state is checked, never used to authorize writes or forge results.
"""

import atexit
from copy import deepcopy
from functools import wraps
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import RLock
import uuid
from typing_extensions import TypedDict
import mathformer as hub
from catalog_check_tools import SOURCE, source
from quality_smoke_tools import Context

ACTION = "adoption:catalog"


class Boundary(TypedDict):
    execute: bool
    session: str


class Data(TypedDict):
    session: str
    value: dict
    runnable: bool


class State(TypedDict):
    session: str
    data: dict
    position: int
    lines: list[str]
    runnable: bool


class Prepared(TypedDict):
    boundary: Boundary


class Loaded(TypedDict):
    data: Data


class Begun(TypedDict):
    state: State


class Advanced(TypedDict):
    state: State
    done: bool


class Text(TypedDict):
    text: str


class Result(TypedDict):
    result: dict


def serialized(method):
    @wraps(method)
    def invoke(self, *args, **kwargs):
        with self.lock:
            return method(self, *args, **kwargs)

    return invoke


class CatalogTools:
    def __init__(self, before_write):
        self.lock = RLock()
        self.records = {}
        self.before_write = before_write
        atexit.register(self.close)

    def dispose(self, saved):
        child = saved.get("process")
        if child:
            if child.poll() is None:
                child.terminate()
            child.wait()
            child.stdin.close()
            child.stdout.close()
            saved["stderr"].close()

    @serialized
    def close(self):
        for saved in self.records.values():
            self.dispose(saved)
        self.records.clear()

    @serialized
    def prepare(self, context, extra_args, repository_root):
        root = (
            hub.REPO_ROOT
            if repository_root is None
            else Path(repository_root).resolve()
        )
        item = hub.build_registry()[ACTION]
        native = hub.prepare_leaf_boundary(
            item, hub.RunContext(**context), extra_args, repository_root=root
        )
        token = uuid.uuid4().hex
        boundary = {"execute": native["execute"], "session": token}
        self.records[token] = dict(
            boundary=deepcopy(boundary),
            native=native,
            item=item,
            root=root,
            phase="load" if native["execute"] else "idle",
        )
        return {"boundary": boundary}

    def current(self, value, key, phase):
        saved = self.records[value["session"]]
        if value != saved[key] or saved["phase"] != phase:
            raise ValueError("modified, stale or out-of-order catalog continuation")
        return saved

    def request(self, saved, operation):
        # Uncaught source exceptions exit the child and remain nonzero hub results.
        if saved.get("crashed"):
            return {
                "data": {},
                "state": {"data": {}, "position": 0, "lines": []},
                "text": "",
                "runnable": False,
                "done": True,
            }
        child = saved["process"]
        child.stdin.write(json.dumps({"operation": operation}) + "\n")
        child.stdin.flush()
        line = child.stdout.readline()
        if not line:
            saved["crashed"] = True
            child.wait()
            return self.request(saved, operation)
        return json.loads(line)

    @serialized
    def load(self, boundary):
        saved = self.current(boundary, "boundary", "load")
        # Guard before launch as well as publication; preflight remains native.
        self.before_write(saved["root"] / source().CATALOG.relative_to(hub.REPO_ROOT))
        saved["stderr"] = tempfile.TemporaryFile(mode="w+t")
        # No shell, arbitrary argv, external model or alternate algorithm. The
        # fixed source runs once and waits at its shared native step boundaries.
        program = (
            "import runpy,sys; from pathlib import Path; "
            "ns=runpy.run_path(sys.argv[1]); "
            'raise SystemExit(ns["catalog_protocol"](Path(sys.argv[2])))'
        )
        try:
            saved["process"] = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    program,
                    str(hub.REPO_ROOT / SOURCE),
                    str(saved["root"]),
                ],
                cwd=saved["root"],
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=saved["stderr"],
            )
        except BaseException:
            saved["stderr"].close()
            self.records.pop(boundary["session"])
            raise
        frame = self.request(saved, "load")
        data = dict(
            session=boundary["session"], value=frame["data"], runnable=frame["runnable"]
        )
        saved.update(data=deepcopy(data), phase="begin")
        return {"data": data}

    @serialized
    def begin(self, data):
        saved = self.current(data, "data", "begin")
        frame = self.request(saved, "begin")
        state = dict(
            frame["state"], session=data["session"], runnable=frame["runnable"]
        )
        saved.update(
            state=deepcopy(state), phase="append" if state["runnable"] else "retain"
        )
        return {"state": state}

    @serialized
    def idle(self, boundary):
        saved = self.current(boundary, "boundary", "idle")
        state = dict(
            session=boundary["session"], data={}, position=0, lines=[], runnable=False
        )
        saved.update(state=deepcopy(state), phase="retain")
        return {"state": state}

    @serialized
    def append(self, state):
        saved = self.current(state, "state", "append")
        frame = self.request(saved, "append")
        state = dict(
            frame["state"], session=state["session"], runnable=frame["runnable"]
        )
        saved.update(state=deepcopy(state), phase="text" if frame["done"] else "append")
        return {"state": state, "done": frame["done"]}

    @serialized
    def retain(self, state):
        saved = self.current(state, "state", "retain")
        saved["phase"] = "text" if saved["boundary"]["execute"] else "return"
        return {"state": state, "done": True}

    @serialized
    def text(self, state):
        saved = self.current(state, "state", "text")
        frame = self.request(saved, "text")
        saved.update(text=frame["text"], phase="publish")
        return {"text": frame["text"]}

    @serialized
    def publish(self, boundary, text):
        saved = self.current(boundary, "boundary", "publish")
        if text != saved["text"]:
            raise ValueError("modified catalog text")
        self.before_write(saved["root"] / source().CATALOG.relative_to(hub.REPO_ROOT))
        try:
            frame = self.request(saved, "publish")
            child = saved["process"]
            code = child.wait()
            saved["stderr"].seek(0)
            stderr = saved["stderr"].read()
            payload = hub.complete_leaf_boundary(
                deepcopy(saved["native"]["payload"]),
                code,
                frame.get("stdout", ""),
                stderr,
            )
            return {
                "result": hub.finish_leaf_boundary(
                    saved["item"],
                    saved["native"],
                    payload,
                    repository_root=saved["root"],
                )
            }
        finally:
            self.records.pop(boundary["session"])
            self.dispose(saved)

    @serialized
    def early(self, boundary):
        saved = self.current(boundary, "boundary", "return")
        self.records.pop(boundary["session"])
        return {"result": saved["native"]["payload"]}


def register_adoption_catalog_tools(mcp, before_write):
    service = CatalogTools(before_write)

    @mcp.tool()
    def mathformer_adoption_catalog_prepare(
        context: Context, extra_args: list[str], repository_root: str | None = None
    ) -> Prepared:
        return service.prepare(context, extra_args, repository_root)

    @mcp.tool()
    def mathformer_adoption_catalog_load(boundary: Boundary) -> Loaded:
        return service.load(boundary)

    @mcp.tool()
    def mathformer_adoption_catalog_begin(data: Data) -> Begun:
        return service.begin(data)

    @mcp.tool()
    def mathformer_adoption_catalog_idle(boundary: Boundary) -> Begun:
        return service.idle(boundary)

    @mcp.tool()
    def mathformer_adoption_catalog_append(state: State) -> Advanced:
        return service.append(state)

    @mcp.tool()
    def mathformer_adoption_catalog_retain(state: State) -> Advanced:
        return service.retain(state)

    @mcp.tool()
    def mathformer_adoption_catalog_text(state: State) -> Text:
        return service.text(state)

    @mcp.tool()
    def mathformer_adoption_catalog_publish(boundary: Boundary, text: str) -> Result:
        return service.publish(boundary, text)

    @mcp.tool()
    def mathformer_adoption_catalog_return(boundary: Boundary) -> Result:
        return service.early(boundary)

    return service

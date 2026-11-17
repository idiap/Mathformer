# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Step the actual unittest runner at test boundaries, retaining its live result.

No test algorithm or runner summary is reimplemented. A worker owns the native
suite, fixtures and TextTestRunner throughout; JSON state is a checked receipt,
not a serialized replacement for unittest's result. Sessions cannot be resumed.
"""

from copy import deepcopy
from functools import partial
import importlib.util
import io
from pathlib import Path
from queue import Queue
import threading
import unittest
import uuid
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/agent_clients/test_agent_plugins.py"


def load_source(repository_root):
    spec = importlib.util.spec_from_file_location("mathformer_plugin_tests", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # These globals are the source's repository context. Its test methods,
    # synchronize implementation, loader and assertions remain unchanged.
    module.ROOT = Path(repository_root).resolve(strict=True)
    module.load_catalog = partial(module.load_catalog, module.ROOT)
    return module


class Session:
    def __init__(self, repository_root):
        self.source = load_source(repository_root)
        self.suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            self.source.AgentPluginTests
        )
        self.names = [test.id() for test in self.suite]
        if len(self.names) != 11:
            raise ValueError(
                "native discovery differs from the eleven-test contract bound"
            )
        self.token = uuid.uuid4().hex
        self.outcomes = []
        self.events = Queue()
        self.permit = threading.Event()
        self.stream = io.StringIO()
        self.finished = False
        self.error = None
        self.result = None
        self.lock = threading.Lock()
        owner = self

        class Result(unittest.TextTestResult):
            def startTest(self, test):
                owner.events.put("ready")
                # A disconnected client must not leave a blocked worker forever.
                if not owner.permit.wait(3600):
                    raise TimeoutError(
                        "plugin-test session expired awaiting its next operation"
                    )
                owner.permit.clear()
                super().startTest(test)

            def addSuccess(self, test):
                super().addSuccess(test)
                owner.outcomes.append(dict(test=test.id(), status="success", detail=""))

            def addFailure(self, test, err):
                super().addFailure(test, err)
                owner.outcomes.append(
                    dict(test=test.id(), status="failure", detail=self.failures[-1][1])
                )

            def addError(self, test, err):
                super().addError(test, err)
                owner.outcomes.append(
                    dict(test=test.id(), status="error", detail=self.errors[-1][1])
                )

            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                owner.outcomes.append(
                    dict(test=test.id(), status="skipped", detail=reason)
                )

        self.runner = unittest.TextTestRunner(stream=self.stream, resultclass=Result)
        # Retain the result before the first test boundary, using runner's normal
        # factory, and still let TextTestRunner.run own start/stop/summary.
        self.result = self.runner._makeResult()
        self.runner._makeResult = lambda: self.result
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()
        self._wait()

    def _run(self):
        try:
            self.runner.run(self.suite)
        except BaseException as error:
            self.error = error
        finally:
            self.finished = True
            self.events.put("finished")

    def _wait(self):
        self.events.get()
        if self.error is not None:
            raise RuntimeError("native unittest runner aborted") from self.error

    def state(self):
        return dict(
            session=self.token,
            tests=self.names,
            index=self.result.testsRun,
            outcomes=deepcopy(self.outcomes),
            should_stop=self.result.shouldStop,
        )

    def check(self, state):
        if state != self.state():
            raise ValueError("stale or modified unittest state")

    def advance(self, state):
        with self.lock:
            self.check(state)
            if self.finished:
                raise ValueError("suite already exhausted")
            self.permit.set()
            self._wait()
            return dict(state=self.state(), done=self.finished)

    def finish(self, state):
        with self.lock:
            self.check(state)
            if not self.finished:
                raise ValueError("suite has not stopped")
            self.worker.join()
            successful = self.result.wasSuccessful()
            return dict(
                result=dict(
                    successful=successful,
                    exit_code=0 if successful else 1,
                    tests_run=self.result.testsRun,
                    state=self.state(),
                    runner_output=self.stream.getvalue(),
                )
            )


class Initialized(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    result: dict


def register_plugin_test_tools(mcp):
    sessions = {}

    def session(state):
        try:
            return sessions[state["session"]]
        except KeyError as error:
            raise ValueError("unknown or finalized unittest session") from error

    @mcp.tool()
    def mathformer_plugin_test_initialize(repository_root: str) -> Initialized:
        """Discover the selected native suite in its explicit repository context."""
        live = Session(repository_root)
        sessions[live.token] = live
        return {"state": live.state()}

    @mcp.tool()
    def mathformer_plugin_test_next(state: dict) -> Advanced:
        """Advance one native unittest, continuing after ordinary failures/errors."""
        return session(state).advance(state)

    @mcp.tool()
    def mathformer_plugin_test_finish(state: dict) -> Finished:
        """Return unittest's accumulated result and unmodified runner transcript."""
        live = session(state)
        output = live.finish(state)
        # stdout belongs to MCP; preserve the source runner's human transcript.
        sys.stderr.write(output["result"]["runner_output"])
        del sessions[live.token]
        return output


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("mathformer-plugin-test")
    register_plugin_test_tools(server)
    server.run(transport="stdio")

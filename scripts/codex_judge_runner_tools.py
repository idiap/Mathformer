# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the native runner, specialized to the hub's limit of one.

CLI working directory is explicit. Native prompt files, resume precedence,
provider invocation, parsing, and persistence remain owned by the source.
"""

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
from threading import RLock
from typing_extensions import TypedDict

from codex_judge_self_test_tools import source

_LOCK = RLock()


class Context(TypedDict):
    working_directory: str


class Initialized(TypedDict):
    state: dict
    parallel: bool
    nonempty: bool


class State(TypedDict):
    state: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Persisted(TypedDict):
    manifest: dict


def native_args(args):
    if args.get("limit") != 1 or args.get("self_test", False):
        raise ValueError("runner contract requires limit=1 and self_test=false")
    values = dict(
        self_test=False,
        json=False,
        **{k: v for k, v in args.items() if k not in ("self_test", "json")},
    )
    values.update({k: args[k] for k in ("self_test", "json") if k in args})
    values["prompts_json"] = Path(values["prompts_json"])
    values["output_dir"] = Path(values["output_dir"])
    return argparse.Namespace(**values)


@contextmanager
def invocation(args, context, write_guard, state=None):
    directory = Path(context["working_directory"])
    if not directory.is_absolute():
        raise ValueError("working_directory must be absolute")
    with _LOCK:
        previous = Path.cwd()
        try:
            os.chdir(directory)
            native = native_args(args)
            write_guard(native.output_dir.resolve())
            if state is not None:
                if state["args"] != {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in vars(native).items()
                }:
                    raise ValueError("state arguments differ from invocation")
                # Recheck every transported write path under the service policy.
                for path in state["artifacts"].values():
                    write_guard(Path(path).resolve())
            yield native
        except SystemExit as error:
            # Native preflight failure must fail the call, not terminate MCP.
            raise RuntimeError(str(error)) from error
        finally:
            os.chdir(previous)


def register_codex_judge_runner_tools(mcp, write_guard):
    @mcp.tool()
    def mathformer_codex_judge_runner_initialize(
        args: dict, context: Context
    ) -> Initialized:
        """Create directories, filter/slice prompts and persist selection."""
        with invocation(args, context, write_guard) as native:
            state = source().initialize_run(native)
            return {
                "state": state,
                "parallel": native.execute and native.workers > 1,
                "nonempty": bool(state["selected"]),
            }

    @mcp.tool()
    def mathformer_codex_judge_runner_parallel_batch(
        args: dict, state: dict, context: Context
    ) -> State:
        """Run the native bounded thread pool and ordered join, including empty input."""
        with invocation(args, context, write_guard, state) as native:
            source().parallel_run_rows(native, state)
            return {"state": state}

    @mcp.tool()
    def mathformer_codex_judge_runner_append_row(
        args: dict, state: dict, context: Context
    ) -> Advanced:
        """Append the next native row; completion is checked after the append."""
        with invocation(args, context, write_guard, state) as native:
            done = source().append_run_row(native, state)
            return {"state": state, "done": done}

    @mcp.tool()
    def mathformer_codex_judge_runner_empty_state(state: dict) -> State:
        """Export unchanged state for the native empty sequential loop."""
        return {"state": state}

    @mcp.tool()
    def mathformer_codex_judge_runner_persist(
        args: dict, state: dict, context: Context
    ) -> Persisted:
        """Write native results, then manifest; exceptions propagate without retry."""
        with invocation(args, context, write_guard, state) as native:
            return {"manifest": source().persist_run(native, state)}

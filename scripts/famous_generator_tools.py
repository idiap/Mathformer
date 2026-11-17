# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for the shared famous theorem generator steps."""

from contextlib import redirect_stdout
from functools import lru_cache
import importlib.util
import io
from pathlib import Path
import sys
from typing_extensions import TypedDict


@lru_cache(maxsize=1)
def source():
    path = (
        Path(__file__).resolve().parents[1]
        / "skills/premise-kb/premise-kb-theorem-seed-generator/scripts/generate_famous_theorem_axiom_corpus.py"
    )
    spec = importlib.util.spec_from_file_location("_famous_generator_native", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Parsed(TypedDict):
    options: dict
    state: dict


class State(TypedDict):
    state: dict


class Transition(TypedDict):
    state: dict
    done: bool


class Entries(TypedDict):
    entries: list[dict]


class Written(TypedDict):
    result: dict
    exit_code: int
    stdout: str


def decode(state):
    return {
        **state,
        "entries": [source().KBEntry.from_dict(e) for e in state["entries"]],
    }


def encode(state):
    return {**state, "entries": [e.to_dict() for e in state["entries"]]}


def register_famous_generator_tools(mcp, guard=lambda path: None):
    @mcp.tool()
    def mathformer_seed_parse(argv: list[str]) -> Parsed:
        # Argparse's SystemExit must be an MCP failure, not kill the server.
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                return source().parse_seed(argv)
        except SystemExit as error:
            raise ValueError(
                f"Argument parsing exited with code {error.code}"
            ) from error
        finally:
            # --help writes stdout before exiting; keep stdio protocol intact.
            print(out.getvalue(), end="", file=sys.stderr)

    @mcp.tool()
    def mathformer_seed_open(state: dict) -> State:
        return {"state": source().open_domain(state)}

    @mcp.tool()
    def mathformer_seed_append(state: dict) -> Transition:
        result = source().append_entry(decode(state))
        return {**result, "state": encode(result["state"])}

    @mcp.tool()
    def mathformer_seed_advance(state: dict) -> Transition:
        return source().advance_domain(state)

    @mcp.tool()
    def mathformer_seed_slice(state: dict, options: dict) -> Entries:
        return {"entries": source().check_slice(state, options)}

    @mcp.tool()
    def mathformer_seed_write(entries: list[dict], options: dict) -> Written:
        output = Path(options["output"])
        guard(output if output.is_absolute() else source().REPO_ROOT / output)
        out = io.StringIO()
        with redirect_stdout(out):
            result = source().write_report(
                [source().KBEntry.from_dict(e) for e in entries], options
            )
        print(out.getvalue(), end="", file=sys.stderr)
        return {**result, "stdout": out.getvalue()}

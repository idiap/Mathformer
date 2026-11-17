# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable MCP ports for the native Wiki-level suite stages."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tests/wiki_level/run_suite.py"


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location("wiki_suite_native", ROOT / SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared(TypedDict):
    session: dict
    state: dict
    has_cases: bool
    skip_declarations: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Retained(TypedDict):
    state: dict


class Checked(TypedDict):
    check: dict


class Finished(TypedDict):
    report: dict


def register_wiki_suite_tools(mcp, write_policy):
    @mcp.tool()
    def mathformer_wiki_suite_prepare(manifest: str, options: dict) -> Prepared:
        write_policy()
        native = source()
        args = native.parse_args([])
        for key, value in options.items():
            if key not in vars(args) or key in ("manifest", "json"):
                raise ValueError(f"Unknown suite option: {key}")
            setattr(args, key, value)
        args.manifest = Path(manifest)
        args.output_dir = Path(args.output_dir)
        args.reasoning_log = Path(args.reasoning_log)
        return native.prepare_suite(args, max_cases=1000)

    @mcp.tool()
    def mathformer_wiki_suite_case_step(session: dict, state: dict) -> Advanced:
        write_policy()
        return source().advance_case(session, state)

    @mcp.tool()
    def mathformer_wiki_suite_empty_cases(state: dict) -> Advanced:
        return {"state": state, "done": True}

    @mcp.tool()
    def mathformer_wiki_suite_compile_gold(session: dict) -> Checked:
        write_policy()
        return {"check": source().compile_suite_gold(session)}

    @mcp.tool()
    def mathformer_wiki_suite_audit(session: dict) -> Checked:
        write_policy()
        return {"check": source().audit_suite(session)}

    @mcp.tool()
    def mathformer_wiki_suite_check_declarations(session: dict, state: dict) -> Checked:
        write_policy()
        return {"check": source().check_suite_declarations(session, state)}

    @mcp.tool()
    def mathformer_wiki_suite_skip_declarations() -> Checked:
        return {"check": source().skipped_declarations()}

    @mcp.tool()
    def mathformer_wiki_suite_finish(
        session: dict, state: dict, lean: dict, audit: dict, declarations: dict
    ) -> Finished:
        write_policy()
        return {
            "report": source().finish_suite(session, state, lean, audit, declarations)
        }


def create_server(*, readonly: bool = False):
    """Create the standalone suite service using the same production registration."""
    from mcp.server.fastmcp import FastMCP

    def write_policy():
        if readonly:
            raise ValueError(
                "Wiki suite writes are disabled by the service read-only policy"
            )

    mcp = FastMCP("mathformer-wiki-suite")
    register_wiki_suite_tools(mcp, write_policy)
    return mcp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readonly", action="store_true")
    create_server(readonly=parser.parse_args().readonly).run(transport="stdio")

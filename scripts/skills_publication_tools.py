# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""JSON ports for link_agent_skills.main's all-repo specialization.

Only cursor packing is adapter-owned. Discovery, target resolution, publication
and completion rendering use the CLI implementation. Service authorization is
checked before each filesystem mutation; native errors propagate without rollback.
"""

import argparse
from contextlib import redirect_stdout
from dataclasses import asdict
import io
from pathlib import Path
import sys
from typing import Literal
from typing_extensions import TypedDict

import link_agent_skills as native


class Options(TypedDict):
    source: Literal["skills/"]
    profile: Literal["all-repo"]
    mode: Literal["auto", "symlink", "copy"]
    replace: bool
    dry_run: bool
    json: bool
    max_discovered_skills: Literal[1024]


class Result(TypedDict):
    skill: str
    source: str
    target: str
    mode: Literal["auto", "symlink", "copy"]
    status: Literal["created", "unchanged", "skipped"]
    detail: str


class State(TypedDict):
    skills: list[str]
    targets: list[str]
    target_index: int
    skill_index: int
    results: list[Result]


class Discovered(TypedDict):
    skills: list[str]


class Packed(TypedDict):
    state: State


class Advanced(TypedDict):
    state: State
    done: bool


class Finished(TypedDict):
    returncode: Literal[0]
    stdout: str


def register_skills_publication_tools(mcp, authorize, path_allowed):
    def check(state, *, publishing=False):
        n, t, s = len(state["skills"]), state["target_index"], state["skill_index"]
        if (
            not 1 <= n <= 1024
            or len(state["targets"]) != 3
            or not 0 <= t <= 3
            or not 0 <= s <= n
        ):
            raise ValueError("publication cursor outside admitted domain")
        if publishing and (t == 3 or s == n):
            raise ValueError("publication cursor exhausted")

    def guard(target, options, destination=None):
        if not options["dry_run"]:
            authorize()
            if not path_allowed(target) or (
                destination is not None and not path_allowed(destination)
            ):
                raise ValueError("skill publication outside configured service roots")

    @mcp.tool()
    def mathformer_skills_publication_discover(
        options: Options, repository_root: str
    ) -> Discovered:
        source = (
            Path(repository_root).expanduser().resolve() / options["source"]
        ).resolve()
        try:
            skills = native.discover_skills(source)
        except SystemExit as error:
            # A CLI admission error must fail this call, not terminate MCP.
            raise ValueError(str(error)) from error
        if len(skills) > options["max_discovered_skills"]:
            raise ValueError(
                "discovered skills exceed descriptor admission bound of 1024"
            )
        return {"skills": [str(path) for path in skills]}

    @mcp.tool()
    def mathformer_skills_publication_resolve_and_pack(
        options: Options, skills: list[str], repository_root: str
    ) -> Packed:
        root = Path(repository_root).expanduser().resolve()
        # Explicit mount of the unchanged all-repo profile, in native order.
        targets = [
            root / path.relative_to(native.REPO_ROOT)
            for path in native.PROFILE_TARGETS[options["profile"]]
        ]
        resolved = native.resolve_targets(
            argparse.Namespace(target=targets, profile=options["profile"])
        )
        state = dict(
            skills=skills,
            targets=[str(path) for path in resolved],
            target_index=0,
            skill_index=0,
            results=[],
        )
        check(state)
        return {"state": state}

    @mcp.tool()
    def mathformer_skills_publication_prepare_target(
        state: State, options: Options
    ) -> Packed:
        check(state)
        if state["target_index"] == 3:
            raise ValueError("target cursor exhausted")
        target = Path(state["targets"][state["target_index"]])
        guard(target, options)
        prepared = native.prepare_publication_target(target, options["dry_run"])
        targets = list(state["targets"])
        targets[state["target_index"]] = str(prepared)
        return {"state": {**state, "targets": targets, "skill_index": 0}}

    @mcp.tool()
    def mathformer_skills_publication_publish_and_advance(
        state: State, options: Options
    ) -> Advanced:
        check(state, publishing=True)
        source = Path(state["skills"][state["skill_index"]]).resolve()
        target = Path(state["targets"][state["target_index"]])
        guard(target, options, target / source.name)
        result = native.publish_one(
            source, target, options["mode"], options["replace"], options["dry_run"]
        )
        index = state["skill_index"] + 1
        return {
            "state": {
                **state,
                "skill_index": index,
                "results": [*state["results"], asdict(result)],
            },
            "done": index == len(state["skills"]),
        }

    @mcp.tool()
    def mathformer_skills_publication_advance_target(state: State) -> Advanced:
        check(state)
        if state["target_index"] == 3 or state["skill_index"] != len(state["skills"]):
            raise ValueError("target advancement requires completed skill pass")
        index = state["target_index"] + 1
        return {
            "state": {**state, "target_index": index},
            "done": index == len(state["targets"]),
        }

    @mcp.tool()
    def mathformer_skills_publication_finish(
        state: State, options: Options
    ) -> Finished:
        check(state)
        if state["target_index"] != 3 or len(state["results"]) != 3 * len(
            state["skills"]
        ):
            raise ValueError("publication completion requires all three target passes")
        output = io.StringIO()
        with redirect_stdout(output):
            code = native.finish_publication(
                [native.LinkResult(**row) for row in state["results"]], options["json"]
            )
        # stdout is a protocol channel for stdio MCP. Preserve source output in
        # a typed port and the server's stderr, without corrupting MCP framing.
        text = output.getvalue()
        print(text, end="", file=sys.stderr)
        return {"returncode": code, "stdout": text}

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only typed boundaries for portable_adoption.main's describe branch."""

from typing_extensions import TypedDict

from catalog_check_tools import source, repository_path, complete, CAUGHT


class Parsed(TypedDict):
    identity: str


class Failure(TypedDict):
    ok: bool
    error: str


class Loaded(TypedDict):
    loaded: bool
    metadata: dict | None
    failure: Failure | None


class Completion(TypedDict):
    returncode: int
    json: dict


class Finished(TypedDict):
    result: Completion


def register_adoption_describe_tools(mcp):
    @mcp.tool()
    def mathformer_describe_parse(extra_args: list[str]) -> Parsed:
        try:
            return {
                "identity": source().parse_arguments(["describe", *extra_args]).identity
            }
        except SystemExit as error:
            # An argparse termination is a failed tool call, never a server exit.
            raise ValueError(f"argparse exited with status {error.code}") from error

    @mcp.tool()
    def mathformer_describe_load(metadata_path: str = "") -> Loaded:
        try:
            data, _ = source().load_contract(
                repository_path(metadata_path, source().METADATA)
            )
            return {"loaded": True, "metadata": data, "failure": None}
        except CAUGHT as error:
            return {
                "loaded": False,
                "metadata": None,
                "failure": source().error_result(error),
            }

    @mcp.tool()
    def mathformer_describe_emit(identity: str, metadata: dict | None) -> Finished:
        try:
            return {"result": complete(source().describe_result(identity, metadata))}
        except CAUGHT as error:
            return {"result": complete(source().error_result(error), 2)}

    @mcp.tool()
    def mathformer_describe_error(failure: Failure | None = None) -> Finished:
        # The load branch supplies this port exclusively on failure.
        return {"result": complete(failure, 2)}

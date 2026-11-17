# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP bindings for native catalogue construction, disposition and emission."""

from contextlib import redirect_stdout
from pathlib import Path
import sys
from threading import Lock
from typing_extensions import TypedDict
from reasoning_catalog_tools import Context, Constructed, source

_EMISSION_LOCK = Lock()


class Request(TypedDict):
    flows_dir: str
    output_file: str
    materializations_file: str
    check: bool
    json: bool


class Payload(TypedDict):
    payload: dict


class Emitted(TypedDict):
    result: dict
    exit_code: int


def paths(context, request):
    native = source(context)
    root = Path(context["repository_root"]).resolve()
    resolved = []
    for key in ("flows_dir", "output_file", "materializations_file"):
        path = Path(request[key]).resolve()
        path.relative_to(root)
        resolved.append(path)
    return native, resolved


def register_reasoning_catalog_render_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_catalog_render_construct(
        request: Request, context: Context
    ) -> Constructed:
        native, values = paths(context, request)
        return {"construction": native.construct_catalog(values[0])}

    @mcp.tool()
    def mathformer_reasoning_catalog_render_compare(
        request: Request, context: Context, construction: dict
    ) -> Payload:
        native, values = paths(context, request)
        return {
            "payload": native.dispose_catalog(construction, values[1], values[2], True)
        }

    @mcp.tool()
    def mathformer_reasoning_catalog_render_generate(
        request: Request, context: Context, construction: dict
    ) -> Payload:
        native, values = paths(context, request)
        return {
            "payload": native.dispose_catalog(construction, values[1], values[2], False)
        }

    @mcp.tool()
    def mathformer_reasoning_catalog_render_emit(
        request: Request, context: Context, payload: dict
    ) -> Emitted:
        native, _ = paths(context, request)
        # MCP owns stdout. Preserve the native text on the diagnostic stream.
        with _EMISSION_LOCK, redirect_stdout(sys.stderr):
            emitted = native.emit_catalog_result(payload, request["json"])
        return {"result": emitted["payload"], "exit_code": emitted["exit_code"]}

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Callable ports for the registry main graph, using independent native contexts.

A fresh module namespace binds the source's four path constants per invocation;
no shared module globals are mutated, and all registry algorithms remain native.
The root layout deliberately matches the source, including its legacy lib path.
"""

from contextlib import redirect_stdout
import importlib.util
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]


class Context(TypedDict):
    repository_root: str
    allow_mutating: bool


class Flags(TypedDict):
    write: bool
    check: bool
    json: bool


class Built(TypedDict):
    rows: list[dict]
    rows_json: str


class Discovered(TypedDict):
    rows: list[dict]


class Guarded(TypedDict):
    required: bool


class Checked(TypedDict):
    errors: list[str]


class Emitted(TypedDict):
    result: dict


def source(context: Context):
    spec = importlib.util.spec_from_file_location(
        "physics_registry_context", ROOT / "scripts/build_physics_registry.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    root = Path(context["repository_root"]).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository_root must be a directory")
    module.REPO_ROOT = root
    module.LIB_ROOT = root / "MathformerPhysicsLib"
    module.MANIFEST = module.LIB_ROOT / "MANIFEST.json"
    module.README = module.LIB_ROOT / "README.md"
    return module


def register_physics_registry_tools(mcp, before_write, path_allowed):
    @mcp.tool()
    def mathformer_physics_registry_discover(context: Context) -> Discovered:
        """Read native registry rows for the fixed read-only check workflow."""
        return {"rows": source(context).build_registry()}

    @mcp.tool()
    def mathformer_physics_registry_build(context: Context) -> Built:
        rows = source(context).build_registry()
        return {"rows": rows, "rows_json": json.dumps(rows)}

    @mcp.tool()
    def mathformer_physics_registry_write(
        rows: list[dict], rows_json: str, context: Context
    ) -> dict:
        before_write()
        if not context["allow_mutating"]:
            raise ValueError("registry writes require mutation authorization")
        native = source(context)
        if not all(
            path_allowed(path.resolve()) for path in (native.MANIFEST, native.README)
        ):
            raise ValueError("registry outputs are outside service write roots")
        ordered = json.loads(rows_json)
        if ordered != rows:
            raise ValueError("ordered row transport differs from typed rows")
        native.write_registry(ordered)
        return {}

    @mcp.tool()
    def mathformer_physics_registry_skip_write() -> dict:
        from build_physics_registry import skip_write

        skip_write()
        return {}

    @mcp.tool()
    def mathformer_physics_registry_skip_check() -> Checked:
        from build_physics_registry import no_errors

        return {"errors": no_errors()}

    @mcp.tool()
    def mathformer_physics_registry_check_guard(flags: Flags) -> Guarded:
        from build_physics_registry import check_required

        return {"required": check_required(flags)}

    @mcp.tool()
    def mathformer_physics_registry_check(
        rows: list[dict], context: Context
    ) -> Checked:
        return {"errors": source(context).validate_registry(rows)}

    @mcp.tool()
    def mathformer_physics_registry_emit(
        flags: Flags, rows: list[dict], errors: list[str], context: Context
    ) -> Emitted:
        # stdout belongs to MCP. Preserve the source's console emission on stderr
        # and expose the exact native bytes in the typed result.
        with redirect_stdout(sys.stderr):
            result = source(context).emit_result(flags, rows, errors)
        return {"result": result}

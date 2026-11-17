# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports for shared native library documentation stages."""

from contextlib import redirect_stdout
from dataclasses import asdict
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "skills/mathformerlib/mathformer-library-docs-generator/scripts/generate_mathformer_library_docs.py"
)
ARGV = ["--output-dir", "docs/libraries/mathformerlib"]


class Context(TypedDict):
    repository_root: str


class Configured(TypedDict):
    config: dict


class Collected(TypedDict):
    modules: list[dict]


class Published(TypedDict):
    manifest: dict


class Completed(TypedDict):
    result: dict


def source(context):
    """Load real source with an explicit repository filesystem context."""
    root = Path(context["repository_root"]).resolve()
    if root != ROOT and not root.is_relative_to(ROOT / "artifacts/workflow_hub"):
        raise ValueError(
            "repository context must be the repository or a workflow_hub workspace"
        )
    if not root.is_dir():
        raise ValueError("repository context must exist")
    spec = importlib.util.spec_from_file_location("_library_docs_native", SOURCE)
    native = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = native
    spec.loader.exec_module(native)
    native.REPO_ROOT = root
    return native


def configuration(native):
    args = native.parse_args(ARGV)
    return dict(
        roots=[
            str(p)
            for p in (
                args.include_root
                or [
                    Path("MathformerLib"),
                    Path("libraries/MathformerLib.lean"),
                    Path("Mathformer"),
                ]
            )
        ],
        output_dir=str(args.output_dir),
        registry_file=None,
        reasoning_log_file=None,
        expect_docs=False,
        self_test=False,
        json=False,
    )


def validate_config(native, config):
    if config != configuration(native):
        raise ValueError(
            "configuration must match the registered docs:library invocation"
        )
    return native.parse_args(ARGV)


def register_library_docs_tools(mcp, write_policy=lambda: None):
    @mcp.tool()
    def mathformer_library_docs_configure(
        argv: list[str], context: Context
    ) -> Configured:
        if argv != ARGV:
            raise ValueError("docs:library rejects extra or alternate arguments")
        native = source(context)
        args = native.parse_args(argv)
        roots = native.prepare_generation(args)
        config = configuration(native)
        config["roots"] = [str(p) for p in roots]
        return {"config": config}

    @mcp.tool()
    def mathformer_library_docs_collect_modules(
        config: dict, context: Context
    ) -> Collected:
        native = source(context)
        validate_config(native, config)
        modules = native.collect_docs([Path(p) for p in config["roots"]], None)
        return {
            "modules": json.loads(json.dumps([asdict(m) for m in modules], default=str))
        }

    @mcp.tool()
    def mathformer_library_docs_publish_docs(
        config: dict, modules: list[dict], context: Context
    ) -> Published:
        native = source(context)
        args = validate_config(native, config)
        write_policy()
        output = (native.REPO_ROOT / args.output_dir).resolve()
        output.relative_to(native.REPO_ROOT)
        records = []
        for row in modules:
            values = dict(row)
            values["path"] = Path(values["path"])
            if values["module_comment"] is not None:
                values["module_comment"] = native.DocComment(**values["module_comment"])
            declarations = []
            for declaration in values["declarations"]:
                fields = dict(declaration)
                if fields["comment"] is not None:
                    fields["comment"] = native.DocComment(**fields["comment"])
                declarations.append(native.Declaration(**fields))
            values["declarations"] = declarations
            record = native.ModuleDoc(**values)
            (
                output / "modules" / native.module_page_name(record.module)
            ).resolve().relative_to(output / "modules")
            records.append(record)
        return {
            "manifest": native.publish_docs(
                [Path(p) for p in config["roots"]], args.output_dir, records
            )
        }

    @mcp.tool()
    def mathformer_library_docs_complete_main(
        config: dict, manifest: dict, context: Context
    ) -> Completed:
        native = source(context)
        args = validate_config(native, config)
        stream = io.StringIO()
        with redirect_stdout(stream):
            code = native.complete_generation(args, manifest)
        text = stream.getvalue()
        print(text, end="", file=sys.stderr)
        return {"result": {"returncode": code, "stdout": text, "manifest": manifest}}

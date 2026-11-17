# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Typed MCP interfaces over the chapter coordinator's shared native steps."""

from functools import lru_cache
import importlib.util
import json
from pathlib import Path
from typing_extensions import TypedDict
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "skills/latex-textbook/textbook-chapter-autoformalization-orchestrator/scripts/orchestrate_textbook_chapters.py"
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/textbook-chapter.workflow.json"
)


@lru_cache(maxsize=1)
def chapter_source():
    spec = importlib.util.spec_from_file_location(
        "textbook_chapter_native", ROOT / SOURCE
    )
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    return native


def native_options(native, options):
    """Use native parser defaults, converting the two native Path options."""
    args = native.parse_args([])
    for key, value in options.items():
        setattr(
            args,
            key,
            (
                Path(value)
                if key in {"archive", "source_dir"} and value is not None
                else value
            ),
        )
    return args


class Inventoried(TypedDict):
    state: dict
    has_chapters: bool


class Prepared(TypedDict):
    prepared: dict


class Advanced(TypedDict):
    state: dict
    done: bool


class Planned(TypedDict):
    plan: dict


def register_textbook_chapter_tools(
    mcp, authorize=lambda: None, path_allowed=lambda p: True
):
    def invoke(operation, values):
        document = json.loads(AUTHORED.read_text())
        signature = document["operations"][operation]

        def validate(ports, payload):
            Draft202012Validator(
                dict(
                    type="object",
                    additionalProperties=False,
                    required=[k for k, v in ports.items() if v.get("required", True)],
                    properties={
                        k: document["types"][v["type"]]["schema"]
                        for k, v in ports.items()
                    },
                )
            ).validate(payload)

        validate(signature["inputs"], values)
        # Copy transported values before native code mutates per-chapter records.
        values = json.loads(json.dumps(values))
        native = chapter_source()
        args = native_options(native, values.get("options", {}))
        if operation in {"prepare_chapter", "run_objects", "write_plan"}:
            authorize()
            paths = [Path(values["output_dir"])]
            if operation == "run_objects":
                paths.append(Path(values["prepared"]["entry"]["batch_manifest"]))
                # Native gate subprocesses also own these default report paths.
                paths.extend(
                    native.REPO_ROOT / "artifacts" / p
                    for p in [
                        "lean_consistency",
                        "reference_free_critic_monitor",
                        "reasoning_logs",
                    ]
                )
            if any(not path_allowed(path.resolve()) for path in paths):
                raise PermissionError("Chapter artifacts outside service write roots")
        if operation == "inventory_and_pack":
            state = native.inventory_and_pack(args, values["full_report"])
            state["has_chapters"] = bool(state["remaining"])
            result = dict(state=state, has_chapters=state["has_chapters"])
        elif operation == "prepare_chapter":
            result = dict(
                prepared=native.prepare_chapter(
                    values["state"],
                    args,
                    values["full_report"],
                    Path(values["output_dir"]),
                )
            )
        elif operation == "run_objects":
            result = dict(
                prepared=native.run_objects(
                    values["prepared"], args, Path(values["output_dir"])
                )
            )
        elif operation == "append_and_advance":
            state = native.append_and_advance(values["state"], values["prepared"])
            state["has_chapters"] = bool(state["remaining"])
            result = dict(state=state, done=not state["has_chapters"])
        elif operation == "empty_selection":
            if values["state"]["remaining"]:
                raise ValueError(
                    "Empty-selection adapter requires an exhausted inventory"
                )
            result = dict(state=values["state"], done=True)
        elif operation == "write_plan":
            result = dict(
                plan=native.write_plan(
                    values["state"],
                    args,
                    Path(values["theory_path"]),
                    Path(values["output_dir"]),
                )
            )
        else:
            raise ValueError(operation)
        validate(signature["outputs"], result)
        return result

    @mcp.tool()
    def mathformer_textbook_chapter_inventory(
        options: dict, full_report: dict
    ) -> Inventoried:
        """Inventory chapters, apply native selectors and pack ordered finite state."""
        return invoke(
            "inventory_and_pack", dict(options=options, full_report=full_report)
        )

    @mcp.tool()
    def mathformer_textbook_chapter_prepare(
        state: dict, options: dict, full_report: dict, output_dir: str
    ) -> Prepared:
        """Write the chapter inventory and run native section organizer and queue builder."""
        return invoke(
            "prepare_chapter",
            dict(
                state=state,
                options=options,
                full_report=full_report,
                output_dir=output_dir,
            ),
        )

    @mcp.tool()
    def mathformer_textbook_chapter_run(
        prepared: dict, options: dict, output_dir: str
    ) -> Prepared:
        """Run an explicitly selected chapter's native batch and attach its summary."""
        return invoke(
            "run_objects",
            dict(prepared=prepared, options=options, output_dir=output_dir),
        )

    @mcp.tool()
    def mathformer_textbook_chapter_advance(state: dict, prepared: dict) -> Advanced:
        """Accumulate entries and commands and stop on selection exhaustion."""
        return invoke("append_and_advance", dict(state=state, prepared=prepared))

    @mcp.tool()
    def mathformer_textbook_chapter_write(
        state: dict, options: dict, theory_path: str, output_dir: str
    ) -> Planned:
        """Persist and return the native chapter plan, including an empty selection."""
        return invoke(
            "write_plan",
            dict(
                state=state,
                options=options,
                theory_path=theory_path,
                output_dir=output_dir,
            ),
        )

    @mcp.tool()
    def mathformer_textbook_chapter_empty(state: dict) -> Advanced:
        """Return an empty inventory unchanged without invoking chapter preparation."""
        return invoke("empty_selection", dict(state=state))

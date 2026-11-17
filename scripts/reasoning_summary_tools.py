# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Read-only MCP bindings to the shared native summary steps."""

import importlib.util
from functools import lru_cache
from pathlib import Path
from typing_extensions import TypedDict

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    "skills/control/reasoning-log-schema-guardian/scripts/summarize_reasoning_log.py"
)


@lru_cache(maxsize=1)
def source():
    spec = importlib.util.spec_from_file_location(
        "reasoning_summary_native", ROOT / SOURCE
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Loaded(TypedDict):
    events: list[dict]


class Validated(TypedDict):
    validation: dict


class Audited(TypedDict):
    quality: dict


class Initialized(TypedDict):
    state: dict
    empty: bool


class Advanced(TypedDict):
    state: dict
    done: bool


class Finished(TypedDict):
    summary: dict


def register_reasoning_summary_tools(mcp):
    @mcp.tool()
    def mathformer_reasoning_summary_load(log_file: str) -> Loaded:
        events = source().load_events(Path(log_file))
        if len(events) > 10000:
            raise ValueError(
                "Log exceeds workflow admission limit of 10000 loaded events"
            )
        return {"events": events}

    @mcp.tool()
    def mathformer_reasoning_summary_validate(
        log_file: str, hooks_file: str
    ) -> Validated:
        return {
            "validation": source().validate_summary_log(
                Path(log_file), hooks_file=Path(hooks_file)
            )
        }

    @mcp.tool()
    def mathformer_reasoning_summary_audit(log_file: str, hooks_file: str) -> Audited:
        return {
            "quality": source().audit_logs(
                [Path(log_file)], hooks_file=Path(hooks_file)
            )
        }

    @mcp.tool()
    def mathformer_reasoning_summary_initialize(events: list[dict]) -> Initialized:
        return source().initialize_summary(events)

    @mcp.tool()
    def mathformer_reasoning_summary_advance(
        events: list[dict], state: dict
    ) -> Advanced:
        # Lunar loops execute at least once. Empty input performs no event body.
        if not events and state["cursor"] == 0:
            return {"state": state, "done": True}
        return source().advance_summary(events, state)

    @mcp.tool()
    def mathformer_reasoning_summary_finish(
        log_file: str, events: list[dict], validation: dict, quality: dict, state: dict
    ) -> Finished:
        return {
            "summary": source().finish_summary(
                Path(log_file), events, validation, quality, state
            )
        }

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic logs and an isolated copy of the real renderer, no providers.

No compiler/model exists in this route. Generic external compiler capture tests
use reasoning_route_compiler; the renderer itself is never substituted.
"""

import json
from pathlib import Path
import shutil

DIRECTORY = Path("skills/control/reasoning-log-schema-guardian/scripts")
RENDERER = str(DIRECTORY / "render_reasoning_log_html.py")
LOG = Path("artifacts/reasoning/self_test/good.jsonl")


def populate(root, source):
    for name in (
        "render_reasoning_log_html.py",
        "render_reasoning_log.py",
        "validate_reasoning_log.py",
        "audit_reasoning_log_quality.py",
        "reasoning_log.py",
    ):
        target = root / DIRECTORY / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / DIRECTORY / name, target)


def events(count=2):
    result = []
    for index in range(1, count + 1):
        result.append(
            {
                "event_index": index,
                "timestamp_utc": "2026-07-08T00:00:00+00:00",
                "timestamp_unix_ms": 1783468800000 + index,
                "monotonic_ns": index,
                "elapsed_ms_since_log_start": index,
                "elapsed_ms_since_prev_event": 1,
                "step": (
                    "skill_application_start"
                    if index == 1
                    else "skill_application_complete"
                ),
                "payload": {
                    "skill_application": {
                        "schema_version": 1,
                        "skill": "fixture-skill",
                        "skill_call_id": "fixture-call",
                        "status": "running" if index == 1 else "complete",
                        "intent": "Inspect <evidence>",
                        "inputs": {},
                        "artifacts": {},
                        "evidence": {},
                        "decision": {},
                        "risks": {},
                        "next_action": "Review fixture",
                        "human_summary": "Finished & checked",
                    }
                },
            }
        )
    return result


def write_log(root, content=None, count=2):
    target = root / LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        content
        if content is not None
        else "".join(json.dumps(e) + "\n" for e in events(count))
    )
    return target

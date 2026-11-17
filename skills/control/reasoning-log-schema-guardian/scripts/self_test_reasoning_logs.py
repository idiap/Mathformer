#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# ruff: noqa: E402 - imports follow explicit direct-script path setup
#
#

# File Documentation
#
# Motivation:
#   Protect the reasoning-log contract with a deterministic smoke test.
#
# Intent:
#   Exercise the shared skill-application helpers, strict validation, Markdown
#   and HTML rendering, and repository coverage audit in one dependency-free
#   command.
#
# Function:
#   Creates a temporary reasoning log, validates it, renders it to Markdown and
#   HTML, audits coverage, and returns a JSON-compatible result.
#
# Maintenance Notes:
#   Keep this test small. It should fail only when the shared contract breaks,
#   not when a domain backend such as Lean, Vampire, or SymPy is unavailable.

"""Self-test the Mathformer reasoning-log contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any, Dict, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from audit_skill_reasoning_log_coverage import audit as audit_coverage  # noqa: E402
from reasoning_log import (  # noqa: E402
    append_skill_complete,
    append_skill_progress,
    append_skill_start,
)
from render_reasoning_log_html import render_html_dashboard  # noqa: E402
from render_reasoning_log import (
    build_summary,
    load_events,
    render_markdown,
)  # noqa: E402
from validate_reasoning_log import validate_reasoning_log  # noqa: E402


def create_fixture(root: Path) -> Dict[str, Any]:
    """Append the three native events within a caller-owned temporary scope."""
    log_file = root / "reasoning.jsonl"
    rendered_file = root / "reasoning.md"
    html_file = root / "reasoning.html"
    call_id = append_skill_start(
        log_file,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        run_id="reasoning-log-self-test",
        intent="Validate that skill-application logs are self-explaining.",
        inputs={"fixture": "synthetic skill invocation"},
        artifacts={"log_file": str(log_file)},
        human_summary="Started the reasoning-log self-test fixture.",
    )
    append_skill_progress(
        log_file,
        phase="evidence_recorded",
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        skill_call_id=call_id,
        run_id="reasoning-log-self-test",
        intent="Validate that skill-application logs are self-explaining.",
        inputs={"fixture": "synthetic skill invocation"},
        artifacts={"log_file": str(log_file)},
        evidence={"schema_sections_present": True},
        human_summary="Recorded synthetic schema evidence.",
    )
    append_skill_complete(
        log_file,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        skill_call_id=call_id,
        run_id="reasoning-log-self-test",
        intent="Validate that skill-application logs are self-explaining.",
        inputs={"fixture": "synthetic skill invocation"},
        artifacts={
            "log_file": str(log_file),
            "rendered_file": str(rendered_file),
            "html_file": str(html_file),
        },
        evidence={"event_count": 3, "schema_sections_present": True},
        decision={"status": "pass"},
        risks={},
        human_summary="Completed the reasoning-log self-test fixture.",
    )

    return dict(
        log_file=str(log_file),
        rendered_file=str(rendered_file),
        html_file=str(html_file),
        skill_call_id=call_id,
    )


def validate_fixture(fixture: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    log_file = Path(fixture["log_file"])
    validation = validate_reasoning_log(
        log_file,
        hooks_file=repo_root / "skills" / "SKILL_HOOKS.yaml",
        strict=True,
        require_instrumentation=True,
        require_skill_application=True,
    )
    return validation


def render_fixture(
    fixture: Dict[str, Any], validation: Dict[str, Any]
) -> Dict[str, Any]:
    log_file = Path(fixture["log_file"])
    rendered_file = Path(fixture["rendered_file"])
    html_file = Path(fixture["html_file"])
    events = load_events(log_file)
    summary = build_summary(events)
    rendered = render_markdown(summary, title="Reasoning Log Self-Test")
    rendered_file.write_text(rendered, encoding="utf-8")
    html_rendered = render_html_dashboard(
        log_file=log_file,
        events=events,
        validation=validation,
        title="Reasoning Log Self-Test",
    )
    html_file.write_text(html_rendered, encoding="utf-8")
    return {
        "markdown": rendered,
        "html": html_rendered,
        "summary": {
            "event_count": summary["event_count"],
            "skill_invocation_count": summary["skill_invocation_count"],
            "html_bytes": len(html_rendered.encode("utf-8")),
        },
    }


def audit_fixture_coverage(repo_root: Path) -> Dict[str, Any]:
    if repo_root == REPO_ROOT:
        return audit_coverage(REPO_ROOT / "skills")
    return audit_coverage(repo_root / "skills", repo_root=repo_root)


def finish_fixture(
    validation: Dict[str, Any],
    rendered_payload: Dict[str, Any],
    coverage: Dict[str, Any],
) -> Dict[str, Any]:
    rendered = rendered_payload["markdown"]
    html_rendered = rendered_payload["html"]
    summary = rendered_payload["summary"]
    checks = {
        "validation_ok": validation["ok"],
        "render_has_skill": "reasoning-log-schema-guardian" in rendered,
        "render_has_evidence": "schema_sections_present" in rendered,
        "html_render_has_skill": "reasoning-log-schema-guardian" in html_rendered,
        "html_render_has_filters": "searchBox" in html_rendered
        and "skillFilter" in html_rendered,
        "coverage_ok": coverage["ok"],
        "coverage_has_all_skills": coverage["skill_count"] > 100,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "validation_summary": validation["summary"],
        "render_summary": {
            "event_count": summary["event_count"],
            "skill_invocation_count": summary["skill_invocation_count"],
            "html_bytes": len(html_rendered.encode("utf-8")),
        },
        "coverage_summary": {
            "skill_count": coverage["skill_count"],
            "script_count": coverage["script_count"],
            "logging_class_counts": coverage["logging_class_counts"],
            "native_logged_script_count": coverage["native_logged_script_count"],
            "wrapper_logged_script_count": coverage["wrapper_logged_script_count"],
            "missing_skill_count": coverage["missing_skill_count"],
        },
    }


def run_self_test(repo_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """Run the same single-pass lifecycle using shared native step functions."""
    with TemporaryDirectory() as temp_dir:
        fixture = create_fixture(Path(temp_dir))
        validation = validate_fixture(fixture, repo_root)
        rendered = render_fixture(fixture, validation)
        coverage = audit_fixture_coverage(repo_root)
        return finish_fixture(validation, rendered, coverage)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the self-test and print a concise report."""
    args = parse_args(argv)
    report = run_self_test()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok: {report['ok']}")
        for key, value in report["checks"].items():
            print(f"{key}: {value}")
    return 0 if report["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())

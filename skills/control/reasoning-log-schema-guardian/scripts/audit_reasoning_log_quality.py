#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Audit reasoning logs for consumer-grade readability and safety."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reasoning_log import append_skill_complete, append_skill_start  # noqa: E402
from validate_reasoning_log import (  # noqa: E402
    finding,
    load_entries,
    parse_hook_contract,
    validate_entries,
)

QUALITY_DIMENSIONS = (
    "self_contained",
    "self_explanatory",
    "concise",
    "human_understandable",
    "machine_processable",
)
SECRET_PATTERNS = (
    re.compile(r"bearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}",
        re.IGNORECASE,
    ),
)
PRIVATE_PATH_PATTERN = re.compile(
    r"(/Users/[^\\s\"']+|/home/[^\\s\"']+|C:\\\\Users\\\\[^\\s\"']+)"
)
MAX_PAYLOAD_BYTES = 8192
MAX_SUMMARY_CHARS = 320
MAX_INTENT_CHARS = 180


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def default_hooks_file() -> Path:
    return REPO_ROOT / "skills" / "SKILL_HOOKS.yaml"


def default_good_fixture(directory: str = "") -> Path:
    return (
        Path(directory)
        if directory
        else REPO_ROOT / "artifacts" / "reasoning" / "self_test"
    ) / "good.jsonl"


def default_bad_fixture(directory: str = "") -> Path:
    return (
        Path(directory)
        if directory
        else REPO_ROOT / "artifacts" / "reasoning" / "self_test"
    ) / "bad.jsonl"


def as_object(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def event_application(event: Dict[str, Any]) -> Dict[str, Any]:
    payload = as_object(event.get("payload"))
    application = payload.get("skill_application")
    return application if isinstance(application, dict) else {}


def text_values(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: List[str] = []
        for key, item in value.items():
            result.extend(text_values(str(key)))
            result.extend(text_values(item))
        return result
    if isinstance(value, (list, tuple)):
        result: List[str] = []
        for item in value:
            result.extend(text_values(item))
        return result
    return []


def has_secret(value: Any) -> bool:
    for text in text_values(value):
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return True
    return False


def private_paths(value: Any) -> List[str]:
    paths: List[str] = []
    for text in text_values(value):
        paths.extend(match.group(1) for match in PRIVATE_PATH_PATTERN.finditer(text))
    return sorted(set(paths))


def is_repo_artifact_path(text: str) -> bool:
    return (
        text.startswith("artifacts/")
        or text.startswith(str(REPO_ROOT / "artifacts"))
        or "/artifacts/" in text
    )


def add_quality_finding(
    findings: List[Dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    *,
    dimension: str,
    log_file: Path,
    event_index: Optional[int] = None,
    line: Optional[int] = None,
) -> None:
    item = finding(severity, code, message, line=line, event_index=event_index)
    item["dimension"] = dimension
    item["log_file"] = repo_rel(log_file)
    findings.append(item)


def audit_event(
    *,
    event: Dict[str, Any],
    log_file: Path,
    findings: List[Dict[str, Any]],
    known_hooks: set[str],
) -> Dict[str, bool]:
    dimensions = {dimension: True for dimension in QUALITY_DIMENSIONS}
    event_index = (
        event.get("event_index") if isinstance(event.get("event_index"), int) else None
    )
    line = event.get("_line") if isinstance(event.get("_line"), int) else None
    payload = as_object(event.get("payload"))
    application = event_application(event)
    step = event.get("step")

    if not application:
        dimensions["self_contained"] = False
        dimensions["self_explanatory"] = False
        add_quality_finding(
            findings,
            "high",
            "missing_skill_application",
            "payload.skill_application is required for consumer-grade logs.",
            dimension="self_contained",
            log_file=log_file,
            event_index=event_index,
            line=line,
        )
    else:
        for field in ("skill", "skill_call_id", "status"):
            if not application.get(field):
                dimensions["self_contained"] = False
                add_quality_finding(
                    findings,
                    "high",
                    "missing_skill_application_field",
                    f"payload.skill_application.{field} is required.",
                    dimension="self_contained",
                    log_file=log_file,
                    event_index=event_index,
                    line=line,
                )
        for field in ("inputs", "artifacts", "evidence", "decision", "risks"):
            if not isinstance(application.get(field), dict):
                dimensions["machine_processable"] = False
                add_quality_finding(
                    findings,
                    "high",
                    "non_object_skill_application_section",
                    f"payload.skill_application.{field} must be an object.",
                    dimension="machine_processable",
                    log_file=log_file,
                    event_index=event_index,
                    line=line,
                )
        if not application.get("intent"):
            dimensions["self_explanatory"] = False
            add_quality_finding(
                findings,
                "high",
                "missing_intent",
                "Consumer-grade events need a short plain-language intent.",
                dimension="self_explanatory",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
        if not application.get("human_summary"):
            dimensions["human_understandable"] = False
            add_quality_finding(
                findings,
                "high",
                "missing_human_summary",
                "Consumer-grade events need a concise human summary.",
                dimension="human_understandable",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
        if (
            isinstance(application.get("intent"), str)
            and len(application["intent"]) > MAX_INTENT_CHARS
        ):
            dimensions["concise"] = False
            add_quality_finding(
                findings,
                "medium",
                "intent_too_long",
                f"Intent should normally stay under {MAX_INTENT_CHARS} characters.",
                dimension="concise",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
        if (
            isinstance(application.get("human_summary"), str)
            and len(application["human_summary"]) > MAX_SUMMARY_CHARS
        ):
            dimensions["concise"] = False
            add_quality_finding(
                findings,
                "medium",
                "human_summary_too_long",
                f"Human summary should normally stay under {MAX_SUMMARY_CHARS} characters.",
                dimension="concise",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
        if application.get("status") in {"blocked", "error"} and not application.get(
            "next_action"
        ):
            dimensions["human_understandable"] = False
            add_quality_finding(
                findings,
                "high",
                "missing_recoverable_next_action",
                "Blocked or error events must say what a consumer can do next.",
                dimension="human_understandable",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
        artifacts = as_object(application.get("artifacts"))
        if artifacts and not any(
            "hash" in str(key).lower() or "sha" in str(key).lower() for key in artifacts
        ):
            add_quality_finding(
                findings,
                "low",
                "artifact_hash_missing",
                "Artifact references are stronger when at least one stable hash is recorded.",
                dimension="self_contained",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )

    hook_id = payload.get("hook_id")
    if (
        hook_id
        and isinstance(hook_id, str)
        and known_hooks
        and hook_id not in known_hooks
    ):
        dimensions["machine_processable"] = False
        add_quality_finding(
            findings,
            "high",
            "unknown_hook_id",
            f"Hook id is not registered: {hook_id}",
            dimension="machine_processable",
            log_file=log_file,
            event_index=event_index,
            line=line,
        )

    raw_payload = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(raw_payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        dimensions["concise"] = False
        add_quality_finding(
            findings,
            "medium",
            "payload_too_large",
            f"Payload exceeds the recommended {MAX_PAYLOAD_BYTES} byte bound.",
            dimension="concise",
            log_file=log_file,
            event_index=event_index,
            line=line,
        )
    for raw_key in ("stdout", "stderr", "raw_output", "model_output"):
        if raw_key in raw_payload and len(raw_payload) > 1200:
            dimensions["concise"] = False
            add_quality_finding(
                findings,
                "medium",
                "raw_output_inline",
                f"Inline {raw_key} should be bounded or moved to an artifact.",
                dimension="concise",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
            break

    if (
        step
        and "wrapper" in raw_payload
        and application.get("skill")
        in {"mathformer-workflow-router", "final-derivation-review-orchestrator"}
    ):
        add_quality_finding(
            findings,
            "medium",
            "wrapper_only_high_value_workflow",
            "High-value routing and review workflows should emit native domain events.",
            dimension="self_explanatory",
            log_file=log_file,
            event_index=event_index,
            line=line,
        )

    if has_secret(payload):
        dimensions["machine_processable"] = False
        add_quality_finding(
            findings,
            "high",
            "secret_looking_value",
            "Payload contains a credential-looking value; redact it before publishing the log.",
            dimension="machine_processable",
            log_file=log_file,
            event_index=event_index,
            line=line,
        )
    for path_text in private_paths(payload):
        if not is_repo_artifact_path(path_text):
            add_quality_finding(
                findings,
                "medium",
                "private_path_inline",
                "Payload contains a local private path that is not clearly a repository artifact.",
                dimension="self_contained",
                log_file=log_file,
                event_index=event_index,
                line=line,
            )
            break

    return dimensions


def score_dimensions(event_scores: List[Dict[str, bool]]) -> Dict[str, float]:
    if not event_scores:
        return {dimension: 0.0 for dimension in QUALITY_DIMENSIONS}
    scores: Dict[str, float] = {}
    for dimension in QUALITY_DIMENSIONS:
        scores[dimension] = sum(1 for row in event_scores if row[dimension]) / len(
            event_scores
        )
    return scores


def audit_logs(
    log_files: Sequence[Path],
    *,
    hooks_file: Path,
) -> Dict[str, Any]:
    hook_contract = parse_hook_contract(hooks_file)
    known_hooks = set(hook_contract["known_hooks"])
    findings: List[Dict[str, Any]] = []
    per_log: List[Dict[str, Any]] = []
    all_scores: List[Dict[str, bool]] = []
    event_count = 0

    for log_file in log_files:
        entries, load_findings = load_entries(log_file)
        for item in load_findings:
            item["log_file"] = repo_rel(log_file)
            item.setdefault("dimension", "machine_processable")
            findings.append(item)
        schema_findings = validate_entries(
            entries,
            known_hooks=known_hooks,
            hook_steps=hook_contract["hook_steps"],
            required_payload_fields=hook_contract["required_payload_fields"],
            strict=True,
            require_instrumentation=False,
            require_skill_application=False,
        )
        for item in schema_findings:
            if item["severity"] == "high":
                item = dict(item)
                item["log_file"] = repo_rel(log_file)
                item.setdefault("dimension", "machine_processable")
                findings.append(item)

        log_scores: List[Dict[str, bool]] = []
        for entry in entries:
            event_count += 1
            row = audit_event(
                event=entry,
                log_file=log_file,
                findings=findings,
                known_hooks=known_hooks,
            )
            log_scores.append(row)
            all_scores.append(row)
        per_log.append(
            {
                "log_file": repo_rel(log_file),
                "event_count": len(entries),
                "quality_scores": score_dimensions(log_scores),
            }
        )

    severity_counts = Counter(item["severity"] for item in findings)
    quality_scores = score_dimensions(all_scores)
    blocking = [item for item in findings if item["severity"] == "high"]
    consumer_ready = (
        bool(log_files)
        and event_count > 0
        and not blocking
        and all(score >= 0.95 for score in quality_scores.values())
    )
    return {
        "schema_version": 1,
        "style": "reasoning_log_consumer_quality_audit",
        "ok": not blocking,
        "log_count": len(log_files),
        "event_count": event_count,
        "quality_scores": quality_scores,
        "quality_dimensions": list(QUALITY_DIMENSIONS),
        "consumer_readiness": {
            "ready": consumer_ready,
            "status": "ready" if consumer_ready else "blocked_or_advisory",
            "blocking_finding_count": len(blocking),
            "severity_counts": dict(severity_counts),
        },
        "logs": per_log,
        "findings": findings,
    }


def write_self_test_fixtures(directory: str = "") -> Dict[str, str]:
    good = default_good_fixture(directory)
    bad = default_bad_fixture(directory)
    good.parent.mkdir(parents=True, exist_ok=True)
    good_tmp = good.with_name(f"{good.name}.{os.getpid()}.tmp")
    bad_tmp = bad.with_name(f"{bad.name}.{os.getpid()}.tmp")
    for path in (good_tmp, bad_tmp):
        path.unlink(missing_ok=True)
    call_id = append_skill_start(
        good_tmp,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        run_id="reasoning-log-quality-fixture",
        intent="Create a consumer-grade reasoning-log fixture.",
        inputs={"fixture": "good", "source": "deterministic_self_test"},
        artifacts={"log_file": repo_rel(good), "log_file_sha256": "synthetic-fixture"},
        human_summary="Started a compact consumer-grade fixture.",
    )
    append_skill_complete(
        good_tmp,
        skill="reasoning-log-schema-guardian",
        hook_id="control.reasoning_log_schema",
        skill_call_id=call_id,
        run_id="reasoning-log-quality-fixture",
        intent="Create a consumer-grade reasoning-log fixture.",
        inputs={"fixture": "good"},
        artifacts={"log_file": repo_rel(good), "log_file_sha256": "synthetic-fixture"},
        evidence={"consumer_profile": "all_dimensions_present"},
        decision={"status": "pass"},
        risks={},
        next_action="Use this fixture for quality-auditor acceptance tests.",
        human_summary="Completed a consumer-grade reasoning-log fixture.",
    )
    bad_tmp.write_text(
        json.dumps(
            {
                "event_index": 1,
                "timestamp_utc": "2026-07-08T00:00:00+00:00",
                "timestamp_unix_ms": 1783468800000,
                "monotonic_ns": 1,
                "step": "skill_application_complete",
                "payload": {
                    "skill": "reasoning-log-schema-guardian",
                    "hook_id": "unknown.hook",
                    "stdout": "Bearer sk-thisisnotarealtokenbutlookslikeone",
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    good_tmp.replace(good)
    bad_tmp.replace(bad)
    return {"good": repo_rel(good), "bad": repo_rel(bad)}


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", action="append", type=Path, default=[])
    parser.add_argument("--hooks-file", type=Path, default=default_hooks_file())
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def parse_and_guard(
    argv: Optional[Sequence[str]], context: Dict[str, Any]
) -> Dict[str, Any]:
    args = parse_args(argv)
    request = {
        "log_files": [str(path) for path in args.log_file],
        "hooks_file": str(args.hooks_file),
        "self_test": args.self_test,
        "json": args.json,
        "fixture_directory": context["fixture_directory"],
    }
    return {"request": request, "use_fixtures": args.self_test or not args.log_file}


def prepare_fixtures(request: Dict[str, Any]) -> Dict[str, Any]:
    directory = request["fixture_directory"]
    fixtures = write_self_test_fixtures(directory)
    return {
        "selection": {
            "fixtures": fixtures,
            "log_files": [str(default_good_fixture(directory))],
        }
    }


def select_supplied(request: Dict[str, Any]) -> Dict[str, Any]:
    return {"selection": {"fixtures": {}, "log_files": list(request["log_files"])}}


def audit_selected(
    request: Dict[str, Any], selection: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "report": audit_logs(
            [Path(path) for path in selection["log_files"]],
            hooks_file=Path(request["hooks_file"]),
        )
    }


def verify_bad(
    request: Dict[str, Any], selection: Dict[str, Any], report: Dict[str, Any]
) -> Dict[str, Any]:
    fixtures = selection["fixtures"]
    poor_report = audit_logs(
        [default_bad_fixture(request["fixture_directory"])],
        hooks_file=Path(request["hooks_file"]),
    )
    report["self_test"] = {
        "fixtures": fixtures,
        "good_ok": report["ok"],
        "bad_has_high_findings": any(
            item["severity"] == "high" for item in poor_report["findings"]
        ),
        "bad_finding_codes": sorted({item["code"] for item in poor_report["findings"]}),
    }
    report["ok"] = report["ok"] and report["self_test"]["bad_has_high_findings"]
    return {"report": report}


def emit(request: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    # Formatting is shared with the CLI; the CLI owns printing to stdout.
    if request["json"]:
        stdout = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    else:
        lines = [
            f"ok: {report['ok']}",
            f"consumer readiness: {report['consumer_readiness']['status']}",
        ]
        lines.extend(
            f"- {item['severity']} {item['code']}: {item['message']}"
            for item in report["findings"][:20]
        )
        stdout = "\n".join(lines) + "\n"
    return {
        "result": {
            "report": report,
            "stdout": stdout,
            "exit_code": 0 if report["ok"] else 3,
        }
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parsed = parse_and_guard(argv, {"fixture_directory": ""})
    request = parsed["request"]
    selection = (
        prepare_fixtures(request)
        if parsed["use_fixtures"]
        else select_supplied(request)
    )["selection"]
    report = audit_selected(request, selection)["report"]
    if request["self_test"]:
        report = verify_bad(request, selection, report)["report"]
    result = emit(request, report)["result"]
    print(result["stdout"], end="")
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

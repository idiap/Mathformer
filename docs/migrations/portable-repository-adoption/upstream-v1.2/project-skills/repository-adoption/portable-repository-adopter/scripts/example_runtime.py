# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Standalone adoption fixture; not a BioAgents schema or production runtime."""
import argparse
import hashlib
import html
import json
from pathlib import Path
from uuid import uuid4


SKILL = {
    "id": "example:config-validator", "label": "Configuration validator",
    "capability": "Check configuration values against existing application rules.",
    "reasoning_types": [], "mapping_status": "unassigned", "version": "1.0.0",
    "binding": "config-validator.validate", "implementation": "validate",
}


def encoded(value):
    # This contract uses Python JSON encoding; no cross-language claim is made.
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def digest(record):
    return sha256(encoded({k: v for k, v in record.items() if k != "digest"}))


def validate(config):
    """The hypothetical legacy application implementation, retained unchanged."""
    timeout = config["timeout"]
    return [] if timeout > 0 else ["timeout must be positive"]


def invoke_validate(config, *, context):
    """context supplies IDs, an optional sink and an existing diagnostic hook."""
    def record(status, **details):
        event = dict(context["identity"], event_key="event-" + uuid4().hex, operation="validate",
                     execution_status=status, **details)
        try:
            context["emit"](event)
        except Exception:
            # Neither an optional sink nor its diagnostic hook owns the result.
            try:
                context["diagnostic"]("Optional skill trace could not be written")
            except Exception:
                pass

    try:
        findings = validate(config)
    except Exception as exc:
        record("failed", error_type=type(exc).__name__)
        raise
    record("completed", finding_count=len(findings))
    return findings


# An explicit registry resolves the metadata binding to the traced route.
# No dynamic import, code evaluation or second call to the algorithm is needed.
REGISTRY = {"config-validator.validate": invoke_validate}


def verify(record, root):
    """Check fixture integrity and joins, not authenticity or scientific validity."""
    if record["schema_version"] != "repository-adoption.example/v2":
        raise ValueError("Unsupported fixture schema")
    if record["digest"] != digest(record):
        raise ValueError("Record digest mismatch")
    if len(record["entries"]) != 1 or len(record["provenance"]) != 1:
        raise ValueError("Invocation join mismatch")
    entry, activity = record["entries"][0], record["provenance"][0]
    if (entry["invocation_id"] != activity["id"]
            or entry["invocation_id"] != record["invocation_id"]
            or entry["run_id"] != record["run_id"]
            or activity["run_id"] != record["run_id"]
            or activity["event_key"] != entry["event_key"]
            or entry["execution_status"] != record["execution_status"]
            or entry["skill_id"] != record["skill_metadata"]["id"]
            or activity["skill_id"] != entry["skill_id"]
            or activity["execution_status"] != entry["execution_status"]
            or entry["inputs"] != activity["used"]
            or entry["outputs"] != activity["generated"]):
        raise ValueError("Invocation join mismatch")
    snapshot = record["skill_metadata"]
    if snapshot["digest"] != digest(snapshot):
        raise ValueError("Metadata digest mismatch")
    artifacts = record["artifacts"]
    ids = [artifact["id"] for artifact in artifacts]
    if len(ids) != len(set(ids)) or set(ids) != set(entry["inputs"] + entry["outputs"]):
        raise ValueError("Artifact join mismatch")
    for artifact in artifacts:
        locator = Path(artifact["locator"])
        path = (root / locator).resolve()
        if locator.is_absolute() or root.resolve() not in path.parents:
            raise ValueError("Artifact escapes fixture directory")
        if sha256(path.read_bytes()) != artifact["byte_sha256"]:
            raise ValueError("Artifact digest mismatch")
    terminal = record["terminal_snapshot"]
    if (terminal["run_id"] != record["run_id"]
            or terminal["invocation_id"] != entry["invocation_id"]
            or terminal["event_key"] != entry["event_key"]
            or terminal["execution_status"] != entry["execution_status"]
            or entry["outputs"] != [terminal["result_artifact_id"]]):
        raise ValueError("Terminal snapshot join mismatch")
    result_artifact = next(a for a in artifacts if a["id"] == terminal["result_artifact_id"])
    if terminal["result_byte_sha256"] != result_artifact["byte_sha256"]:
        raise ValueError("Terminal result digest mismatch")
    result = json.loads((root / result_artifact["locator"]).read_bytes())
    if (result["run_id"] != record["run_id"]
            or result["invocation_id"] != record["invocation_id"]):
        raise ValueError("Result invocation join mismatch")


def render(record):
    """Render frozen metadata only; viewing never resolves or executes a skill."""
    snapshot, entry = record["skill_metadata"], record["entries"][0]
    preamble = [snapshot["label"], snapshot["capability"],
                "Reasoning type: " + (", ".join(snapshot["reasoning_types"]) or "Unassigned")]
    details = [entry["operation"] + " · " + entry["execution_status"],
               entry["outcome"], entry["rationale_summary"],
               "Invocation: " + entry["invocation_id"]]
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Adoption fixture trace</title></head><body>"
            + "<h1>" + html.escape(preamble[0]) + "</h1>"
            + "".join("<p>" + html.escape(text) + "</p>" for text in preamble[1:] + details)
            + "<h2>Provenance and artifacts</h2><pre>"
            + html.escape(json.dumps(record, ensure_ascii=False, indent=2))
            + "</pre></body></html>\n")


def build_example(output_dir):
    """Write a NEW directory containing one real, local fixture invocation."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    snapshot = json.loads(encoded(SKILL))
    snapshot["source_byte_sha256"] = sha256(Path(__file__).read_bytes())
    snapshot["digest"] = digest(snapshot)
    config = {"timeout": 0}
    (root / "input.json").write_bytes(encoded(config))
    events = []
    # Stand-ins for host-issued identities, not a host attestation.
    identity = {"run_id": "fixture-run-" + uuid4().hex,
                "invocation_id": "validate-" + uuid4().hex}
    context = {"identity": identity, "emit": events.append,
               "diagnostic": lambda message: None}
    result = REGISTRY[snapshot["binding"]](config, context=context)
    (root / "findings.json").write_bytes(encoded({**identity, "findings": result}))
    event, = events
    entry = dict(event, entry_id=event["event_key"], sequence=1, stage="configuration",
                 actor="example-host", skill_id=snapshot["id"],
                 action="Validated supplied configuration", outcome="One configuration finding returned.",
                 rationale_summary="Rationale not recorded.", inputs=["input-1"],
                 outputs=["output-1"], checks=[], alternatives_considered=[], operational_problems=[])
    activity = {"id": event["invocation_id"], "run_id": event["run_id"],
                "event_key": event["event_key"], "skill_id": snapshot["id"],
                "implementation": snapshot["implementation"], "used": entry["inputs"],
                "generated": entry["outputs"], "execution_status": event["execution_status"]}
    artifacts = [{"id": aid, "locator": name,
                  "byte_sha256": sha256((root / name).read_bytes())}
                 for aid, name in [("input-1", "input.json"), ("output-1", "findings.json")]]
    terminal = {**identity, "event_key": event["event_key"],
                "execution_status": event["execution_status"], "result_artifact_id": "output-1",
                "result_byte_sha256": sha256((root / "findings.json").read_bytes())}
    record = {"schema_version": "repository-adoption.example/v2", **identity,
              "identity_origin": "fixture-generated stand-ins; no host attestation",
              "subject": "Local configuration fixture", "execution_status": "completed",
              "summary": "Validation completed with one finding.",
              "visibility": "public synthetic fixture; no private input captured",
              "assumptions": [], "limitations": ["Single synchronous fixture invocation"],
              "skill_metadata": snapshot, "entries": [entry],
              "provenance": [activity], "artifacts": artifacts, "terminal_snapshot": terminal}
    record["digest"] = digest(record)
    verify(record, root)
    (root / "trace.json").write_bytes(encoded(record))
    (root / "trace.html").write_text(render(record), encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="New fixture directory; existing paths rejected")
    args = parser.parse_args()
    build_example(args.output_dir)
    print(str(Path(args.output_dir) / "trace.html"))

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Native Isabelle adapter packaged into Lunar's isolated worker runtime.

The adapter treats the Isabelle process receipt—not model-authored text—as the
authority for backend execution and verification.  It deliberately supports a
single, bounded operation: build one self-contained ``Mathformer`` theory in a
fresh session directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

INSTRUCTIONS = """Write a complete Isabelle2025-2 theory named Mathformer. Import
Complex_Main for real or complex arithmetic (Main alone does not define real),
or HOL-Analysis.Analysis when calculus is required. Begin the theory, prove the
exact requested statement as lemma mathformer_target, and end the theory. Keep
all assumptions explicit. Do not use sorry, oops, axiomatization, ML, oracle,
setup, skip_proofs, or external file reads. Return only the theory source and a
source_mapping that relates its assumptions and conclusion to the request."""

FORBIDDEN = re.compile(
    r"\b(sorry|oops|axiomatization|oracle|skip_proofs|ML|ML_file|setup|local_setup)\b"
)


def digest(path):
    """Return the SHA-256 digest of an executed artifact."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command_run(argv, directory, *, timeout=180, env=None, log_name="backend"):
    """Execute one bounded process group and retain complete log files."""
    directory = Path(directory)
    started = time.monotonic()
    stdout_path = directory / (log_name + ".stdout")
    stderr_path = directory / (log_name + ".stderr")
    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(
            argv,
            cwd=directory,
            env=env,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
        )
        timed_out = False
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            exit_code = process.wait()
    return {
        "command": argv,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": stdout_path.read_text(errors="replace")[-24000:],
        "stderr": stderr_path.read_text(errors="replace")[-12000:],
        "log_files": [stdout_path.name, stderr_path.name],
    }


def preflight(root):
    """Require the host-owned worker's Isabelle installation before model use."""
    binary = shutil.which("isabelle")
    if not binary:
        raise RuntimeError("Isabelle is not installed in the prepared package runtime")
    checked = command_run([binary, "version"], root, timeout=60, log_name="version")
    if checked["exit_code"] or checked["timed_out"]:
        raise RuntimeError("Isabelle version probe failed: " + checked["stderr"])
    return {
        "backend": "isabelle",
        "version": checked["stdout"].strip(),
        "executable": binary,
    }


def check_source(code):
    """Reject empty, oversized, placeholder-bearing, or misnamed theories."""
    if not code.strip() or len(code.encode()) > 200000:
        raise ValueError("Artifact is empty or exceeds 200 KB")
    if FORBIDDEN.search(code):
        raise ValueError(
            "Artifact contains a prohibited proof placeholder or escape hatch"
        )
    theory = re.search(r"(?m)^theory\s+([A-Za-z][A-Za-z0-9_]*)\b", code)
    if theory is None:
        raise ValueError("Isabelle artifact must declare a safe theory name")
    if not re.search(r"\b(?:lemma|theorem)\s+mathformer_target\b", code):
        raise ValueError("Missing required declaration mathformer_target")
    return theory.group(1)


def execute_artifact(code, root, *, timeout=180):
    """Build a submitted theory in a fresh Isabelle session and issue a receipt."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    runtime = preflight(root)
    theory = re.search(r"(?m)^theory\s+([A-Za-z][A-Za-z0-9_]*)\b", code)
    source = root / ((theory.group(1) if theory else "Rejected") + ".thy")
    source.write_text(code)
    receipt = {
        "backend": "isabelle",
        "runtime": runtime,
        "source_file": source.name,
        "source_sha256": digest(source),
        "backend_executed": False,
        "backend_verified": False,
        "status": "rejected",
        "verification_scope": (
            "submitted Isabelle theory and declared theorem; source fidelity "
            "and physical interpretation require separate review"
        ),
    }
    try:
        theory_name = check_source(code)
    except ValueError as exc:
        receipt["diagnostic"] = str(exc)
        (root / "receipt.json").write_text(json.dumps(receipt, indent=2))
        return receipt
    if theory_name != source.stem:
        raise ValueError("Retained Isabelle theory name changed during validation")

    parent = '"HOL-Analysis"' if "HOL-Analysis" in code else "HOL"
    (root / "ROOT").write_text(
        f"session Mathformer_Run = {parent} +\n"
        " options [document = false]\n"
        f" theories {theory_name}\n"
    )
    environment = dict(os.environ)
    environment["HOME"] = str(root / "home")
    Path(environment["HOME"]).mkdir(exist_ok=True)
    environment["ISABELLE_HOME_USER"] = str(root / "isabelle-user")
    environment["ISABELLE_JAVA_SYSTEM_OPTIONS"] = "-Xms64m -Xmx512m -Xss4m"
    command = [
        runtime["executable"],
        "build",
        "-j",
        "1",
        "-o",
        "threads=1",
        "-o",
        "parallel_proofs=0",
        "-D",
        str(root),
    ]
    observed = command_run(command, root, timeout=timeout, env=environment)
    passed = observed["exit_code"] == 0 and not observed["timed_out"]
    receipt.update(
        observed,
        backend_executed=True,
        backend_verified=bool(passed),
        status="passed" if passed else "failed",
    )
    (root / "receipt.json").write_text(json.dumps(receipt, indent=2))
    return receipt


class BackendHandler:
    """Bind Prism's declared Python.Call effect to the Isabelle adapter."""

    def __init__(self, root, event):
        self.root = Path(root)
        self.event = event
        self.receipt = None

    def handles(self, symbol, effects):
        return symbol == "mathformer.isabelle.execute" and effects == ("Python.Call",)

    def execute(self, request):
        from prism.language.core import Ok, RecordValue
        from prism.language.effects import EffectResult

        if "PythonCall" not in request.permissions:
            raise PermissionError("Native Isabelle execution requires PythonCall")
        self.event("stage", {"stage": "isabelle_execution", "status": "running"})
        candidate = request.arguments[0].fields
        self.receipt = execute_artifact(candidate["code"], self.root)
        self.receipt["source_mapping"] = candidate["source_mapping"]
        (self.root / "receipt.json").write_text(json.dumps(self.receipt, indent=2))
        self.event(
            "stage",
            {
                "stage": "isabelle_execution",
                "status": self.receipt["status"],
                "backend": "isabelle",
                "backend_executed": self.receipt["backend_executed"],
            },
        )
        result = RecordValue(
            "BackendReceipt",
            {
                "passed": self.receipt["backend_verified"],
                "diagnostics": json.dumps(self.receipt),
                "artifact": str(self.root / self.receipt["source_file"]),
            },
        )
        return EffectResult(
            Ok(result),
            request.result_type,
            provenance={
                "backend": "isabelle",
                "source_sha256": self.receipt["source_sha256"],
            },
            executor=self.receipt["runtime"]["executable"],
        )

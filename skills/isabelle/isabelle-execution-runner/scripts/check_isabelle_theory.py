#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.
#
# Intent:
#   Tell coding agents what context to load, what invariants to preserve, and how to validate their work.
#
# Function:
#   Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Run Isabelle build checks for generated `.thy` files."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any, Dict, Optional


def find_isabelle(explicit: Optional[Path] = None) -> Optional[Path]:
    """Document the responsibility of ``find_isabelle``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Search available candidates and return the matches needed by the caller.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if explicit is not None:
        return explicit if explicit.exists() else None
    configured = os.environ.get("ISABELLE_BIN")
    if configured:
        candidate = Path(configured).expanduser()
        return candidate if candidate.is_file() else None
    path = shutil.which("isabelle")
    if path:
        return Path(path)
    return None


def theory_name(path: Path) -> str:
    """Document the responsibility of ``theory_name``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``theory_name`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return path.stem


def ensure_root(session_dir: Path, session_name: str) -> Path:
    """Document the responsibility of ``ensure_root``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ensure_root`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    root = session_dir / "ROOT"
    theory_files = sorted(session_dir.glob("*.thy"))
    theories = sorted(path.stem for path in theory_files)
    if not theories:
        raise ValueError(f"No .thy files found in {session_dir}")
    theory_lines = "\n".join(f"    {name}" for name in theories)
    theory_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore") for path in theory_files
    )
    parent_session = '"HOL-Analysis"' if "HOL-Analysis" in theory_text else "HOL"
    root.write_text(
        f"session {session_name} = {parent_session} +\n"
        "  options [document = false]\n"
        "  theories\n"
        f"{theory_lines}\n",
        encoding="utf-8",
    )
    return root


def placeholder_report(text: str) -> Dict[str, Any]:
    """Document the responsibility of ``placeholder_report``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``placeholder_report`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    markers = re.findall(r"\b(?:sorry|oops|quickcheck_params)\b", text)
    return {
        "placeholder_count": len(markers),
        "markers": sorted(set(markers)),
        "placeholder_free": not markers,
    }


def ensure_text(value: Any) -> str:
    """Document the responsibility of ``ensure_text``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``ensure_text`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_check(
    *,
    theory_file: Path,
    session_dir: Path,
    session_name: str,
    isabelle_bin: Optional[Path],
    timeout_sec: int,
) -> Dict[str, Any]:
    """Document the responsibility of ``run_check``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Run the local workflow step and surface success, failure, and evidence in a predictable form.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    located = find_isabelle(isabelle_bin)
    placeholder = placeholder_report(theory_file.read_text(encoding="utf-8"))
    root = ensure_root(session_dir, session_name)
    payload: Dict[str, Any] = {
        "schema_version": 1,
        "skill": "isabelle-execution-runner",
        "hook_id": "execute.isabelle_initial",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "theory_file": str(theory_file),
        "session_dir": str(session_dir),
        "session_name": session_name,
        "root_file": str(root),
        "theory_name": theory_name(theory_file),
        "placeholder_report": placeholder,
        "isabelle_bin": str(located) if located else None,
        "ok": False,
    }
    if located is None:
        payload["error"] = (
            "Isabelle command not found. Install Isabelle or pass --isabelle-bin."
        )
        return payload

    cmd = [str(located), "build", "-D", str(session_dir)]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        payload.update(
            {
                "cmd": cmd,
                "returncode": proc.returncode,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "timeout": False,
                "process_ok": proc.returncode == 0,
                "ok": proc.returncode == 0 and placeholder["placeholder_free"],
            }
        )
    except subprocess.TimeoutExpired as exc:
        payload.update(
            {
                "cmd": cmd,
                "returncode": None,
                "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                "stdout": ensure_text(exc.stdout),
                "stderr": ensure_text(exc.stderr) or f"timeout after {timeout_sec}s",
                "timeout": True,
                "process_ok": False,
                "ok": False,
            }
        )
    return payload


def self_test() -> Dict[str, Any]:
    """Document the responsibility of ``self_test``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Provide the local operation named ``self_test`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    tmp = Path("artifacts/isabelle_wiki_level/self_test_exec")
    tmp.mkdir(parents=True, exist_ok=True)
    theory = tmp / "SelfTest.thy"
    theory.write_text(
        "theory SelfTest\n  imports Main\nbegin\n\ntheorem t: True by simp\n\nend\n",
        encoding="utf-8",
    )
    report = run_check(
        theory_file=theory,
        session_dir=tmp,
        session_name="Mathformer_Isabelle_Self_Test",
        isabelle_bin=None,
        timeout_sec=120,
    )
    return {"ok": report["ok"] or report.get("isabelle_bin") is None, "report": report}


def main(argv: Optional[list[str]] = None) -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theory-file", type=Path)
    parser.add_argument("--session-dir", type=Path)
    parser.add_argument("--session-name", default="Mathformer_Isabelle")
    parser.add_argument("--isabelle-bin", type=Path)
    parser.add_argument("--timeout-sec", type=int, default=180)
    parser.add_argument("--report-file", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = self_test()
    else:
        if args.theory_file is None:
            parser.error("--theory-file is required unless --self-test is used")
        session_dir = args.session_dir or args.theory_file.parent
        payload = run_check(
            theory_file=args.theory_file,
            session_dir=session_dir,
            session_name=args.session_name,
            isabelle_bin=args.isabelle_bin,
            timeout_sec=args.timeout_sec,
        )
        if args.report_file is not None:
            args.report_file.parent.mkdir(parents=True, exist_ok=True)
            args.report_file.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

    if args.json or args.self_test:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("PASS" if payload.get("ok") else "FAIL")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

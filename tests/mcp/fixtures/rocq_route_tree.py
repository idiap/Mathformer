# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Isolated source trees: real controlled templates, manifest and LaTeX inputs."""

import json
import shutil

LEAF = "tests/rocq/run_wiki_suite.py"
DRAFT = "skills/rocq/rocq-autoformalization-drafter/scripts/draft_rocq_wiki_case.py"
CHECK = "skills/rocq/rocq-execution-runner/scripts/check_rocq_file.py"
BACKEND = "backends/rocq/MathformerRocq/autoformalize.py"
MANIFEST = "tests/latex/wiki_level/manifest.json"


def populate(
    root,
    source,
    *,
    compiler="success",
    draft_failure=False,
    subset=False,
    ready=True,
    extra_bad=False,
):
    manifest = json.loads((source / MANIFEST).read_text())
    for relative in [
        LEAF,
        DRAFT,
        CHECK,
        BACKEND,
        "backends/rocq/MathformerRocq/__init__.py",
        MANIFEST,
        *[row["latex_file"] for row in manifest["cases"]],
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    # Exists solely for discovery metadata. Launch is intercepted, never executed.
    executable = root / "fixture-bin/rocq"
    executable.parent.mkdir()
    executable.write_text("compiler fixture; must never execute")
    (root / ".rocq-route-fixture.json").write_text(json.dumps({"compiler": compiler}))
    if draft_failure:
        # Source-owned metadata guard reports failure, then suite still checks files.
        first = root / manifest["cases"][0]["latex_file"]
        first.write_text("% mathformer-case-id: wrong_case\n")
    if subset:
        # Native drafting writes the first artifact, then reports an input error.
        (root / manifest["cases"][1]["latex_file"]).unlink()
    output = root / "artifacts/rocq_wiki_level"
    output.mkdir(parents=True)
    if extra_bad:
        (output / "Invalid.v").write_text(
            "Theorem invalid : True.\nProof.\nadmit.\nAdmitted.\n"
        )
    if not ready:
        (root / LEAF).unlink()
    return output


def stable(value):
    """Remove only timestamps and durations, including nested captured JSON."""
    if isinstance(value, dict):
        return {
            k: stable(v)
            for k, v in value.items()
            if k not in {"generated_at_utc", "duration_ms"}
        }
    if isinstance(value, list):
        return [stable(v) for v in value]
    if isinstance(value, str):
        try:
            return json.dumps(stable(json.loads(value)), sort_keys=True)
        except (ValueError, TypeError):
            return value
    return value

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Temporary native source trees and deterministic local grounding data."""

import json
import shutil

LEAF = "tests/isabelle/run_wiki_case.py"
GROUND = "skills/isabelle/isarmathlib-grounding-navigator/scripts/search_isarmathlib.py"
DRAFT = "skills/isabelle/isabelle-autoformalization-drafter/scripts/draft_isabelle_wiki_case.py"
CHECK = "skills/isabelle/isabelle-execution-runner/scripts/check_isabelle_theory.py"
LATEX = "tests/latex/wiki_level/injective_composition.tex"


def populate(
    root,
    source,
    *,
    compiler="success",
    ground_failure=False,
    draft_failure=False,
    ready=True,
):
    for relative in [LEAF, GROUND, DRAFT, CHECK, LATEX]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    (root / ".isabelle-route-fixture.json").write_text(
        json.dumps({"compiler": compiler})
    )
    # Actual navigator input, never a substituted navigator result.
    theory = root / "library/Fixture.thy"
    theory.parent.mkdir()
    theory.write_text(
        "theory Fixture imports Main begin\nlemma injective_composition: True by simp\nend\n"
    )
    output = root / "artifacts/isabelle/wiki_level"
    output.mkdir(parents=True)
    if ground_failure:
        (output / "wiki_injective_composition.grounding.json").mkdir()
    if draft_failure:
        (root / LATEX).write_text("invalid latex input without theorem or proof")
    if not ready:
        (root / LEAF).unlink()
    return output


def stable(value):
    """Retain every semantic/output field; omit only wall-clock measurements."""
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

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Synthetic inputs for unchanged native reasoning-log gates, with no providers.

Only native Python auditors run, in temporary trees containing no production
artifacts. Compiler failures are exercised separately by reasoning_route_compiler.
"""

from pathlib import Path
import shutil
from reasoning_log_schema_tree import populate as schema_tree, DIRECTORY


def populate(root, project, *, count=101):
    schema_tree(root, project, count=count)
    for source in (project / DIRECTORY).glob("*.py"):
        shutil.copyfile(source, root / DIRECTORY / source.name)
    reference = Path(
        "skills/control/reasoning-log-schema-guardian/references/schema.md"
    )
    (root / reference).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project / reference, root / reference)
    suite = Path("tests/reasoning_logs/run_consumer_contract_suite.py")
    (root / suite).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(project / suite, root / suite)

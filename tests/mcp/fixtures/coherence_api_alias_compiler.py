# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler boundary for generic hub failure tests only."""

import json
from pathlib import Path
import sys

mode = sys.argv[1]
if mode == "write":
    Path("undeclared.txt").write_text("compiler fixture output\n")
print(json.dumps({"ok": False, "mode": mode}))
print("compiler fixture diagnostic", file=sys.stderr)
raise SystemExit(7 if mode == "fail" else 0)

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler boundary for native leaf tests only."""

import json
from pathlib import Path
import sys
import time

mode = sys.argv[1]
if mode == "timeout":
    time.sleep(1)
if mode == "write":
    Path("undeclared.txt").write_text("compiler output\n")
print(json.dumps({"compiled": mode == "success", "mode": mode}))
print("compiler diagnostic: " + mode, file=sys.stderr)
sys.exit(7 if mode == "fail" else 0)

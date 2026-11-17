# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only installed-distribution provider for the real child process.

No production switch is installed. Tests alone put this directory on PYTHONPATH.
The registered argv, process launch, inventory main and filesystem stay real.
"""

import os
from pathlib import Path
import sys

if Path(sys.argv[0]).name == "generate_python_license_inventory.py":
    from importlib import metadata
    from licenses_metadata_provider import provider

    metadata.distributions = lambda: provider(
        Path(os.environ["LICENSES_METADATA_FIXTURE"])
    )

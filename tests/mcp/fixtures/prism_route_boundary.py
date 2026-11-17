# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only external PRISM/provider boundary; native verification stays intact."""

import json
import os
from pathlib import Path
from threading import Lock
from run_prism_verification_workflow_tests import CompilerProviderFixture


class Boundary(CompilerProviderFixture):
    def __init__(self):
        super().__init__()
        self.log_lock = Lock()

    def run(self, argv, **kwargs):
        assert set(kwargs) == {"cwd", "text", "capture_output", "check", "env"}
        assert kwargs["text"] and kwargs["capture_output"] and not kwargs["check"]
        # The native workers intentionally have no subprocess timeout.
        with self.log_lock:
            with Path(os.environ["PRISM_ROUTE_FIXTURE_LOG"]).open("a") as stream:
                stream.write(
                    json.dumps(
                        {
                            "workflow": Path(kwargs["cwd"]).parent.name,
                            "argv": argv,
                            "timeout": kwargs.get("timeout"),
                        }
                    )
                    + "\n"
                )
        return super().run(argv, **kwargs)

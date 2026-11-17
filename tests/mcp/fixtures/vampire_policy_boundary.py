# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Test-only deterministic external Vampire process boundary; no production switch."""

from pathlib import Path
import json
import subprocess
import tempfile


class Compiler:
    def __init__(
        self,
        root,
        statuses=("Theorem",),
        returncode=0,
        failure=None,
        empty_proof=False,
        unexpected_write=False,
    ):
        self.root = Path(root)
        self.statuses = statuses
        self.returncode = returncode
        self.failure = failure
        self.empty_proof = empty_proof
        self.unexpected_write = unexpected_write
        self.ledger = tempfile.TemporaryDirectory(prefix="policy-provider-fixture-")
        self.calls_path = Path(self.ledger.name) / "calls.json"
        self.versions_path = Path(self.ledger.name) / "versions.json"
        self.reset_calls()
        self.versions = 0

    @property
    def calls(self):
        return json.loads(self.calls_path.read_text())

    def reset_calls(self):
        self.calls_path.write_text("[]")

    @property
    def versions(self):
        return json.loads(self.versions_path.read_text())

    @versions.setter
    def versions(self, value):
        self.versions_path.write_text(json.dumps(value))

    def __call__(self, command, **kwargs):
        assert command[0] == "fixture-vampire", command
        assert "timeout" not in kwargs  # Preserve native subprocess arguments.
        if "--version" in command:
            self.versions += 1
            return subprocess.CompletedProcess(command, 0, "fixture Vampire 1", "")
        path = Path(command[-1])
        assert path.is_relative_to(self.root)
        assert command[command.index("--time_limit") + 1] == "10"
        assert command[command.index("--mode") + 1] == "portfolio"
        assert command[command.index("--proof") + 1] == "tptp"
        calls = self.calls
        calls.append({"command": command, "text": path.read_text()})
        self.calls_path.write_text(json.dumps(calls))
        assert "conjecture" in self.calls[-1]["text"]
        if self.unexpected_write:
            (self.root / "unexpected.txt").write_text("external compiler side effect")
        if self.failure:
            raise self.failure
        status = self.statuses[len(self.calls) - 1]
        output = "% SZS status " + status + "\n"
        if status != "GaveUp" and not self.empty_proof:
            output += "% SZS output start Proof\nfof(end,plain,$false,inference(resolution,[],[])).\n% SZS output end Proof\n"
        return subprocess.CompletedProcess(command, self.returncode, output, "")

# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external compiler boundary for native controller test inputs."""

import json
import subprocess


class Compiler:
    def __init__(self, root):
        self.root, self.calls = root, []

    def __call__(self, argv, **kwargs):
        assert argv[0] == "fixture-quality-compiler", argv
        assert kwargs == dict(
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=31,
        ), kwargs
        self.calls.append(list(argv))
        mode = argv[1]
        if mode == "crash":
            raise OSError("fixture compiler launch failed")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(
                argv, 31, output="partial", stderr="compiler timed out"
            )
        if mode == "write":
            (self.root / "undeclared.txt").write_text("compiler output")
        if mode == "artifact":
            (self.root / "artifacts").mkdir(exist_ok=True)
            (self.root / "artifacts/compiled.json").write_text('{"compiled":true}')
        return subprocess.CompletedProcess(
            argv,
            7 if mode == "fail" else 0,
            json.dumps({"ok": False, "diagnostic": mode}),
            "compiler stderr",
        )

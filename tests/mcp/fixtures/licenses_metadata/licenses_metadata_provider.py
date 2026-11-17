# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic package-metadata provider, including exhaustion and failure."""

from email.message import Message
import json
from types import SimpleNamespace


def provider(path):
    config = json.loads(path.read_text())
    log = path.with_suffix(".calls")

    def record(event):
        with log.open("a") as stream:
            stream.write(event + "\n")

    record("begin")
    for index, row in enumerate(config["packages"]):
        if config.get("fail_at") == index:
            record("failed")
            raise RuntimeError("metadata fixture failure")
        meta = Message()
        for key, value in row["fields"]:
            meta[key] = value
        record("yield")
        yield SimpleNamespace(name=row.get("fallback", ""), metadata=meta)
    if config.get("fail_at") == len(config["packages"]):
        record("failed")
        raise RuntimeError("metadata fixture failure")
    record("exhausted")

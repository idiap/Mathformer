# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external provider boundary; production stages remain untouched."""

import json
from pathlib import Path


class FixtureProvider:
    ledger = None

    def __init__(self, config=None):
        self.calls = []

    def generate(self, messages):
        stage = messages[0]["content"].split("stage ", 1)[1].split(".", 1)[0]
        args = json.loads(messages[1]["content"])
        if stage == "p:P":
            scope = args["scope"]
        elif stage == "r:R":
            scope = args["probe_evidence"]["scope"]
        else:
            scope = args["assessment"]["probe_evidence"]["scope"]
        case = scope["case"]
        call = {"stage": stage, "arguments": args, "messages": messages}
        self.calls.append(call)
        if self.ledger:
            with Path(self.ledger).open("a") as stream:
                stream.write(json.dumps(call) + "\n")
        if case == "error_" + stage[0]:
            raise RuntimeError("deterministic provider failure at " + stage)
        if case == "invalid_" + stage[0]:
            return "[]"
        if case == "malformed_" + stage[0]:
            return "{bad json"
        if stage == "p:P":
            return json.dumps(
                {
                    "findings": ["dimension algebra checked", "domain caveat"],
                    "target_seen": args["target"],
                }
            )
        if stage == "r:R":
            assert args["probe_evidence"]["result"]["target_seen"] == args["target"]
            return json.dumps(
                {
                    "assessment": "dimensioned evidence with limitations",
                    "findings_seen": args["probe_evidence"]["result"]["findings"],
                }
            )
        assert (
            args["assessment"]["result"]["findings_seen"]
            == args["assessment"]["probe_evidence"]["result"]["findings"]
        )
        return json.dumps(
            {"validation_status": "proved" if case == "unknown_decision" else case}
        )


def serve(ledger):
    import adversarial_validation_tools as native
    import mcp_server as server

    # Only the external provider is substituted. No config loader, credential
    # lookup, configured service launch, model SDK or scientific process runs.
    FixtureProvider.ledger = ledger
    native.ServiceLLM = FixtureProvider
    server._AGENTC_SERVICE_CONFIG = object()
    server.mcp.run(transport="stdio")

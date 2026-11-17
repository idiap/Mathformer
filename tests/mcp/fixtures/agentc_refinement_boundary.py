# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Deterministic external LLM and compiler boundaries, never a source-step stub."""

from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
import json
import re
from pathlib import Path
from types import SimpleNamespace


def install(module, directory, mode):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    calls = []
    events = []

    def log(kind, payload):
        calls.append({"kind": kind, "payload": payload})
        with (directory / "calls.jsonl").open("a") as stream:
            stream.write(json.dumps(calls[-1]) + "\n")

    class Provider:
        name = "deterministic-test-provider"

        def __init__(self, kind):
            self.kind = kind

        def generate(self, messages):
            log(self.kind, messages)
            if mode == self.kind + "_failure":
                raise TimeoutError("fixture provider failure: " + self.kind)
            if self.kind == "soft":
                text = messages[-1]["content"]
                if (
                    mode
                    in {
                        "semantic_false",
                        "semantic_unknown",
                        "mixed",
                        "semantic_failure",
                    }
                    and "-- semantic repaired" not in text
                ):
                    return "Explanation: meaning mismatch\n" + (
                        "unparseable"
                        if mode == "semantic_unknown"
                        else "Judgement: False"
                    )
                return "Explanation: aligned\nJudgement: True"
            if self.kind == "taxonomy":
                return "{}"
            match = re.search(
                r"-- (?:draft|formal|semantic) repaired (\d+)", messages[-1]["content"]
            )
            repair_index = (
                int(match.group(1)) + 1
                if self.kind in {"formal", "semantic"} and match
                else 0
            )
            broken = (
                mode in {"formal", "mixed", "cap", "last", "formal_failure"}
                and self.kind == "draft"
                or mode == "cap"
                or mode == "last"
                and repair_index < 4
            )
            return (
                "%%%%%%%%%%\n"
                + ("-- broken\n" if broken else "")
                + f"-- {self.kind} repaired {repair_index}\ntheorem fixture : True := by trivial\n%%%%%%%%%%"
            )

    def compiler(command, **kwargs):
        assert command[:3] == ["fixture-lake", "env", "lean"], command
        assert kwargs["env"] == {}
        assert kwargs["timeout"] == 13
        path = Path(command[-1])
        code = path.read_text()
        log(
            "compile",
            {"code": code, "file_prefix": path.stem, "timeout": kwargs["timeout"]},
        )
        if mode == "compiler_failure":
            raise OSError("fixture compiler launch failure")
        failed = "-- broken" in code
        return SimpleNamespace(
            returncode=int(failed),
            stdout=f"{path}:2:3: error: fixture syntax" if failed else "",
            stderr="",
        )

    # The module-local process and compiler environment seams cannot affect MCP.
    module.subprocess = SimpleNamespace(run=compiler)
    module._augment_env_with_lean_path = lambda: {}

    def trace(event, payload):
        value = json.loads(
            json.dumps(
                payload, default=lambda x: asdict(x) if is_dataclass(x) else str(x)
            )
        )
        events.append({"event": event, "payload": value})
        with (directory / "events.jsonl").open("a") as stream:
            stream.write(json.dumps(events[-1]) + "\n")

    @contextmanager
    def factory(request):
        def provider(kind):
            return Provider(kind)

        agent = module.IterativeSelfRefinementAgentC(
            autoformalizer=module.AutoformalizationAgent(
                llm=provider("draft"), formal_language="Lean4"
            ),
            hard_critique=module.HardCritiqueAgent(
                formal_language="Lean4",
                file_dir=str(directory),
                lean_workdir=str(directory),
                lake_bin="fixture-lake",
                lean_timeout_seconds=13,
            ),
            soft_critique=module.SoftCritiqueAgent(
                llm=provider("soft"),
                formal_language="Lean4",
                aspect_description=request["aspect_description"],
            ),
            formal_refiner=module.FormalRefinementAgent(
                llm=provider("formal"), formal_language="Lean4"
            ),
            informal_refiner=module.InformalRefinementAgent(
                llm=provider("semantic"), formal_language="Lean4"
            ),
            refinement_taxonomy_agent=module.RefinementTaxonomyAgent(
                llm=provider("taxonomy"), formal_language="Lean4"
            ),
            aspect_description=request["aspect_description"],
            max_iterations=4,
        )
        agent.workflow_trace_event = trace
        yield agent

    factory.provider = Provider
    return factory, calls, events


def configure(directory, mode):
    import mcp_server
    import agentc_workflow_tools as tools

    factory, _, _ = install(tools.agentc_module(), directory, mode)

    class ServiceProvider:
        name = "deterministic-test-provider"
        client = SimpleNamespace(close=lambda: None)

        def generate(self, messages):
            system = messages[0]["content"]
            if "classify the refinement transition" in system:
                kind = "taxonomy"
            elif "evaluate a specific aspect" in system:
                kind = "soft"
            elif "make it syntactically correct" in system:
                kind = "formal"
            elif "make it satisfy a specific aspect" in system:
                kind = "semantic"
            else:
                kind = "draft"
            return factory.provider(kind).generate(messages)

    # Only the external provider constructor, compiler process and compiler
    # environment are substituted. Production configuration, agent construction,
    # registered tools, dispatch and native observability all execute unchanged.
    tools.ServiceLLM = lambda config: ServiceProvider()
    settings = {
        ("lean", "workdir"): str(directory),
        ("lean", "lake_bin"): "fixture-lake",
        ("lean", "lean_timeout_seconds"): 13,
        ("paths", "artifacts_dir"): str(directory),
    }
    mcp_server._AGENTC_SERVICE_CONFIG = SimpleNamespace(
        get=lambda section, key: settings[(section, key)]
    )
    mcp_server._ALLOWED_WRITE_ROOTS = [Path(directory).resolve()]
    mcp_server.CALL_LOG_PATH = Path(directory) / "server-calls.jsonl"
    return mcp_server


def serve(directory, mode, contract_path):
    configure(directory, mode).mcp.run(transport="stdio")

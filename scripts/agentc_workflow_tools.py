# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
"""Typed MCP step boundaries over AgentC's native refinement iterator."""

import importlib.util
import json
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = Path("skills/autoformalization/autoformalization-agentc/workflow.yaml")


@lru_cache(maxsize=1)
def agentc_module():
    path = (
        REPO_ROOT
        / "skills/autoformalization/autoformalization-agentc/scripts/agentc.py"
    )
    spec = importlib.util.spec_from_file_location("mathformer_agentc_steps", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def iteration_guard(state):
    if state["correctness"] != "True":
        return "formal_repair"
    return (
        "early_stop"
        if agentc_module().judge_value(state["semantic_judgement"]) is True
        else "semantic_repair"
    )


class AgentCSteps:
    def __init__(self, document, agent_factory):
        self.document = document
        self.agent_factory = agent_factory

    def validate(self, ports, values):
        required = {name for name, port in ports.items() if port.get("required", True)}
        if (
            not isinstance(values, dict)
            or required - values.keys()
            or values.keys() - ports.keys()
        ):
            raise ValueError("Step ports do not match the workflow contract")
        for name, value in values.items():
            schema = self.document["types"][ports[name]["type"]]["schema"]
            if not Draft202012Validator(schema).is_valid(value):
                raise ValueError("Step port does not satisfy its schema: " + name)

    def call(self, operation, arguments):
        ports = self.document["operations"][operation]
        self.validate(ports["inputs"], arguments)
        if operation == "compute_iteration_guard":
            output = {"guard": {"route": iteration_guard(arguments["state"])}}
        else:
            arguments = json.loads(json.dumps(arguments))
            state = arguments.pop("state", None)
            arguments.pop("max_iterations", None)
            prefix = arguments.get("file_prefix", "sample")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", prefix):
                raise ValueError("file_prefix must be a simple artifact name")
            if state is not None:
                expected = {
                    "record_early_stop": "early_stop",
                    "formal_repair_round": "formal_repair",
                    "semantic_repair_round": "semantic_repair",
                }[operation]
                if iteration_guard(state) != expected:
                    raise ValueError("Step does not match the native refinement guard")
                if (
                    state["round_index"] >= 4
                    or not state["history"]
                    or state["history"][-1]["round_index"] != state["round_index"]
                ):
                    raise ValueError("Refinement state is exhausted or inconsistent")
            with self.agent_factory() as agent:
                iterator = agent.iter_refinement_steps(**arguments, _resume_state=state)
                try:
                    result = next(iterator)
                    stopped = (
                        result["history"][-1]["agent_name"] == "EarlyStop"
                        or result["round_index"] >= agent.max_iterations
                    )
                    if stopped:
                        next(iterator, None)  # Retain the native completion callback.
                finally:
                    iterator.close()
            output = {"state": result}
            if operation != "initialize_and_assess":
                output["stop"] = stopped
        self.validate(ports["outputs"], output)
        return output


class ServiceLLM:
    """AgentC provider interface using only explicit service configuration."""

    def __init__(self, config):
        from openai import OpenAI

        provider = config.get("providers", "default_llm_provider")
        self.model = config.get("providers", "default_llm_model")
        key = config.get("external_api_keys", "openai_api_key")
        if provider != "openai" or not self.model or not key:
            raise ValueError(
                "Configure providers.default_llm_provider=openai, providers.default_llm_model and external_api_keys.openai_api_key in the Mathformer service config"
            )
        self.name = self.model
        self.client = OpenAI(
            api_key=key,
            timeout=config.get("service", "default_timeout_seconds"),
            max_retries=0,
        )

    def generate(self, messages):
        response = self.client.responses.create(
            model=self.model, input=messages, store=False
        )
        if response.status != "completed" or not response.output_text:
            raise RuntimeError("AgentC model did not return a completed text response")
        return response.output_text


@contextmanager
def configured_agent(config, path_allowed, *, aspect_description=None):
    module = agentc_module()
    workdir = Path(config.get("lean", "workdir") or "")
    if not workdir.is_absolute():
        workdir = REPO_ROOT / workdir
    if not config.get("lean", "workdir") or not workdir.is_dir():
        raise ValueError("Configure lean.workdir with an existing Lake project")
    root = REPO_ROOT / config.get("paths", "artifacts_dir") / "agentc_steps"
    if not path_allowed(root):
        raise ValueError("AgentC artifacts are outside the configured write roots")
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="step-", dir=root))
    llm = ServiceLLM(config)
    aspect = (
        config.get("providers", "agentc_aspect_description")
        if aspect_description is None
        else aspect_description
    )
    try:
        critic = module.HardCritiqueAgent(
            formal_language="Lean4",
            file_dir=str(directory),
            lean_workdir=str(workdir),
            lean_timeout_seconds=config.get("lean", "lean_timeout_seconds"),
            lake_bin=config.get("lean", "lake_bin"),
        )
        agent = module.IterativeSelfRefinementAgentC(
            autoformalizer=module.AutoformalizationAgent(
                llm=llm, formal_language="Lean4"
            ),
            hard_critique=critic,
            soft_critique=module.SoftCritiqueAgent(
                llm=llm, formal_language="Lean4", aspect_description=aspect
            ),
            formal_refiner=module.FormalRefinementAgent(
                llm=llm, formal_language="Lean4"
            ),
            informal_refiner=module.InformalRefinementAgent(
                llm=llm, formal_language="Lean4"
            ),
            aspect_description=aspect,
            max_iterations=4,
        )

        def trace(event, payload):
            with (directory / "native-events.jsonl").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(
                    json.dumps(
                        {"event": event, "payload": payload},
                        default=lambda value: (
                            asdict(value) if is_dataclass(value) else str(value)
                        ),
                    )
                    + "\n"
                )

        agent.workflow_trace_event = trace
        yield agent
    finally:
        llm.client.close()


def register_agentc_tools(mcp, invoke):
    """Register the five workflow operations without exposing arbitrary Python."""

    @mcp.tool()
    def mathformer_agentc_initialize_and_assess(
        informal_statement: str,
        file_prefix: str,
        dependency_context: str | None,
        alignment_hints: str | None,
        core_statement_annotations: str | None,
        initial_formalization_raw: str | None,
        max_iterations: int,
        informal_formal_pairs: list[list[str]] | None = None,
        initial_formalization: str | None = None,
    ) -> dict:
        """Execute the native AgentC initialize and assess step."""
        values = {
            "informal_statement": informal_statement,
            "file_prefix": file_prefix,
            "dependency_context": dependency_context,
            "alignment_hints": alignment_hints,
            "core_statement_annotations": core_statement_annotations,
            "initial_formalization_raw": initial_formalization_raw,
            "max_iterations": max_iterations,
            "informal_formal_pairs": informal_formal_pairs,
            "initial_formalization": initial_formalization,
        }
        if informal_formal_pairs is None:
            values.pop("informal_formal_pairs")
        if initial_formalization is None:
            values.pop("initial_formalization")
        return invoke("initialize_and_assess", values)

    @mcp.tool()
    def mathformer_agentc_compute_iteration_guard(state: dict) -> dict:
        """Execute the native AgentC compute iteration guard step."""
        values = {"state": state}
        return invoke("compute_iteration_guard", values)

    @mcp.tool()
    def mathformer_agentc_record_early_stop(
        state: dict,
        informal_statement: str,
        dependency_context: str | None,
        alignment_hints: str | None,
        core_statement_annotations: str | None,
    ) -> dict:
        """Execute the native AgentC record early stop step."""
        values = {
            "state": state,
            "informal_statement": informal_statement,
            "dependency_context": dependency_context,
            "alignment_hints": alignment_hints,
            "core_statement_annotations": core_statement_annotations,
        }
        return invoke("record_early_stop", values)

    @mcp.tool()
    def mathformer_agentc_formal_repair_round(
        informal_statement: str,
        file_prefix: str,
        dependency_context: str | None,
        alignment_hints: str | None,
        core_statement_annotations: str | None,
        state: dict,
        max_iterations: int,
    ) -> dict:
        """Execute the native AgentC formal repair round step."""
        values = {
            "informal_statement": informal_statement,
            "file_prefix": file_prefix,
            "dependency_context": dependency_context,
            "alignment_hints": alignment_hints,
            "core_statement_annotations": core_statement_annotations,
            "state": state,
            "max_iterations": max_iterations,
        }
        return invoke("formal_repair_round", values)

    @mcp.tool()
    def mathformer_agentc_semantic_repair_round(
        informal_statement: str,
        file_prefix: str,
        dependency_context: str | None,
        alignment_hints: str | None,
        core_statement_annotations: str | None,
        state: dict,
        max_iterations: int,
    ) -> dict:
        """Execute the native AgentC semantic repair round step."""
        values = {
            "informal_statement": informal_statement,
            "file_prefix": file_prefix,
            "dependency_context": dependency_context,
            "alignment_hints": alignment_hints,
            "core_statement_annotations": core_statement_annotations,
            "state": state,
            "max_iterations": max_iterations,
        }
        return invoke("semantic_repair_round", values)

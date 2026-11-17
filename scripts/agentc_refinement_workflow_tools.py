# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Structured request adapters over the authoritative Agent C iterator.

No refinement algorithm lives here: each mutating step consumes one native
snapshot, and terminal steps exhaust that iterator to retain its completion event.
The older flat AgentC tools remain available with their existing contract.
"""

import json
import re
from pathlib import Path

from agentc_workflow_tools import AgentCSteps, configured_agent, iteration_guard

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/agentc-refinement.workflow.json"
)


class RefinementSteps(AgentCSteps):
    """A factory takes the request so aspect configuration is never lost."""

    def call(self, operation, arguments):
        ports = self.document["operations"][operation]
        self.validate(ports["inputs"], arguments)
        args = json.loads(json.dumps(arguments))
        if operation == "compute_guard":
            output = {
                "route": (
                    "exhausted"
                    if args["state"]["round_index"] >= 4
                    else iteration_guard(args["state"])
                )
            }
        else:
            request = args["request"]
            state = (
                args.get("resume_state")
                if operation == "prepare_state"
                else args["state"]
            )
            if not re.fullmatch(
                r"[A-Za-z0-9_-]{1,80}", request.get("file_prefix", "sample")
            ):
                raise ValueError("file_prefix must be a simple artifact name")
            if state is not None:
                if state["history"][-1]["round_index"] != state["round_index"]:
                    raise ValueError(
                        "Refinement history does not match the saved round"
                    )
            if operation == "prepare_state" and state is not None:
                # Native resume restores these fields without new work or a yield.
                output = {"state": state, "can_enter": state["round_index"] < 4}
            else:
                if operation == "return_current":
                    if state["round_index"] < 4:
                        raise ValueError(
                            "return_current requires an exhausted native range"
                        )
                elif operation != "prepare_state":
                    expected = {
                        "formal_repair_round": "formal_repair",
                        "semantic_repair_round": "semantic_repair",
                        "record_early_stop": "early_stop",
                    }[operation]
                    if state["round_index"] >= 4 or iteration_guard(state) != expected:
                        raise ValueError(
                            "Step does not match the native refinement guard or bound"
                        )
                native_args = {
                    k: v
                    for k, v in request.items()
                    if k not in {"max_iterations", "aspect_description"}
                }
                with self.agent_factory(request) as agent:
                    if (
                        agent.max_iterations != 4
                        or agent.aspect_description != request["aspect_description"]
                    ):
                        raise ValueError(
                            "Agent factory does not match the request aspect or bound"
                        )
                    iterator = agent.iter_refinement_steps(
                        **native_args,
                        _resume_state=state,
                        trace_event=getattr(agent, "workflow_trace_event", None),
                    )
                    try:
                        if operation == "return_current":
                            sentinel = object()
                            if next(iterator, sentinel) is not sentinel:
                                raise RuntimeError(
                                    "Exhausted source unexpectedly yielded a state"
                                )
                            output = {"state": state, "stop": True}
                        else:
                            result = next(iterator)
                            stop = (
                                result["history"][-1]["agent_name"] == "EarlyStop"
                                or result["round_index"] >= 4
                            )
                            if stop:
                                sentinel = object()
                                if next(iterator, sentinel) is not sentinel:
                                    raise RuntimeError(
                                        "Stopped source unexpectedly yielded another state"
                                    )
                            output = {"state": result}
                            output[
                                "can_enter" if operation == "prepare_state" else "stop"
                            ] = (
                                result["round_index"] < 4
                                if operation == "prepare_state"
                                else stop
                            )
                    finally:
                        iterator.close()
        self.validate(ports["outputs"], output)
        return output


def register_refinement_tools(
    mcp,
    write_policy,
    path_allowed=lambda path: True,
    *,
    agent_factory=None,
    document=None,
    config_getter=lambda: None,
):
    """Register concrete interfaces; production uses explicit service configuration."""

    def invoke(operation, values):
        if operation != "compute_guard":
            write_policy()
        contract = document or json.loads(AUTHORED.read_text())
        factory = agent_factory
        if factory is None:
            # Resolve only at invocation, never during discovery or import.
            config = config_getter()
            if operation != "compute_guard" and config is None:
                raise ValueError(
                    "AgentC execution requires a Mathformer service config"
                )

            def factory(request):
                return configured_agent(
                    config,
                    path_allowed,
                    aspect_description=request["aspect_description"],
                )

        return RefinementSteps(contract, factory).call(operation, values)

    @mcp.tool()
    def mathformer_agentc_workflow_prepare_state(
        request: dict, resume_state: dict | None = None
    ) -> dict:
        """Draft and critique, or restore a saved native iterator snapshot."""
        values = {"request": request}
        if resume_state is not None:
            values["resume_state"] = resume_state
        return invoke("prepare_state", values)

    @mcp.tool()
    def mathformer_agentc_workflow_compute_guard(state: dict) -> dict:
        """Select the native formal, semantic or early-stop branch."""
        return invoke("compute_guard", {"state": state})

    @mcp.tool()
    def mathformer_agentc_workflow_formal_repair_round(
        request: dict, state: dict
    ) -> dict:
        """Consume one native formal repair and its critiques and analysis."""
        return invoke("formal_repair_round", {"request": request, "state": state})

    @mcp.tool()
    def mathformer_agentc_workflow_semantic_repair_round(
        request: dict, state: dict
    ) -> dict:
        """Consume one native semantic repair and its critiques and analysis."""
        return invoke("semantic_repair_round", {"request": request, "state": state})

    @mcp.tool()
    def mathformer_agentc_workflow_record_early_stop(
        request: dict, state: dict
    ) -> dict:
        """Record the native unchanged-code EarlyStop and completion event."""
        return invoke("record_early_stop", {"request": request, "state": state})

    @mcp.tool()
    def mathformer_agentc_workflow_return_current(request: dict, state: dict) -> dict:
        """Complete an exhausted native resumed range without a new history entry."""
        return invoke("return_current", {"request": request, "state": state})

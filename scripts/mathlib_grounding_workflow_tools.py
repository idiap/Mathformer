# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP interfaces over the source-owned mathlib grounding loop steps."""

import inspect
import json
from pathlib import Path

from agentc_workflow_tools import AgentCSteps, agentc_module

AUTHORED = (
    Path(__file__).resolve().parents[1]
    / "skills/control/workflow-contract-validator/references/mathlib-grounding.workflow.json"
)


class GroundingSteps(AgentCSteps):
    def __init__(self, document, write_policy, path_allowed):
        self.document = document
        self.write_policy = write_policy
        self.path_allowed = path_allowed

    def call(self, operation, arguments):
        ports = self.document["operations"][operation]
        self.validate(ports["inputs"], arguments)
        args = json.loads(json.dumps(arguments))
        module = agentc_module()
        request = args.get("request", {})
        if request:
            bound = inspect.signature(
                module.run_mathlib_concept_compatibility_loop
            ).bind(**request)
            bound.apply_defaults()
            request = dict(bound.arguments)
            request.pop("trace_event")
        context = args.get("context", {})
        trace = None
        if operation in {"initialize", "attempt_round", "finish"}:
            self.write_policy()
            # The mapper writes its declaration index relative to cwd, and Lean
            # verification writes scratch files there. Both share this policy.
            if not self.path_allowed(Path(request["lean_workdir"]).resolve()):
                raise ValueError("Lean workdir is outside the configured write roots")
            for value in [request["reasoning_log_file"], context.get("trace_log_file")]:
                if value is not None and not self.path_allowed(Path(value).resolve()):
                    raise ValueError(
                        "Reasoning log is outside the configured write roots"
                    )
            if context.get("trace_log_file") is not None:

                def trace(event, payload):
                    module.append_reasoning_log_entry(
                        context["trace_log_file"],
                        statement=request["statement"],
                        file_prefix=context.get("file_prefix", "mathlib_grounding"),
                        dependency_label=context.get("dependency_label"),
                        step=event,
                        payload=payload,
                    )

        loop = module.MathlibConceptCompatibilityLoop(request, args.get("state"), trace)
        if operation == "initialize":
            output = {"state": loop.initialize()}
        elif operation == "attempt_round":
            if loop.state["round_index"] > loop.state["max_rounds"]:
                raise ValueError("Native round range is exhausted")
            status = loop.attempt_round()
            output = {"state": loop.state, "status": status}
        elif operation == "compute_guards":
            output = loop.compute_guards(args["status"])
        elif operation == "pack_transition":
            output = {"state": loop.pack_transition(args["widen"])}
        elif operation == "finish":
            output = dict(
                zip(("best_map", "coverage", "rounds", "last_error"), loop.finish())
            )
        else:
            raise ValueError("Unknown grounding operation: " + operation)
        self.validate(ports["outputs"], output)
        return output


def register_grounding_tools(mcp, write_policy, path_allowed):
    def invoke(operation, values):
        return GroundingSteps(
            json.loads(AUTHORED.read_text()), write_policy, path_allowed
        ).call(operation, values)

    @mcp.tool()
    def mathformer_mathlib_grounding_initialize(request: dict, context: dict) -> dict:
        """Initialize native budgets, coverage and start observability."""
        return invoke("initialize", dict(request=request, context=context))

    @mcp.tool()
    def mathformer_mathlib_grounding_attempt_round(
        request: dict, context: dict, state: dict
    ) -> dict:
        """Run the real local mapper, optional Lean checks and coverage review."""
        return invoke(
            "attempt_round", dict(request=request, context=context, state=state)
        )

    @mcp.tool()
    def mathformer_mathlib_grounding_compute_guards(state: dict, status: dict) -> dict:
        """Evaluate target, first-error and native range stopping conditions."""
        return invoke("compute_guards", dict(state=state, status=status))

    @mcp.tool()
    def mathformer_mathlib_grounding_pack_transition(
        request: dict, state: dict, widen: bool
    ) -> dict:
        """Carry native results and widen from the initial budgets when continuing."""
        return invoke(
            "pack_transition", dict(request=request, state=state, widen=widen)
        )

    @mcp.tool()
    def mathformer_mathlib_grounding_finish(
        request: dict, context: dict, state: dict
    ) -> dict:
        """Emit the source completion event and return retained results and errors."""
        return invoke("finish", dict(request=request, context=context, state=state))

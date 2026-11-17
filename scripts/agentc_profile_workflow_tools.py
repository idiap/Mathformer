# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Ordered MCP capabilities over the shared source-grounded AgentC iterator.

Native generators own all scientific state, side effects and exception scopes.
The JSON ports are validated projections; only an unmodified, current capability
can advance a context. Contexts expire after one hour and close on any failure.
"""

import atexit
import json
import time
import uuid
from pathlib import Path

from agentc_readiness_workflow_tools import ReadinessSteps, readiness_agent, value
from agentc_workflow_tools import agentc_module

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/agentc-profile.workflow.json"
)
OPERATIONS = (
    "normalize_and_pack_cycles",
    "dependencies_expand_annotate",
    "initialize_concepts",
    "concept_round_and_pack",
    "concepts_once_or_skip",
    "context_draft_and_hard_check",
    "initialize_refinement",
    "refinement_round_and_pack",
    "finalize_without_refinement",
    "save_check_audit_report",
    "advance_cycles_and_guards",
    "finish",
)
EVENTS = {
    "initialize": OPERATIONS[0],
    "check_report_save": "save_check_audit_report",
    "advance": "advance_cycles_and_guards",
    "finish": "finish",
}


def native_options(request):
    """Restore explicit recursive context using native report objects and sets."""
    module = agentc_module()
    options = dict(request["options"])
    context = request.get("native_context", {})

    def report(item):
        item = dict(item)
        if item.get("dependency_reports") is not None:
            item["dependency_reports"] = [
                report(child) for child in item["dependency_reports"]
            ]
        return module.SystematicAutoformalizationReport(**item)

    if "dependency_cache" in context:
        options["_dependency_cache"] = {
            key: report(item) for key, item in context["dependency_cache"].items()
        }
    if "dependency_stack" in context:
        options["_dependency_stack"] = set(context["dependency_stack"])
    if "shared_reasoning_log_file" in context:
        options["_shared_reasoning_log_file"] = context["shared_reasoning_log_file"]
    return options


class ProfileSteps(ReadinessSteps):
    def _next(self, session):
        while True:
            event, native = next(session["iterator"])
            if event.startswith("profile:"):
                event = event.removeprefix("profile:")
            elif event in EVENTS:
                event = EVENTS[event]
            else:
                continue
            session["native"].update(native)
            return event, session["native"]

    def call(self, operation, arguments):
        with self.lock:
            for key, session in list(self.sessions.items()):
                if time.monotonic() - session["touched"] > 3600:
                    self.close(key)
            handle = None
            try:
                supplied = arguments.get("state", arguments.get("work"))
                if isinstance(supplied, dict):
                    handle = supplied.get("context_id")
                self.validate(
                    self.document["operations"][operation]["inputs"], arguments
                )
                if operation == "normalize_and_pack_cycles":
                    if len(self.sessions) >= 32:
                        raise RuntimeError("Profile service context capacity reached")
                    request = json.loads(json.dumps(arguments["request"]))
                    self._paths(request)
                    shared = request.get("native_context", {}).get(
                        "shared_reasoning_log_file"
                    )
                    if shared is not None and not self.path_allowed(
                        Path(shared).resolve()
                    ):
                        raise ValueError("Shared log is outside service write roots")
                    manager = self.agent_factory(request)
                    agent = manager.__enter__()
                    handle = uuid.uuid4().hex
                    session = dict(
                        manager=manager,
                        iterator=agent.iter_systematic_workflow(
                            request["informal_statement"], **native_options(request)
                        ),
                        request=request,
                        revision=0,
                        native={},
                        touched=time.monotonic(),
                    )
                    self.sessions[handle] = session
                else:
                    session = self.sessions.get(handle)
                    if session is None:
                        raise ValueError("Profile context is missing or expired")
                    if supplied != session["state"]:
                        raise ValueError("Profile context is stale or modified")
                    if operation != session["next_operation"]:
                        raise ValueError(
                            "Operation does not match the native workflow guard"
                        )
                session["touched"] = time.monotonic()
                if operation == "retain_unrefined":
                    if supplied["eligible"]:
                        raise ValueError(
                            "Only ineligible refinement state may be forwarded"
                        )
                    self.validate(
                        self.document["operations"][operation]["outputs"],
                        {"state": supplied},
                    )
                    session["next_operation"] = "finalize_without_refinement"
                    return {"state": value(supplied)}
                event, native = self._next(session)
                if event != operation:
                    raise RuntimeError(
                        f"Expected native boundary {event}, received {operation}"
                    )
                session["revision"] += 1
                prior = session.get("state", {})
                state = {**prior, "context_id": handle, "revision": session["revision"]}
                state.update(
                    value(
                        {
                            key: native[key]
                            for key in (
                                "statement",
                                "statement_for_formalization",
                                "expanded_statement",
                                "dependency_reports",
                                "core_statement_items",
                                "core_statement_annotations",
                                "effective_pairs",
                                "concept_map",
                                "concept_map_error",
                                "mathlib_concept_coverage",
                                "alignment_hints",
                                "dependency_context",
                                "initial_code",
                                "latex_expansion_reviews",
                                "latex_expansion_review_passed",
                            )
                            if key in native
                        }
                    )
                )
                state["dependency_cache"] = value(native.get("dependency_cache", {}))
                state["dependency_stack"] = sorted(native.get("dependency_stack", []))
                output = {"state": state}
                next_op = None
                if operation in (
                    "normalize_and_pack_cycles",
                    "advance_cycles_and_guards",
                ):
                    multi = "cycles" in native
                    cap = native["cycles"] if multi else 1
                    index = native.get("cycle_idx", 1)
                    report = (
                        native.get("cycle_report") if multi else native.get("report")
                    )
                    done = (
                        not multi
                        or index >= cap
                        or bool(
                            report
                            and report.compatibility_target_met
                            and native["consistency_allows_stop"]
                        )
                    )
                    state.update(
                        value(
                            dict(
                                request=session["request"],
                                cycle_index=index,
                                cycle_limit=cap,
                                delegated=multi,
                                previous_final_code=native.get(
                                    "previous_final_code",
                                    report.final_code if report else None,
                                ),
                                summaries=native.get("cycle_summaries", []),
                                latest_report=report,
                            )
                        )
                    )
                    next_op = "dependencies_expand_annotate"
                    if operation == "advance_cycles_and_guards":
                        output["done"] = done
                        next_op = "finish" if done else next_op
                elif operation == "dependencies_expand_annotate":
                    output = {"work": state}
                    # A new cycle must not inherit the previous cycle's loop projections.
                    native.pop("concept_loop", None)
                    native.pop("refinement", None)
                    next_op = "initialize_concepts"
                elif operation in (
                    "initialize_concepts",
                    "concept_round_and_pack",
                    "concepts_once_or_skip",
                ):
                    loop = (
                        native.get("concept_loop")
                        if operation != "concepts_once_or_skip"
                        else None
                    )
                    projection = loop.state if loop else {}
                    state.update(
                        value(
                            dict(
                                iterate=native.get("iterate", False),
                                round_index=projection.get("round_index", 1),
                                best_map=projection.get(
                                    "best_map", native.get("concept_map")
                                ),
                                best_coverage=projection.get(
                                    "best_coverage",
                                    native.get("mathlib_concept_coverage") or {},
                                ),
                                rounds=projection.get(
                                    "rounds",
                                    native.get("mathlib_concept_compatibility_rounds")
                                    or [],
                                ),
                                last_error=projection.get(
                                    "last_error",
                                    native.get(
                                        "initialization_error",
                                        native.get("concept_map_error"),
                                    ),
                                ),
                                search_limits={
                                    key: item
                                    for key, item in projection.items()
                                    if key.startswith("current_")
                                },
                            )
                        )
                    )
                    next_op = "context_draft_and_hard_check"
                    if operation == "concepts_once_or_skip":
                        output["done"] = True
                    if operation == "initialize_concepts":
                        next_op = (
                            "concept_round_and_pack"
                            if state["iterate"]
                            else "concepts_once_or_skip"
                        )
                    elif operation == "concept_round_and_pack":
                        output["done"] = native["done"]
                        if not output["done"]:
                            next_op = operation
                elif operation == "context_draft_and_hard_check":
                    state.update(
                        eligible=native["eligible"],
                        round_index=0,
                        code=native["initial_code"],
                        correctness=native["initial_correctness"],
                        error_details=native["initial_details"],
                        semantic_judgement="",
                        history=[],
                    )
                    next_op = (
                        "initialize_refinement"
                        if state["eligible"]
                        else "retain_unrefined"
                    )
                elif operation in (
                    "initialize_refinement",
                    "refinement_round_and_pack",
                ):
                    state.update(value(native["refinement"]))
                    next_op = "refinement_round_and_pack"
                    if operation == "refinement_round_and_pack":
                        output["done"] = native["done"]
                        if output["done"]:
                            next_op = "save_check_audit_report"
                elif operation == "finalize_without_refinement":
                    output["done"] = True
                    state.update(
                        value(
                            dict(
                                code=native["final_code"],
                                correctness=native["final_correctness"],
                                error_details=native["final_details"],
                                history=native["history"],
                            )
                        )
                    )
                    next_op = "save_check_audit_report"
                elif operation == "save_check_audit_report":
                    state["latest_report"] = value(native["report"])
                    output = {"work": state}
                    next_op = "advance_cycles_and_guards"
                elif operation == "finish":
                    output = {
                        "report": value(native.get("final_report") or native["report"])
                    }
                    try:
                        next(session["iterator"])
                    except StopIteration:
                        pass
                    else:
                        raise RuntimeError(
                            "Completed native workflow yielded another boundary"
                        )
                self.validate(self.document["operations"][operation]["outputs"], output)
                session["state"] = value(state)
                session["next_operation"] = next_op
                if operation == "finish":
                    self.close(handle)
                return output
            except BaseException:
                if handle:
                    self.close(handle)
                raise


def register_profile_tools(
    mcp, write_policy, path_allowed=lambda path: True, *, config_getter=lambda: None
):
    """Discover real interfaces without loading models or reading credentials."""
    engine = None

    def invoke(operation, arguments):
        nonlocal engine
        write_policy()
        if engine is None:

            def factory(request):
                config = config_getter()
                if config is None:
                    raise ValueError(
                        "Profile execution requires an explicit Mathformer service config"
                    )
                context = request["agent_configuration"]
                return readiness_agent(
                    config, path_allowed, {**request, "agent_context": context}
                )

            engine = ProfileSteps(
                json.loads(AUTHORED.read_text()), factory, path_allowed
            )
            atexit.register(engine.close_all)
        return engine.call(operation, arguments)

    @mcp.tool()
    def mathformer_profile_normalize_and_pack_cycles(request: dict) -> dict:
        """Execute the native normalize and pack cycles boundary."""
        return invoke("normalize_and_pack_cycles", {"request": request})

    @mcp.tool()
    def mathformer_profile_dependencies_expand_annotate(state: dict) -> dict:
        """Execute the native dependencies expand annotate boundary."""
        return invoke("dependencies_expand_annotate", {"state": state})

    @mcp.tool()
    def mathformer_profile_initialize_concepts(work: dict) -> dict:
        """Execute the native initialize concepts boundary."""
        return invoke("initialize_concepts", {"work": work})

    @mcp.tool()
    def mathformer_profile_concept_round_and_pack(state: dict) -> dict:
        """Execute the native concept round and pack boundary."""
        return invoke("concept_round_and_pack", {"state": state})

    @mcp.tool()
    def mathformer_profile_concepts_once_or_skip(state: dict) -> dict:
        """Execute the native concepts once or skip boundary."""
        return invoke("concepts_once_or_skip", {"state": state})

    @mcp.tool()
    def mathformer_profile_context_draft_and_hard_check(state: dict) -> dict:
        """Execute the native context draft and hard check boundary."""
        return invoke("context_draft_and_hard_check", {"state": state})

    @mcp.tool()
    def mathformer_profile_initialize_refinement(state: dict) -> dict:
        """Execute the native initialize refinement boundary."""
        return invoke("initialize_refinement", {"state": state})

    @mcp.tool()
    def mathformer_profile_refinement_round_and_pack(state: dict) -> dict:
        """Execute the native refinement round and pack boundary."""
        return invoke("refinement_round_and_pack", {"state": state})

    @mcp.tool()
    def mathformer_profile_finalize_without_refinement(state: dict) -> dict:
        """Execute the native finalize without refinement boundary."""
        return invoke("finalize_without_refinement", {"state": state})

    @mcp.tool()
    def mathformer_profile_save_check_audit_report(state: dict) -> dict:
        """Execute the native save check audit report boundary."""
        return invoke("save_check_audit_report", {"state": state})

    @mcp.tool()
    def mathformer_profile_advance_cycles_and_guards(work: dict) -> dict:
        """Execute the native advance cycles and guards boundary."""
        return invoke("advance_cycles_and_guards", {"work": work})

    @mcp.tool()
    def mathformer_profile_finish(state: dict) -> dict:
        """Execute the native finish boundary."""
        return invoke("finish", {"state": state})

    @mcp.tool()
    def mathformer_profile_retain_unrefined(state: dict) -> dict:
        """Forward validated ineligible state without executing a native step."""
        return invoke("retain_unrefined", {"state": state})

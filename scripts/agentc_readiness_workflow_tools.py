# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""MCP ports over the shared native systematic-workflow iterator.

Contexts retain live recursive state and closures in this service process. They
are single-use, ordered capabilities, not durable checkpoints. Closing a context
closes the iterator, including the source's dependency-stack finally blocks.
"""

import atexit
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
import inspect
import json
import re
from pathlib import Path
import threading
import time
import uuid

from agentc_workflow_tools import AgentCSteps, agentc_module, configured_agent

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = (
    ROOT
    / "skills/control/workflow-contract-validator/references/agentc-readiness.workflow.json"
)


def value(item):
    if is_dataclass(item):
        return value(asdict(item))
    if isinstance(item, dict):
        return {str(k): value(v) for k, v in item.items()}
    if isinstance(item, (list, tuple, set)):
        return [value(v) for v in item]
    if isinstance(item, Path):
        return str(item)
    return item


@contextmanager
def readiness_agent(config, path_allowed, request):
    """Resolve providers only from the explicit Mathformer service config."""
    context = request["agent_context"]
    with configured_agent(
        config, path_allowed, aspect_description=context["aspect_description"]
    ) as agent:
        module = agentc_module()
        agent.max_iterations = context.get("max_iterations", 4)
        agent.default_target_compatibility_score = context.get(
            "default_target_compatibility_score", 100
        )
        llm = agent.autoformalizer.llm
        for key, cls in [
            ("latex_expander", module.LatexExpansionAgent),
            (
                "latex_expansion_completeness_reviewer",
                module.LatexExpansionCompletenessReviewAgent,
            ),
            (
                "latex_expansion_binding_reviewer",
                module.LatexExpansionBindingReviewAgent,
            ),
        ]:
            setattr(agent, key, cls(llm=llm) if context.get(key, False) else None)
        if not context.get("refinement", True):
            agent.soft_critique = agent.formal_refiner = agent.informal_refiner = None
        yield agent


class ReadinessSteps(AgentCSteps):
    def __init__(self, document, agent_factory, path_allowed=lambda path: True):
        super().__init__(document, agent_factory)
        self.sessions = {}
        self.lock = threading.RLock()
        self.path_allowed = path_allowed

    def close(self, handle):
        session = self.sessions.pop(handle, None)
        if session:
            try:
                session["iterator"].close()
            finally:
                session["manager"].__exit__(None, None, None)

    def close_all(self):
        for handle in list(self.sessions):
            self.close(handle)

    def _paths(self, request):
        module = agentc_module()
        options = request["options"]
        if not re.fullmatch(
            r"[A-Za-z0-9_-]{1,80}", options.get("file_prefix", "systematic")
        ):
            raise ValueError("file_prefix must be a simple artifact name")
        signature = inspect.signature(
            module.IterativeSelfRefinementAgentC.run_systematic_workflow
        )
        forbidden = {
            "self",
            "informal_statement",
            "_dependency_cache",
            "_dependency_stack",
            "_shared_reasoning_log_file",
        }
        if set(options) - (set(signature.parameters) - forbidden):
            raise ValueError("Unknown or private native options")
        if options.get("default_first_formalization_cycles") not in (None, 2):
            raise ValueError("This contract specializes default cycle caps 2/20")

        def check(path):
            if path is not None and not self.path_allowed(Path(path).resolve()):
                raise ValueError("Readiness path is outside service write roots")

        for key in (
            "output_file",
            "report_file",
            "history_file",
            "reasoning_log_file",
            "version_dir",
        ):
            check(options.get(key))

        def dependencies(statement, children):
            normalized = (
                module.normalize_informal_statement(statement)
                if options.get("normalize_input", True)
                else statement.strip()
            )
            defaults = module.default_artifact_paths(normalized)
            # Top-level overrides do not apply to recursive dependency outputs.
            for key, path in defaults.items():
                if children is None and options.get(key) is not None:
                    continue
                check(path)
            for child in children or []:
                dep = module.coerce_recursive_dependency_input(child)
                dependencies(dep.informal_statement, dep.dependencies)

        dependencies(request["informal_statement"], None)
        for dep in options.get("dependency_statements") or []:
            item = module.coerce_recursive_dependency_input(dep)
            dependencies(item.informal_statement, item.dependencies)

    def call(self, operation, arguments):
        with self.lock:
            for handle, session in list(self.sessions.items()):
                if time.monotonic() - session["touched"] > 3600:
                    self.close(handle)
            self.validate(self.document["operations"][operation]["inputs"], arguments)
            args = json.loads(json.dumps(arguments))
            handle = None
            try:
                if operation == "initialize":
                    if len(self.sessions) >= 32:
                        raise RuntimeError("Readiness service context capacity reached")
                    request = args["request"]
                    self._paths(request)
                    manager = self.agent_factory(request)
                    agent = manager.__enter__()
                    handle = uuid.uuid4().hex
                    iterator = agent.iter_systematic_workflow(
                        request["informal_statement"], **request["options"]
                    )
                    session = dict(
                        manager=manager,
                        iterator=iterator,
                        request=request,
                        revision=0,
                        state=None,
                        invocation=None,
                    )
                    self.sessions[handle] = session
                else:
                    supplied = args.get("invocation", args.get("state"))
                    handle = supplied["context_id"]
                    session = self.sessions.get(handle)
                    if session is None:
                        raise ValueError("Readiness context is missing or expired")
                    expected = (
                        session["invocation"]
                        if "invocation" in args
                        else session["state"]
                    )
                    if supplied != expected:
                        raise ValueError("Readiness context is stale or modified")
                    if "report" in args and args["report"] != session["report"]:
                        raise ValueError("Report differs from the native report")
                session["touched"] = time.monotonic()
                event, native = next(session["iterator"])
                while event.startswith("profile:"):
                    event, native = next(session["iterator"])
                if event != operation:
                    raise ValueError(
                        f"Expected native step {event}, received {operation}"
                    )
                session["revision"] += 1
                capability = dict(context_id=handle, revision=session["revision"])
                if operation in ("initialize", "advance"):
                    multi = "cycles" in native
                    cap = native["cycles"] if multi else 1
                    index = native.get("cycle_idx", 1)
                    stop = (
                        not multi
                        or index >= cap
                        or bool(
                            native.get("cycle_report")
                            and native["cycle_report"].compatibility_target_met
                            and native["consistency_allows_stop"]
                        )
                    )
                    session["state"] = state = value(
                        dict(
                            **capability,
                            request=session["request"],
                            cycle_index=(
                                index if stop else index + (operation == "advance")
                            ),
                            cycle_cap=cap,
                            multi_cycle=multi,
                            previous_final_code=native.get(
                                "previous_final_code",
                                (
                                    native.get("report").final_code
                                    if native.get("report")
                                    else None
                                ),
                            ),
                            dependency_cache=native.get("dependency_cache", {}),
                            dependency_stack=sorted(native.get("dependency_stack", [])),
                            reasoning_log=(
                                str(
                                    native.get("shared_reasoning_log")
                                    or native.get("reasoning_log_file")
                                )
                                if native.get("shared_reasoning_log")
                                or native.get("reasoning_log_file")
                                else None
                            ),
                            cycle_summaries=native.get("cycle_summaries", []),
                        )
                    )
                    output = {"state": state}
                    if operation == "advance":
                        output["stop"] = stop
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
                            "Finished native workflow yielded another step"
                        )
                else:
                    current_state = {
                        **session["state"],
                        "dependency_cache": value(native.get("dependency_cache", {})),
                        "dependency_stack": sorted(native.get("dependency_stack", [])),
                    }
                    invocation = value(
                        dict(
                            **capability,
                            state=current_state,
                            normalized_statement=native["statement"],
                            effective_statement=native["statement_for_formalization"],
                            expanded_statement=native["expanded_statement"],
                            dependency_reports=native["dependency_reports"],
                            review_passed=native["latex_expansion_review_passed"],
                            reviews=native["latex_expansion_reviews"],
                            **{
                                k: native[k]
                                for k in (
                                    "core_statement_items",
                                    "core_statement_annotations",
                                    "effective_pairs",
                                    "concept_map",
                                    "concept_map_error",
                                    "alignment_hints",
                                    "dependency_context",
                                    "initial_code",
                                )
                                if k in native
                            },
                        )
                    )
                    session["invocation"] = invocation
                    output = {"invocation": invocation}
                    if operation == "dependencies":
                        output["expand"] = bool(
                            native["enable_latex_expansion"]
                            and native["self"].latex_expander is not None
                        )
                    if operation == "check_report_save":
                        session["report"] = value(native["report"])
                        output["report"] = session["report"]
                self.validate(self.document["operations"][operation]["outputs"], output)
                if operation == "finish":
                    self.close(handle)
                return output
            except BaseException:
                if handle:
                    self.close(handle)
                raise


def register_readiness_tools(
    mcp, write_policy, path_allowed=lambda path: True, *, config_getter=lambda: None
):
    """Register ordered interfaces without importing providers during discovery."""
    engine = None

    def invoke(operation, arguments):
        nonlocal engine
        write_policy()
        if engine is None:

            def factory(request):
                config = config_getter()
                if config is None:
                    raise ValueError(
                        "Readiness requires an explicit Mathformer service config"
                    )
                return readiness_agent(config, path_allowed, request)

            engine = ReadinessSteps(
                json.loads(AUTHORED.read_text()), factory, path_allowed
            )
            atexit.register(engine.close_all)
        return engine.call(operation, arguments)

    @mcp.tool()
    def mathformer_readiness_initialize(request: dict) -> dict:
        """Validate and initialize the native systematic workflow context."""
        return invoke("initialize", {"request": request})

    @mcp.tool()
    def mathformer_readiness_dependencies(state: dict) -> dict:
        """Resolve native recursive dependencies and select expansion."""
        return invoke("dependencies", {"state": state})

    @mcp.tool()
    def mathformer_readiness_expand(invocation: dict) -> dict:
        """Run the configured native LaTeX expander once."""
        return invoke("expand", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_retain_statement(invocation: dict) -> dict:
        """Retain the native statement on disabled or unconfigured expansion."""
        return invoke("retain_statement", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_review(invocation: dict) -> dict:
        """Run the native sequential readiness reviewers without gating drafting."""
        return invoke("review", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_prepare(invocation: dict) -> dict:
        """Prepare native source annotations, examples, concepts and context."""
        return invoke("prepare", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_draft(invocation: dict) -> dict:
        """Use a seed or call the native autoformalizer."""
        return invoke("draft", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_check_report_save(invocation: dict) -> dict:
        """Check, refine, save and report through the native implementation."""
        return invoke("check_report_save", {"invocation": invocation})

    @mcp.tool()
    def mathformer_readiness_advance(invocation: dict, report: dict) -> dict:
        """Carry native code/cache/summaries and evaluate cycle stopping."""
        return invoke("advance", {"invocation": invocation, "report": report})

    @mcp.tool()
    def mathformer_readiness_finish(state: dict) -> dict:
        """Finalize native artifacts and release the live workflow context."""
        return invoke("finish", {"state": state})

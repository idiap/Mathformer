# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
"""Real AgentC step dispatch with deterministic provider/compiler seams."""

from tempfile import gettempdir

import importlib.util
import json
import os
import sys
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

ROOT = Path(os.getenv("MATHFORMER_TEST_ROOT", Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / "scripts"))
import agentc_workflow_tools as tools


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def document():
    return yaml.safe_load((ROOT / tools.DESCRIPTOR).read_text())


def make_agent(module, mode):
    calls = []
    hard_count = 0

    def auto(**kw):
        calls.append(("draft", kw))
        return "draft", "raw"

    def hard(**kw):
        nonlocal hard_count
        hard_count += 1
        calls.append(("compile", kw))
        return (
            ("False", "compile error")
            if mode == "cap" or mode == "formal" and hard_count == 1
            else ("True", "")
        )

    def soft(**kw):
        calls.append(("critique", kw))
        return (
            "unknown"
            if mode == "semantic" and kw["formalization"] == "draft"
            else "Judgement: True"
        ), "raw"

    def formal(**kw):
        calls.append(("formal", kw))
        return "formally repaired", "raw"

    def semantic(**kw):
        calls.append(("semantic", kw))
        return "semantically repaired", "raw"

    agent = module.IterativeSelfRefinementAgentC(
        autoformalizer=auto,
        hard_critique=hard,
        soft_critique=soft,
        formal_refiner=formal,
        informal_refiner=semantic,
        aspect_description="preserve meaning",
        max_iterations=4,
        enable_llm_refinement_taxonomy=False,
    )
    return agent, calls


def inputs(document, seed=None):
    values = {
        "informal_statement": "Test statement",
        "file_prefix": "case",
        "dependency_context": None,
        "alignment_hints": None,
        "core_statement_annotations": None,
        "initial_formalization_raw": None,
        "max_iterations": 4,
    }
    if seed is not None:
        values["initial_formalization"] = seed
    return values


def run_steps(document, agent, values):
    service = tools.AgentCSteps(document, lambda: nullcontext(agent))
    state = service.call("initialize_and_assess", values)["state"]
    for _ in range(4):
        route = service.call("compute_iteration_guard", {"state": state})["guard"][
            "route"
        ]
        operation = {
            "early_stop": "record_early_stop",
            "formal_repair": "formal_repair_round",
            "semantic_repair": "semantic_repair_round",
        }[route]
        arguments = {
            key: state if key == "state" else values[key]
            for key in document["operations"][operation]["inputs"]
        }
        result = service.call(operation, arguments)
        state = json.loads(json.dumps(result["state"]))  # actual transport boundary
        if result["stop"]:
            return state
    raise AssertionError("expected native early stop or cap stop")


@pytest.mark.parametrize(
    "mode,agents",
    [
        ("early", ["AutoformalizationAgent", "EarlyStop"]),
        ("formal", ["AutoformalizationAgent", "FormalRefinementAgent", "EarlyStop"]),
        (
            "semantic",
            ["AutoformalizationAgent", "InformalRefinementAgent", "EarlyStop"],
        ),
        ("cap", ["AutoformalizationAgent"] + ["FormalRefinementAgent"] * 4),
    ],
)
def test_source_steps_preserve_native_routes_order_history_and_cap(
    document, mode, agents
):
    module = tools.agentc_module()
    agent, calls = make_agent(module, mode)
    state = run_steps(document, agent, inputs(document))
    assert [item["agent_name"] for item in state["history"]] == agents
    assert [item["round_index"] for item in state["history"]] == list(
        range(len(agents))
    )
    assert (
        len([c for c in calls if c[0] == "compile"])
        == len([c for c in calls if c[0] == "critique"])
        == len(agents) - (agents[-1] == "EarlyStop")
    )
    assert [c[0] for c in calls][:3] == ["draft", "compile", "critique"]
    assert state["round_index"] == len(agents) - 1
    assert state["code"] == state["history"][-1]["code"]
    if mode == "cap":
        assert state["correctness"] == "False"  # cap return is not acceptance
    if mode == "formal":
        assert (
            next(c[1] for c in calls if c[0] == "formal")["error_details"]
            == "compile error"
        )
    if mode == "semantic":
        assert (
            next(c[1] for c in calls if c[0] == "semantic")["aspect_evaluation"]
            == "unknown"
        )


def test_empty_seed_is_reused_without_drafting(document):
    agent, calls = make_agent(tools.agentc_module(), "early")
    state = run_steps(document, agent, inputs(document, seed=""))
    assert not any(c[0] == "draft" for c in calls)
    assert state["code"] == ""
    assert state["history"][0]["agent_name"] == "InitialFormalizationSeed"


def test_invalid_input_is_rejected_before_provider_work(document):
    agent, calls = make_agent(tools.agentc_module(), "early")
    service = tools.AgentCSteps(document, lambda: nullcontext(agent))
    values = inputs(document)
    values["max_iterations"] = 5
    with pytest.raises(ValueError, match="schema"):
        service.call("initialize_and_assess", values)
    values = inputs(document)
    values["file_prefix"] = "../../outside"
    with pytest.raises(ValueError, match="artifact name"):
        service.call("initialize_and_assess", values)
    assert calls == []


def test_wrong_repair_route_is_rejected(document):
    agent, calls = make_agent(tools.agentc_module(), "early")
    service = tools.AgentCSteps(document, lambda: nullcontext(agent))
    values = inputs(document)
    state = service.call("initialize_and_assess", values)["state"]
    before = deepcopy(calls)
    arguments = {
        key: state if key == "state" else values[key]
        for key in document["operations"]["formal_repair_round"]["inputs"]
    }
    with pytest.raises(ValueError, match="guard"):
        service.call("formal_repair_round", arguments)
    assert calls == before


def test_provider_exception_propagates_without_fabricating_a_state(document):
    agent, _ = make_agent(tools.agentc_module(), "early")

    def fail(**kw):
        raise TimeoutError("test provider timeout")

    agent.autoformalizer = fail
    with pytest.raises(TimeoutError):
        tools.AgentCSteps(document, lambda: nullcontext(agent)).call(
            "initialize_and_assess", inputs(document)
        )


def test_provider_client_uses_explicit_config_and_rejects_incomplete_responses(
    monkeypatch,
):
    requests = []
    response = SimpleNamespace(status="completed", output_text="native response")
    client = SimpleNamespace(
        responses=SimpleNamespace(create=lambda **kw: requests.append(kw) or response)
    )
    options = []
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(OpenAI=lambda **kw: options.append(kw) or client),
    )
    data = {
        "providers": {
            "default_llm_provider": "openai",
            "default_llm_model": "configured-model",
        },
        "external_api_keys": {"openai_api_key": "test-only"},
        "service": {"default_timeout_seconds": 10},
    }
    config = SimpleNamespace(get=lambda section, key: data[section][key])
    llm = tools.ServiceLLM(config)
    messages = [{"role": "user", "content": "test"}]
    assert llm.generate(messages) == "native response"
    assert requests == [
        {"model": "configured-model", "input": messages, "store": False}
    ]
    assert options[0]["max_retries"] == 0
    response.status = "incomplete"
    with pytest.raises(RuntimeError, match="completed"):
        llm.generate(messages)


def test_early_stop_preserves_statement_and_context_for_taxonomy(document):
    agent, _ = make_agent(tools.agentc_module(), "early")
    transitions = []
    native = agent._analyze_refinement_transition

    def capture(**kwargs):
        transitions.append(kwargs)
        return native(**kwargs)

    agent._analyze_refinement_transition = capture
    values = inputs(document)
    values.update(
        dependency_context="dependencies",
        alignment_hints="alignment",
        core_statement_annotations="annotations",
    )
    run_steps(document, agent, values)
    assert transitions[-1]["agent_name"] == "EarlyStop"
    assert transitions[-1]["informal_statement"] == "Test statement"
    assert transitions[-1]["has_dependency_context"]
    assert transitions[-1]["has_alignment_hints"]
    assert transitions[-1]["has_core_statement_annotations"]


def test_compiler_timeout_and_selected_lake_binary_are_forwarded(tmp_path, monkeypatch):
    module = tools.agentc_module()
    invocations = []

    def compile_fixture(command, **kwargs):
        invocations.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", compile_fixture)
    critic = module.HardCritiqueAgent(
        formal_language="Lean4",
        file_dir=str(tmp_path),
        lean_workdir=str(tmp_path),
        lake_bin=str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"),
        lean_timeout_seconds=7,
    )
    assert (
        critic(formalization="example : True := by trivial", file_prefix="case")[0]
        == "True"
    )
    assert invocations[0][0][:3] == [
        str(Path(gettempdir()) / "mathformer-test-fixtures/fixture/lake"),
        "env",
        "lean",
    ]
    assert invocations[0][1]["timeout"] == 7

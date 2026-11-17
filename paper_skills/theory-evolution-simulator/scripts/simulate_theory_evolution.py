#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Capture the research-paper production workflow as auditable agent skills and helper scripts.
#
# Intent:
#   Separate scientific writing, evidence mapping, figure generation, and theory-evolution modeling roles.
#
# Function:
#   Provides structured guidance and automation for paper-oriented artifacts.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

"""Simulate backends/lean/Mathformer/RFDE theory-evolution trajectories."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import random
from pathlib import Path
from statistics import mean, median


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Document the responsibility of ``clamp``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``clamp`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    return max(low, min(high, value))


def relative_deltas(
    before: dict[str, float], after: dict[str, float], eps: float
) -> dict[str, dict[str, float]]:
    """Document the responsibility of ``relative_deltas``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``relative_deltas`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    result = {}
    for key, b in before.items():
        a = after[key]
        delta = a - b
        up = max(0.0, delta)
        down = max(0.0, -delta)
        result[key] = {
            "delta": delta,
            "up": up,
            "down": down,
            "relative_up": up / (eps + 1.0 - b),
            "relative_down": down / (eps + b),
        }
    return result


def terminal_status(state: dict[str, float], thresholds: dict) -> str:
    """Document the responsibility of ``terminal_status``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``terminal_status`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    complete = thresholds.get("complete", {})
    draft = thresholds.get("draft", {})
    if all(state.get(metric, 0.0) >= value for metric, value in complete.items()):
        return "complete"
    if all(state.get(metric, 0.0) >= value for metric, value in draft.items()):
        return "draft"
    return "blocked"


def update_state(
    state: dict[str, float], phase: dict, model: dict, rng: random.Random
) -> tuple[dict[str, float], dict[str, float]]:
    """Document the responsibility of ``update_state``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``update_state`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    target = phase["target"]
    rate = phase["gain_rate"]
    noise = model.get("noise", {})
    gain_sigma = noise.get("gain_sigma", 0.0)
    regression_scale = noise.get("regression_scale", 0.0)
    regression_probability = phase.get("regression_probability", 0.0)

    next_state = dict(state)
    raw_gain = {}
    for metric in model["metrics"]:
        current = state[metric]
        target_value = max(current, target.get(metric, current))
        gain_rate = max(0.0, rng.gauss(rate, rate * gain_sigma))
        gain = gain_rate * (target_value - current)
        regression = 0.0
        if rng.random() < regression_probability:
            regression = rng.random() * regression_scale * max(current, 0.05)
        next_state[metric] = clamp(current + gain - regression)
        raw_gain[metric] = gain

    # Couplings are weak positive nudges from already-improved dimensions.
    for coupling in model.get("couplings", []):
        source = coupling["source"]
        target_metric = coupling["target"]
        weight = coupling["weight"]
        boost = weight * raw_gain.get(source, 0.0) * (1.0 - next_state[target_metric])
        next_state[target_metric] = clamp(next_state[target_metric] + boost)

    return next_state, raw_gain


def simulate_one(model: dict, run_id: int, seed: int) -> dict:
    """Document the responsibility of ``simulate_one``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``simulate_one`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    trajectory = initialize_trajectory(model, run_id, seed)
    while trajectory["pending"]:
        phase = prepare_phase(trajectory)
        while phase["pending"]:
            phase = advance_step(phase)
        trajectory = finish_phase(phase)
    return finish_trajectory(trajectory)


def initialize_trajectory(model: dict, run_id: int, seed: int) -> dict:
    """Initialize one native trajectory with a transportable Random.getstate()."""
    rng = random.Random(seed + run_id * 1009)
    eps = float(model["delta_notation"].get("epsilon", 1e-6))
    state = dict(model["initial_state"])
    states = [
        {"step": 0, "phase": "initial", "metrics": dict(state), "cumulative_cost": 0.0}
    ]
    transitions = []
    cumulative_cost = 0.0
    step = 0
    return {
        "model": model,
        "run_id": run_id,
        "seed": seed,
        "rng": rng.getstate(),
        "epsilon": eps,
        "metrics": state,
        "states": states,
        "transitions": transitions,
        "cumulative_cost": cumulative_cost,
        "step": step,
        "phase_index": 0,
        "pending": bool(model["phases"]),
    }


def prepare_phase(trajectory: dict) -> dict:
    """Enter the next ordered native range without resetting trajectory state."""
    phase = trajectory["model"]["phases"][trajectory["phase_index"]]
    return {
        "trajectory": trajectory,
        "phase": phase,
        "phase_step": 0,
        "pending": 0 in range(phase["duration_steps"]),
    }


def advance_step(phase_state: dict) -> dict:
    """Apply one native step, preserving RNG cache, cost, and both histories."""
    trajectory = phase_state["trajectory"]
    model, phase = trajectory["model"], phase_state["phase"]
    phase_step = phase_state["phase_step"]
    state, eps = trajectory["metrics"], trajectory["epsilon"]
    states, transitions = trajectory["states"], trajectory["transitions"]
    cumulative_cost, step = trajectory["cumulative_cost"], trajectory["step"]
    rng = random.Random(0)
    version, internal, cache = trajectory["rng"]
    rng.setstate((version, tuple(internal), cache))
    before = dict(state)
    state, _ = update_state(state, phase, model, rng)
    cost_sigma = model.get("noise", {}).get("cost_sigma", 0.0)
    cost = max(
        0.0,
        rng.gauss(phase["cost_per_step"], phase["cost_per_step"] * cost_sigma),
    )
    cumulative_cost += cost
    step += 1
    deltas = relative_deltas(before, state, eps)
    protected = model["protected_metrics"]
    all_up = sum(d["relative_up"] for d in deltas.values()) / len(deltas)
    all_down = sum(d["relative_down"] for d in deltas.values()) / len(deltas)
    protected_up = sum(deltas[m]["relative_up"] for m in protected) / len(protected)
    protected_down = sum(deltas[m]["relative_down"] for m in protected) / len(protected)
    transitions.append(
        {
            "step": step,
            "phase": phase["id"],
            "phase_step": phase_step + 1,
            "cost": cost,
            "delta": deltas,
            "eta_all": (all_up - 2.0 * all_down) / (1.0 + cost),
            "eta_protected": (protected_up - 2.0 * protected_down) / (1.0 + cost),
        }
    )
    states.append(
        {
            "step": step,
            "phase": phase["id"],
            "metrics": dict(state),
            "cumulative_cost": cumulative_cost,
        }
    )
    trajectory.update(
        metrics=state, rng=rng.getstate(), cumulative_cost=cumulative_cost, step=step
    )
    phase_step += 1
    return {
        "trajectory": trajectory,
        "phase": phase,
        "phase_step": phase_step,
        "pending": phase_step < phase["duration_steps"],
    }


def finish_phase(phase_state: dict) -> dict:
    """Advance the phase cursor after its range is exhausted."""
    trajectory = phase_state["trajectory"]
    trajectory["phase_index"] += 1
    trajectory["pending"] = trajectory["phase_index"] < len(
        trajectory["model"]["phases"]
    )
    return trajectory


def finish_trajectory(trajectory: dict) -> dict:
    """Classify the final metrics after all phases, independently of exit status."""
    model, state = trajectory["model"], trajectory["metrics"]
    run_id, seed = trajectory["run_id"], trajectory["seed"]
    cumulative_cost = trajectory["cumulative_cost"]
    states, transitions = trajectory["states"], trajectory["transitions"]
    acceptance_thresholds = model.get(
        "acceptance_thresholds", model.get("gate_thresholds")
    )
    if acceptance_thresholds is None:
        raise KeyError("model must define acceptance_thresholds")
    status = terminal_status(state, acceptance_thresholds)
    return {
        "run_id": f"sim_{run_id:04d}",
        "seed": seed + run_id * 1009,
        "status": status,
        "final_metrics": dict(state),
        "total_cost": cumulative_cost,
        "states": states,
        "transitions": transitions,
    }


def quantile(values: list[float], q: float) -> float:
    """Document the responsibility of ``quantile``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``quantile`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    frac = idx - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def summarize(model: dict, runs: list[dict]) -> dict:
    """Document the responsibility of ``summarize``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Provide the local operation named ``summarize`` while preserving the surrounding module contract.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    metrics = model["metrics"]
    terminal = {
        metric: [run["final_metrics"][metric] for run in runs] for metric in metrics
    }
    statuses = {
        status: sum(1 for run in runs if run["status"] == status)
        for status in ["complete", "draft", "blocked"]
    }
    phase_rows = []
    for phase in model["phases"]:
        phase_id = phase["id"]
        phase_transitions = [
            transition
            for run in runs
            for transition in run["transitions"]
            if transition["phase"] == phase_id
        ]
        if not phase_transitions:
            continue
        rel_up_by_metric = {
            metric: mean(t["delta"][metric]["relative_up"] for t in phase_transitions)
            for metric in metrics
        }
        rel_down_by_metric = {
            metric: mean(t["delta"][metric]["relative_down"] for t in phase_transitions)
            for metric in metrics
        }
        phase_rows.append(
            {
                "phase": phase_id,
                "mean_cost": mean(t["cost"] for t in phase_transitions),
                "mean_eta_all": mean(t["eta_all"] for t in phase_transitions),
                "mean_eta_protected": mean(
                    t["eta_protected"] for t in phase_transitions
                ),
                "relative_up": rel_up_by_metric,
                "relative_down": rel_down_by_metric,
                "dominant_gain_metric": max(rel_up_by_metric, key=rel_up_by_metric.get),
                "dominant_regression_metric": max(
                    rel_down_by_metric, key=rel_down_by_metric.get
                ),
            }
        )
    return {
        "run_count": len(runs),
        "status_counts": statuses,
        "status_probabilities": {
            key: value / len(runs) for key, value in statuses.items()
        },
        "terminal_metrics": {
            metric: {
                "mean": mean(values),
                "median": median(values),
                "p10": quantile(values, 0.10),
                "p90": quantile(values, 0.90),
            }
            for metric, values in terminal.items()
        },
        "cost": {
            "mean": mean(run["total_cost"] for run in runs),
            "median": median(run["total_cost"] for run in runs),
            "p10": quantile([run["total_cost"] for run in runs], 0.10),
            "p90": quantile([run["total_cost"] for run in runs], 0.90),
        },
        "phase_parameter_estimates": phase_rows,
    }


def build_step_summary(model: dict, runs: list[dict]) -> list[dict]:
    """Document the responsibility of ``build_step_summary``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Build the local data structure or artifact used by the next workflow stage.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    max_step = max(len(run["states"]) for run in runs) - 1
    rows = []
    for step in range(max_step + 1):
        states = [run["states"][step] for run in runs if step < len(run["states"])]
        row = {"step": step, "phase": states[0]["phase"]}
        for metric in model["metrics"]:
            values = [state["metrics"][metric] for state in states]
            row[f"{metric}_median"] = median(values)
            row[f"{metric}_p10"] = quantile(values, 0.10)
            row[f"{metric}_p90"] = quantile(values, 0.90)
        rows.append(row)
    return rows


def render_svg(model: dict, rows: list[dict], output: Path) -> None:
    """Document the responsibility of ``render_svg``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Render structured information into a human-readable or machine-consumable representation.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    width, height = 1180, 620
    margin_left, margin_right = 80, 130
    margin_top, margin_bottom = 58, 70
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom
    metrics_to_plot = [
        ("lean_executability", "Lean exec.", "#2563EB"),
        ("anchor_coverage", "Anchors", "#0E7490"),
        ("mathlib_grounding", "Mathlib", "#047857"),
        ("reverse_informal_consistency", "Reverse cons.", "#7C3AED"),
        ("proof_coherence", "Proof", "#B45309"),
        ("workflow_evidence", "Workflow", "#64748B"),
    ]
    max_step = rows[-1]["step"] if rows else 1

    def x(step: float) -> float:
        """Document the responsibility of ``render_svg.x``.

        Motivation:
            Capture the research-paper production workflow as auditable agent skills and helper scripts.

        Intent:
            Render structured information into a human-readable or machine-consumable representation.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return margin_left + (step / max(1, max_step)) * plot_w

    def y(value: float) -> float:
        """Document the responsibility of ``render_svg.y``.

        Motivation:
            Capture the research-paper production workflow as auditable agent skills and helper scripts.

        Intent:
            Render structured information into a human-readable or machine-consumable representation.

        Inputs:
            Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

        Outputs:
            Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
        """
        return margin_top + (1.0 - value) * plot_h

    scenario = model.get("scenario", {})
    title = "Simulated Mathformer theory-evolution trajectories"
    if scenario.get("label"):
        title = f"{title}: {scenario['label']}"
    subtitle = scenario.get("description", "Ensemble median RFDE metric trajectories.")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="40" y="31" font-family="Arial, sans-serif" font-size="20" font-weight="800" fill="#0f172a">{html.escape(title)}</text>',
        f'<text x="40" y="50" font-family="Arial, sans-serif" font-size="12" fill="#475569">{html.escape(subtitle)}</text>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height-margin_bottom}" stroke="#CBD5E1"/>',
        f'<line x1="{margin_left}" y1="{height-margin_bottom}" x2="{width-margin_right}" y2="{height-margin_bottom}" stroke="#CBD5E1"/>',
    ]
    for val in [0.0, 0.25, 0.5, 0.75, 1.0]:
        yy = y(val)
        parts.append(
            f'<line x1="{margin_left}" y1="{yy}" x2="{width-margin_right}" y2="{yy}" stroke="#E2E8F0"/>'
        )
        parts.append(
            f'<text x="{margin_left-12}" y="{yy+4}" text-anchor="end" font-family="Arial" font-size="11" fill="#64748B">{val:.2f}</text>'
        )

    # Phase bands
    phase_start = 0
    current_phase = rows[0]["phase"]
    phase_colors = ["#F8FAFC", "#EFF6FF"]
    band_index = 0
    for i, row in enumerate(rows + [{"step": max_step + 1, "phase": None}]):
        if row["phase"] != current_phase:
            x0 = x(phase_start)
            x1 = x(i - 1)
            parts.append(
                f'<rect x="{x0}" y="{margin_top}" width="{max(1, x1-x0)}" height="{plot_h}" fill="{phase_colors[band_index%2]}" opacity="0.65"/>'
            )
            parts.append(
                f'<text x="{(x0+x1)/2}" y="{height-margin_bottom+30}" text-anchor="middle" font-family="Arial" font-size="10" fill="#475569">{html.escape(current_phase)}</text>'
            )
            phase_start = i
            current_phase = row["phase"]
            band_index += 1

    label_y_positions: list[float] = []
    for metric, label, color in metrics_to_plot:
        pts = " ".join(
            f"{x(row['step']):.1f},{y(row[f'{metric}_median']):.1f}" for row in rows
        )
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.6"/>'
        )
        label_x = width - margin_right - 4
        label_y = y(rows[-1][f"{metric}_median"])
        for prior in label_y_positions:
            if abs(label_y - prior) < 15:
                label_y = prior + 15
        label_y_positions.append(label_y)
        parts.append(
            f'<text x="{label_x}" y="{label_y+4:.1f}" font-family="Arial" font-size="11" font-weight="700" fill="{color}">{html.escape(label)}</text>'
        )

    parts.append(
        f'<text x="{width/2}" y="{height-18}" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">step / phase trajectory</text>'
    )
    parts.append(
        f'<text x="22" y="{height/2}" transform="rotate(-90 22,{height/2})" text-anchor="middle" font-family="Arial" font-size="12" fill="#334155">metric value</text>'
    )
    parts.append("</svg>")
    output.write_text("\n".join(parts) + "\n")


def write_csv(model: dict, rows: list[dict], output: Path) -> None:
    """Document the responsibility of ``write_csv``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    fieldnames = ["step", "phase"]
    for metric in model["metrics"]:
        fieldnames.extend([f"{metric}_median", f"{metric}_p10", f"{metric}_p90"])
    with output.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_report(summary: dict, output: Path) -> None:
    """Document the responsibility of ``write_report``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Persist or emit computed data in the format expected by later workflow stages.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    lines = [
        "# Simulated Theory-Evolution Parameters",
        "",
        "These values are simulation-derived plausible priors, not measured system performance.",
        "",
        "## Terminal Status Probabilities",
        "",
    ]
    for status, prob in summary["status_probabilities"].items():
        lines.append(f"- `{status}`: {prob:.3f}")
    lines.extend(["", "## Cost", ""])
    cost = summary["cost"]
    lines.append(f"- mean: {cost['mean']:.3f}")
    lines.append(f"- median: {cost['median']:.3f}")
    lines.extend(["", "## Phase Parameter Estimates", ""])
    lines.append(
        "| Phase | Mean cost | Eta all | Eta protected | Dominant gain | Dominant regression |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | --- |")
    for row in summary["phase_parameter_estimates"]:
        lines.append(
            f"| `{row['phase']}` | {row['mean_cost']:.3f} | {row['mean_eta_all']:.4f} | "
            f"{row['mean_eta_protected']:.4f} | `{row['dominant_gain_metric']}` | `{row['dominant_regression_metric']}` |"
        )
    output.write_text("\n".join(lines) + "\n")


def main() -> int:
    """Document the responsibility of ``main``.

    Motivation:
        Capture the research-paper production workflow as auditable agent skills and helper scripts.

    Intent:
        Serve as the command-line entry point and coordinate argument parsing, execution, and reporting.

    Inputs:
        Accepts the parameters declared in the signature; callers should satisfy the invariants documented by neighboring code and tests.

    Outputs:
        Returns the value or side effect required by the workflow, with errors kept explicit at the call boundary.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--runs", type=int, default=64)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    batch = load_batch(args.model, vars(args))
    batch["runs"] = [
        simulate_one(batch["model"], i, args.seed) for i in range(args.runs)
    ]
    report_batch(batch)
    return 0


def load_batch(model_path: str, options: dict) -> dict:
    """Read the model and create the output directory in native main order."""
    args = argparse.Namespace(runs=64, seed=7, json=False)
    vars(args).update(options, model=model_path)
    model = json.loads(Path(args.model).read_text())
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "model": model,
        "options": vars(args),
        "runs": [],
        "run_id": 0,
        "pending": 0 < args.runs,
    }


def report_batch(batch: dict) -> dict:
    """Aggregate, write the five native artifacts in order, and emit stdout."""
    args = argparse.Namespace(**batch["options"])
    model, runs = batch["model"], batch["runs"]
    output_dir = Path(args.output_dir)
    summary = summarize(model, runs)
    rows = build_step_summary(model, runs)

    simulation = {
        "schema_version": 1,
        "model_id": model.get("model_id"),
        "seed": args.seed,
        "run_count": args.runs,
        "summary": summary,
        "runs": runs,
    }
    sim_path = output_dir / "simulated_trajectories.json"
    summary_path = output_dir / "plausible_parameters.json"
    csv_path = output_dir / "trajectory_summary.csv"
    svg_path = output_dir / "trajectory_shape.svg"
    report_path = output_dir / "plausible_parameters_report.md"

    sim_path.write_text(json.dumps(simulation, indent=2, sort_keys=True) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_csv(model, rows, csv_path)
    render_svg(model, rows, svg_path)
    write_report(summary, report_path)

    result = {
        "ok": True,
        "model": args.model,
        "run_count": args.runs,
        "seed": args.seed,
        "outputs": {
            "simulation": str(sim_path),
            "parameters": str(summary_path),
            "csv": str(csv_path),
            "svg": str(svg_path),
            "report": str(report_path),
        },
        "status_probabilities": summary["status_probabilities"],
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result)
    return result


if __name__ == "__main__":
    raise SystemExit(main())

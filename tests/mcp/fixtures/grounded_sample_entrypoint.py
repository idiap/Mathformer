# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# Frozen pre-extraction orchestration from the selected source.
def run_suite(case_ids: Sequence[str] | None = None) -> dict[str, Any]:
    specs = selected_case_specs(case_ids)
    cases = [audit_case(case_id, spec) for case_id, spec in specs.items()]
    payload = {
        "schema_version": 1,
        "style": "physics_lean_grounded_sample_thoroughness_report",
        "ok": all(item["ok"] for item in cases),
        "case_count": len(cases),
        "cases": cases,
        "policy": {
            "complete_status_required": "complete_autoformalization",
            "forbidden_shortcuts": FORBIDDEN_SHORTCUTS,
            "grounding_direction": "MathformerPhysicsLib-first, Mathlib-grounded, recursive-frontier-empty",
        },
    }
    write_json(ARTIFACT_ROOT / "report.json", payload)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        help="Run the thoroughness gate for one FormalPhysics sample. Repeat to select several.",
    )
    parser.add_argument("--output", type=Path, help="Optional report path.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = run_suite(args.case)
    if args.output:
        write_json(args.output, payload)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Grounded sample thoroughness ok={payload['ok']}")
        print(f"Report: {rel(ARTIFACT_ROOT / 'report.json')}")
    return 0 if payload["ok"] else 1

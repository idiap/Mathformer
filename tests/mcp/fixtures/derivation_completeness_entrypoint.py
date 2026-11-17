# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-FileContributor: Danilo Gusicuma <danilo.gusicuma@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
"""Frozen pre-extraction build_report/main; executed with native helper globals.

Original source SHA256: 501352258b9fd2daae952f44ad37d28a368d92e58eb0d61507a71ffc649a736c
Analysis helpers are shared, so this fixture compares orchestration only.
"""


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_record = load_json(args.source_record)
    plan = load_json(args.recursive_plan)
    frontier_count = args.recursive_frontier_count
    if frontier_count is None:
        frontier_count = recursive_frontier_count(plan)
    files = [Path(path) for path in args.lean_file]
    artifacts = [
        analyze_file(
            lean_file=file,
            source_record=source_record,
            recursive_frontier_count=frontier_count,
        )
        for file in files
    ]
    status_order = {
        COMPLETE_STATUS: 0,
        "derivation_partial": 1,
        "blocked_target_restating_assumption": 2,
        "missing_lean_text": 3,
    }
    status = max(
        (item["status"] for item in artifacts),
        key=lambda value: status_order.get(value, 1),
        default=COMPLETE_STATUS,
    )
    finding_count = sum(len(item["findings"]) for item in artifacts)
    blocked_obligation_count = sum(
        int(item["blocked_obligation_count"]) for item in artifacts
    )
    return {
        "schema_version": 1,
        "style": "physics_lean_derivation_completeness_report",
        "ok": status == COMPLETE_STATUS,
        "status": status,
        "summary": {
            "file_count": len(files),
            "finding_count": finding_count,
            "blocked_obligation_count": blocked_obligation_count,
            "recursive_frontier_count": frontier_count,
            "complete_file_count": sum(1 for item in artifacts if item["complete"]),
        },
        "artifacts": artifacts,
        "acceptance_policy": {
            "complete_status": COMPLETE_STATUS,
            "open_recursive_frontier_blocks_completion": True,
            "target_restating_witness_blocks_completion": True,
            "compiled_surface_is_not_complete": True,
            "allowed_physical_law_witness_roles": [
                "source_law",
                "constitutive_assumption",
                "domain_assumption",
                "bridge_lemma",
                "generated_support",
            ],
            "forbidden_witness_role_for_complete_status": "target_conclusion",
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        report = self_test()
    else:
        if not args.lean_file:
            raise SystemExit("--lean-file is required unless --self-test is used")
        report = build_report(args)
    if args.output:
        write_json(args.output, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={report.get('status')} ok={report.get('ok')}")
    return 1 if args.expect_complete and not report.get("ok") else 0

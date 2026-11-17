<!--
SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
SPDX-License-Identifier: MIT
Neuro-symbolic AI Group
-->

<!--
File Documentation

Motivation:
  Make agent behavior explicit, scoped, and reproducible for specialized Mathformer tasks.

Intent:
  Tell coding agents what context to load, what invariants to preserve, and how to validate their work.

Function:
  Contains skill instructions, prompts, references, and scripts used by Codex-style workflows.

Maintenance Notes:
  Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.
-->

# Gate Decision Shape

Gate decisions use this object shape:

```json
{
  "gate_id": "wiki-level-suite",
  "hook_id": "control.gate_policy",
  "status": "pass",
  "ok": true,
  "checks": [],
  "blocking_failures": [],
  "warnings": [],
  "waivers": [
    {
      "id": "compatibility",
      "owner": "alice",
      "expiry": "2026-06-30",
      "reason": "Accepted during fixture migration",
      "residual_risk": "Minimal import profile not yet enforced"
    }
  ]
}
```

Statuses:

- `pass`: all checks passed.
- `warn`: no blocking failures, but at least one nonblocking check failed.
- `fail`: at least one unwaived blocking check failed.
- `waived`: all blocking failures are explicitly waived.
- `skip`: no checks were supplied.

Waivers are structured records keyed by check id. A waived failed check is still
present in `checks` with `waived: true` and its waiver record attached.

CLI waiver shorthand:

```bash
--waiver check_id:owner:expiry:reason:residual_risk
```

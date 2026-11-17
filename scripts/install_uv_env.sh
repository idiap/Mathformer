#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
# File Documentation
#
# Motivation:
#   Automate repository maintenance tasks that would be error-prone if performed by hand.
#
# Intent:
#   Expose command-line entry points for setup, generation, indexing, auditing, and proof execution.
#
# Function:
#   Implements operational glue used by tests, skills, docs, and developer workflows.
#
# Maintenance Notes:
#   Keep this header synchronized with major responsibility changes, and prefer updating tests or examples when behavior changes.

set -euo pipefail

# Unix convenience wrapper for the cross-platform Python installer.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "$(command -v python3)" ]]; then
  PYTHON_BIN="python3"
elif [[ -n "$(command -v python)" ]]; then
  PYTHON_BIN="python"
else
  echo "Error: Python 3.10+ is required to run scripts/install_env.py." >&2
  exit 1
fi

exec "$PYTHON_BIN" "$ROOT_DIR/scripts/install_env.py" "$@"

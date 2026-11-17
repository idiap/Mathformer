#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright © 2026 Idiap Research Institute <contact@idiap.ch>
# SPDX-FileContributor: Andre Freitas <andre.freitas@idiap.ch>
# SPDX-License-Identifier: MIT
# Neuro-symbolic AI Group
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

if [[ ! -x .venv/bin/python ]]; then
  printf 'Install the locked development environment with uv sync --locked --group dev.\n' >&2
  exit 1
fi
export PATH="$PWD/.venv/bin:$PATH"

status=0
run() {
  printf '\n+ %s\n' "$*"
  "$@" || status=1
}

run pytest
run ruff check .
run black --check .
run pyright
run vulture . --min-confidence 80
run python3 .idiap-sd/idiap_sd.py frontend-test
run reuse lint
run python3 .idiap-sd/idiap_sd.py check
exit "$status"

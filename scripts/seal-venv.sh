#!/bin/bash
# Make the benchmark's own virtualenv read-only, or writable again.
#
#   scripts/seal-venv.sh            # seal it (do this before a long run)
#   scripts/seal-venv.sh --open     # to install something into it
#
# The tasks this benchmark runs ARE Python repositories, and an agent
# reproducing a bug installs the repo it is working on. It inherited the
# harness's virtualenv, so `pip install -e .` rewrote the harness's own
# site-packages: measured across a day, seven SWE-bench repos (django, flask,
# matplotlib, pylint, sphinx, xarray, pytest) were editable-installed there,
# `pytest` was replaced by a task's 4.6.1 checkout and `pluggy` dragged to
# 0.13.1, and the benchmark's own test suite could no longer start. One `.pth`
# pointed into the PREVIOUS DAY's run, so it had been changing what every later
# task imported, silently, across runs.
#
# Two softer guards were tried first and both leak:
#   - dropping VIRTUAL_ENV and the venv from PATH: `tool_path_env` puts the
#     venv back because node lives there;
#   - a `pip` shim earlier on PATH: `python -m pip` and the venv's absolute
#     `bin/pip` never look at PATH.
#
# A read-only directory is the one guard that does not depend on how pip is
# spelled. The harness only ever READS from here at runtime, so sealing costs
# nothing and an agent's install fails with a permission error naming the
# directory — which is exactly what it should say.
set -uo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bench-root.sh"
VENV=$(bench_root)/venv
SP=$(echo "$VENV"/lib/python*/site-packages)

if [ "${1:-}" = "--open" ]; then
    chmod -R u+w "$SP" "$VENV/bin" 2>/dev/null
    echo "writable: $SP"
    echo "re-seal with: scripts/seal-venv.sh"
    exit 0
fi
chmod -R a-w "$SP" 2>/dev/null
chmod a-w "$VENV/bin" 2>/dev/null
echo "sealed: $SP"
"$VENV/bin/python" -c "import phronix, pytest" 2>/dev/null \
    && echo "harness still imports" \
    || echo "** the harness cannot import — run --open and investigate"

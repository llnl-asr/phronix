"""What the run monitor claims about a run's liveness.

The monitor is how a run is watched for hours, so a wrong liveness reading is
expensive in a way a wrong number is not: it decides whether anyone looks.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def bench_top():
    """Load `scripts/bench_top.py` — a script, not an installed module."""
    path = Path("scripts/bench_top.py").resolve()
    spec = importlib.util.spec_from_file_location("bench_top", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["bench_top"] = module
    spec.loader.exec_module(module)
    return module


def _run_dir(tmp_path: Path, *, report: bool) -> Path:
    run = tmp_path / "claude-0831-161928"
    (run / "claude-phronix").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"model": "gpt-oss-120b"}))
    if report:
        (run / "report.json").write_text(json.dumps({"arms": []}))
    return run


def _watcher(bench_top, run: Path):
    for name in dir(bench_top):
        cls = getattr(bench_top, name)
        if isinstance(cls, type) and "finished" in vars(cls):
            return cls(run)
    raise AssertionError("no class on bench_top owns `finished`")


def test_a_run_that_wrote_its_report_is_done_not_active(bench_top, tmp_path):
    """A finished run must not read ACTIVE just because it is recent.

    Both live signals say "active" for a run that is over. `runner_alive`
    needs a `trace.log` to find the pid, and a run that died before its first
    task never wrote one, so it abstains. The silence threshold then compares
    a directory touched minutes ago against a thirty-minute limit and says
    ACTIVE. mix30-reuse died sixty seconds in, both arms, and top reported
    `ACTIVE 14m42s` over it — nobody looked, because it claimed to be working.

    `report.json` is the terminal signal and has to be checked first.
    """
    run = _run_dir(tmp_path, report=True)
    watcher = _watcher(bench_top, run)

    assert watcher.finished is True
    assert watcher.active is False
    assert watcher.state.startswith("DONE")
    # Not "silent": a finished run is over, and calling it silent invites
    # waiting for it to speak again.
    assert "silent" not in watcher.state


def test_a_run_still_working_is_not_called_done(bench_top, tmp_path):
    """The converse, so the fix cannot be `always DONE`."""
    run = _run_dir(tmp_path, report=False)
    watcher = _watcher(bench_top, run)

    assert watcher.finished is False
    assert not watcher.state.startswith("DONE")

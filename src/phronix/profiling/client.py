"""Talk to the collector over HTTP, or report cleanly that there isn't one.

Every call here is best-effort with a short timeout. Profiling is an observation
of the work, never a participant in it: a collector that is down, wedged, or
simply not started must cost a session nothing more than an empty profile.

The endpoint comes from ``PHRONIX_COLLECTOR_URL`` (set by ``phronix_stack env``),
falling back to the default port. Resolved per call rather than cached so that
starting the stack mid-session begins working immediately, without restarting the
MCP server.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

DEFAULT_URL = "http://127.0.0.1:4318"

#: Short on purpose for the hot calls. The collector is local and answers in
#: milliseconds; a longer timeout would only turn "not running" into a visible
#: stall on every step boundary.
TIMEOUT_S = 2.0

#: ``report`` is the exception and needs its own budget: it renders the profile
#: and pushes it to MLflow, which is a database write and a network round trip.
#: Under the hot-path timeout it reported "no collector" for a collector that was
#: working perfectly — the worst kind of wrong answer, because it looks like the
#: feature is simply not set up.
REPORT_TIMEOUT_S = 120.0


def collector_url() -> str:
    return os.environ.get("PHRONIX_COLLECTOR_URL", DEFAULT_URL).rstrip("/")


def _request(path: str, payload: Optional[Dict[str, Any]] = None,
             method: str = "POST", timeout: float = TIMEOUT_S) -> Dict[str, Any]:
    url = f"{collector_url()}{path}"
    data = json.dumps(payload or {}).encode() if method == "POST" else None
    request = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.URLError as exc:
        return {
            "status": "disabled",
            "error": f"no collector at {collector_url()} ({exc.reason})",
            "hint": "Start it with `phronix_stack start`, then export the env with "
                    "`eval \"$(phronix_stack env)\"` BEFORE launching the harness — "
                    "without OTEL_* set, the harness exports nothing and the profile "
                    "stays empty.",
        }
    except Exception as exc:
        return {"status": "disabled", "error": f"{type(exc).__name__}: {exc}"}


def bind(run_id: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    return _request("/bind", {"run_id": run_id, "tags": tags or {}})


def step_begin(step: str, agent: str = "", model_level: str = "") -> Dict[str, Any]:
    return _request("/step/begin",
                    {"step": step, "agent": agent, "model_level": model_level})


def step_end(step: str, status: str = "ok", notes: str = "") -> Dict[str, Any]:
    return _request("/step/end", {"step": step, "status": status, "notes": notes})


def status() -> Dict[str, Any]:
    return _request("/status", method="GET")


def report(mlflow: bool = True) -> Dict[str, Any]:
    return _request("/report", {"mlflow": mlflow}, timeout=REPORT_TIMEOUT_S)

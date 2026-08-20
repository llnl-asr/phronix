"""The profile collector: an OTLP receiver that keeps a per-step profile in memory.

One long-lived process, two jobs:

1. **Receive** OTLP/JSON on ``/v1/logs`` and ``/v1/metrics`` — the endpoints
   Claude Code exports to when ``CLAUDE_CODE_ENABLE_TELEMETRY=1`` and
   ``OTEL_EXPORTER_OTLP_ENDPOINT`` points here.
2. **Serve a control API** on ``/bind``, ``/step``, ``/status``, ``/report`` so the
   phronix MCP tools can open and close step windows and read the profile back.

The profile lives in memory, and that is a deliberate constraint with a
consequence worth stating plainly: **restarting the collector mid-session
discards the cost accounting so far.** The stack launcher therefore never bounces
it for a mere config change. Raw events are appended to disk as they arrive, so a
crash loses the aggregation but not the data — ``phronix_stack`` can rebuild.

Stdlib only (``http.server``): the receiver has to be trivially installable next
to a harness, and taking a web framework for two POST routes would make the whole
profiling path optional in practice.
"""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

from phronix.profiling.aggregate import RunProfile
from phronix.profiling.otlp import parse

#: Cap on the in-memory raw buffer. A long session can emit hundreds of thousands
#: of events; the aggregate is what matters and the raw stream is already on disk.
_RAW_BUFFER_LIMIT = 5000


class Collector:
    """Owns the current run profile and the raw capture file."""

    def __init__(self, root: Path, mlflow_uri: str = "",
                 experiment: str = "phronix") -> None:
        self.root = Path(root)
        self.mlflow_uri = mlflow_uri
        self.experiment = experiment
        self.profile = RunProfile(run_id="(unbound)")
        self.started_at = time.time()
        self.received = 0
        self.dropped = 0
        self._lock = threading.Lock()
        self._raw: List[Dict[str, Any]] = []
        self._raw_path: Optional[Path] = None

    # -- lifecycle ---------------------------------------------------------

    def bind(self, run_id: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Start profiling a session.

        Rebinding to the SAME run id is a no-op that keeps the accumulated
        profile — an agent re-running ``profile_bind`` defensively must not
        silently reset the accounting. Binding to a different id starts fresh.
        """
        with self._lock:
            if self.profile.run_id == run_id:
                return {"status": "already_bound", "run_id": run_id,
                        "steps": len(self.profile.steps)}
            self.profile = RunProfile(run_id=run_id, started_ns=time.time_ns(),
                                      tags=dict(tags or {}))
            self._raw = []
            directory = self.root / run_id
            directory.mkdir(parents=True, exist_ok=True)
            self._raw_path = directory / "otlp-raw.jsonl"
            return {"status": "bound", "run_id": run_id,
                    "raw_capture": str(self._raw_path)}

    def ingest(self, payload: dict) -> int:
        """Parse and attribute one OTLP payload. Returns the record count."""
        records = parse(payload)
        if not records:
            return 0
        with self._lock:
            for record in records:
                self.profile.absorb(record)
                if len(self._raw) < _RAW_BUFFER_LIMIT:
                    self._raw.append(record)
            self.received += len(records)
            self._append_raw(records)
        return len(records)

    def _append_raw(self, records: List[Dict[str, Any]]) -> None:
        """Caller holds the lock. Never fails the ingest over a disk problem."""
        if self._raw_path is None:
            return
        try:
            with self._raw_path.open("a", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, default=str) + "\n")
        except OSError:
            self.dropped += len(records)

    def step_begin(self, step: str, agent: str = "", model_level: str = "") -> Dict[str, Any]:
        with self._lock:
            profile = self.profile.open_step(step, agent, model_level, time.time_ns())
            return {"status": "ok", "step": step, "attempt": profile.attempts,
                    "retry": profile.attempts > 1}

    def step_end(self, step: str, status: str = "ok", notes: str = "") -> Dict[str, Any]:
        with self._lock:
            profile = self.profile.close_step(step, status, notes, time.time_ns())
            if profile is None:
                return {"status": "error",
                        "error": f"step {step!r} was never begun; call "
                                 "profile_step_begin first so its window exists"}
            return {"status": "ok", **profile.to_dict()}

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": "ok",
                "run_id": self.profile.run_id,
                "bound": self.profile.run_id != "(unbound)",
                "uptime_s": round(time.time() - self.started_at, 1),
                "records_received": self.received,
                "records_dropped": self.dropped,
                "steps": len(self.profile.steps),
                "open_steps": [s.step for s in self.profile.steps if s.status == "running"],
                "totals": self.profile.totals(),
                "cross_check": self.profile.drift(),
            }

    def report(self, write_mlflow: bool = True) -> Dict[str, Any]:
        """Render the profile to markdown, and push it to MLflow if configured."""
        with self._lock:
            profile = self.profile.to_dict()
            raw_path = self._raw_path

        directory = self.root / str(profile["run_id"])
        directory.mkdir(parents=True, exist_ok=True)
        report_path = directory / "profile.md"
        json_path = directory / "profile.json"
        try:
            report_path.write_text(render_markdown(profile))
            json_path.write_text(json.dumps(profile, indent=2) + "\n")
        except OSError as exc:
            return {"status": "error", "error": f"could not write report: {exc}"}

        result: Dict[str, Any] = {
            "status": "ok",
            "run_id": profile["run_id"],
            "report": str(report_path),
            "json": str(json_path),
            "totals": profile["totals"],
            "cross_check": profile["cross_check"],
        }
        # Always present, whatever happened. A caller must be able to tell
        # "deliberately skipped" from "tried and failed" from "not installed" —
        # an absent key collapses all three into the same KeyError.
        if not write_mlflow:
            result["mlflow"] = {"status": "skipped",
                                "note": "not requested; the on-disk report is complete"}
        elif not self.mlflow_uri:
            result["mlflow"] = {"status": "disabled",
                                "error": "no MLflow tracking URI configured; "
                                         "start the stack with `phronix_stack start`"}
        else:
            from phronix.profiling import mlflow_sink

            artifacts = [p for p in (report_path, json_path, raw_path) if p]
            result["mlflow"] = mlflow_sink.write(
                profile, self.mlflow_uri, self.experiment, artifacts)
        return result


def render_markdown(profile: Dict[str, Any]) -> str:
    """A per-step cost table, most expensive first."""
    totals = profile.get("totals", {})
    lines = [
        f"# Session profile — {profile.get('run_id')}",
        "",
        f"**{totals.get('cost_usd', 0):.4f} USD** across "
        f"{totals.get('api_calls', 0)} API calls, "
        f"{totals.get('tokens_total', 0):,} tokens, "
        f"{totals.get('tool_calls', 0)} tool calls "
        f"({totals.get('mcp_tool_calls', 0)} via MCP).",
        "",
        "| Step | Agent | Level | Status | Cost | Tokens | API | Tools | Time |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    steps = sorted(profile.get("steps") or [],
                   key=lambda s: -float(s.get("cost_usd", 0)))
    for step in steps:
        retry = f" ×{step['attempts']}" if step.get("attempts", 1) > 1 else ""
        lines.append(
            f"| {step.get('step', '?')}{retry} | {step.get('agent', '')} "
            f"| {step.get('model_level', '')} | {step.get('status', '')} "
            f"| ${step.get('cost_usd', 0):.4f} | {step.get('tokens_total', 0):,} "
            f"| {step.get('api_calls', 0)} | {step.get('tool_calls', 0)} "
            f"| {step.get('duration_s', 0):.0f}s |")

    unattributed = profile.get("unattributed") or {}
    if unattributed.get("api_calls"):
        lines += [
            "",
            f"**Unattributed:** ${unattributed.get('cost_usd', 0):.4f} over "
            f"{unattributed['api_calls']} API calls fell outside every step window. "
            "That is work the step brackets did not cover — usually the main thread "
            "between steps, or steps that were never begun.",
        ]

    cross = profile.get("cross_check") or {}
    if cross.get("events_dropped"):
        lines += ["", f"> **Warning:** {cross.get('note')} "
                      f"(events ${cross.get('event_cost_usd'):.4f} vs "
                      f"metrics ${cross.get('metric_cost_usd'):.4f})"]
    elif not cross.get("checked", True):
        lines += ["", f"> _{cross.get('note')}_"]

    retries = [s for s in steps if s.get("attempts", 1) > 1]
    if retries:
        lines += ["", "## Retries", ""]
        lines += [f"- `{s['step']}` ran {s['attempts']} times "
                  f"(${s.get('cost_usd', 0):.4f} total)" for s in retries]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    collector: Collector = None  # type: ignore[assignment]

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        return  # the access log would drown the useful output

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            return {}

    def _reply(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/status", "/health"):
            self._reply(200, self.collector.status())
        else:
            self._reply(404, {"error": f"no route {self.path}"})

    def do_POST(self) -> None:  # noqa: N802
        route = self.path.split("?")[0].rstrip("/")
        body = self._body()

        # OTLP ingest. Always 200: an exporter that gets an error retries the same
        # payload forever, and a malformed batch would then wedge the pipe.
        if route in ("/v1/logs", "/v1/metrics"):
            count = self.collector.ingest(body)
            self._reply(200, {"partialSuccess": {}, "accepted": count})
            return

        if route == "/bind":
            self._reply(200, self.collector.bind(str(body.get("run_id", "")),
                                                 body.get("tags")))
        elif route == "/step/begin":
            self._reply(200, self.collector.step_begin(
                str(body.get("step", "")), str(body.get("agent", "")),
                str(body.get("model_level", ""))))
        elif route == "/step/end":
            self._reply(200, self.collector.step_end(
                str(body.get("step", "")), str(body.get("status", "ok")),
                str(body.get("notes", ""))))
        elif route == "/report":
            self._reply(200, self.collector.report(bool(body.get("mlflow", True))))
        else:
            self._reply(404, {"error": f"no route {route}"})


def serve(host: str, port: int, collector: Collector) -> ThreadingHTTPServer:
    Handler.collector = collector
    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    """Entry point for ``phronix-profile-collector``."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="phronix-profile-collector",
        description="Receive Claude Code OTLP telemetry and keep a per-step cost profile.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4318)
    parser.add_argument("--root", default="",
                        help="Where profiles are written (default: <cache>/profiles).")
    parser.add_argument("--mlflow-uri", default="",
                        help="MLflow tracking URI; profiles are pushed there on report.")
    parser.add_argument("--experiment", default="phronix")
    args = parser.parse_args()

    if args.root:
        root = Path(args.root).expanduser()
    else:
        from phronix.knowledge_graph import cache_root

        root = cache_root() / "profiles"
    root.mkdir(parents=True, exist_ok=True)

    collector = Collector(root, args.mlflow_uri, args.experiment)
    server = serve(args.host, args.port, collector)
    print(f"[phronix] collector on http://{args.host}:{args.port} -> {root}",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

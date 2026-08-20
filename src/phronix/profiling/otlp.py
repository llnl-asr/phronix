"""Parse OTLP/JSON payloads into flat records.

Claude Code is the telemetry *source*: with ``CLAUDE_CODE_ENABLE_TELEMETRY=1`` it
exports metrics and log events over OTLP. We ask for the ``http/json`` protocol
specifically so the receiver is a couple of hundred lines of stdlib rather than a
protobuf dependency and a vendored ``opentelemetry-proto`` tree.

Two payload roots matter:

* ``resourceLogs`` — the **events**, and what the profile is actually built from.
  ``claude_code.api_request`` carries ``cost_usd``, ``duration_ms`` and all four
  token counts, already attributed to an ``agent.name``; ``claude_code.tool_result``
  carries ``tool_name`` / ``duration_ms`` / ``success``.
* ``resourceMetrics`` — the **counters** (``claude_code.token.usage``,
  ``claude_code.cost.usage``). Kept only as an independent total to cross-check the
  event-derived sums against. If the two diverge, events were dropped — and a cost
  report that is silently missing a third of its calls is worse than none.

Two OTLP encoding quirks are handled in :func:`_anyvalue` and :func:`_as_num` and
must not be "simplified" away: every attribute is a tagged union
(``{"stringValue": "x"}``), and 64-bit integers are JSON-encoded as *strings* to
survive JavaScript's 53-bit float.
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, List, Optional

#: Events worth keeping. Claude Code emits far more; the rest are noise for a
#: cost/performance profile and would bloat the raw capture on disk.
KEPT_EVENTS = frozenset({
    "claude_code.api_request",
    "claude_code.api_error",
    "claude_code.api_retries_exhausted",
    "claude_code.tool_result",
    "claude_code.tool_decision",
    "claude_code.user_prompt",
    "claude_code.skill_activated",
    "claude_code.compaction",
})

#: Metrics kept for the cross-check totals only.
KEPT_METRICS = frozenset({
    "claude_code.token.usage",
    "claude_code.cost.usage",
    "claude_code.active_time.total",
})


def _anyvalue(value: Any) -> Any:
    """Unwrap an OTLP ``AnyValue`` union into a plain Python value."""
    if not isinstance(value, dict):
        return value
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        # The protobuf JSON mapping renders int64 as a string.
        try:
            return int(value["intValue"])
        except (TypeError, ValueError):
            return value["intValue"]
    if "doubleValue" in value:
        return value["doubleValue"]
    if "boolValue" in value:
        return value["boolValue"]
    if "arrayValue" in value:
        return [_anyvalue(v) for v in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return _attrs(value["kvlistValue"].get("values", []))
    return None


def _attrs(items: Optional[List[dict]]) -> Dict[str, Any]:
    """Flatten an OTLP ``KeyValue`` list into a dict."""
    out: Dict[str, Any] = {}
    for entry in items or []:
        key = entry.get("key")
        if key:
            out[key] = _anyvalue(entry.get("value"))
    return out


def as_num(value: Any, default: float = 0.0) -> float:
    """Coerce an attribute to a float. OTLP may hand us ``"1234"`` or ``1234``."""
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _ts_ns(record: dict) -> int:
    """Event timestamp in nanoseconds.

    ``timeUnixNano`` is the emit time and ``observedTimeUnixNano`` the receive
    time; prefer the former. Both arrive as strings.
    """
    raw = record.get("timeUnixNano") or record.get("observedTimeUnixNano") or 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def parse_logs(payload: dict) -> Iterator[Dict[str, Any]]:
    """Yield one flat record per interesting log event.

    Each is ``{"kind": "event", "name", "ts_ns", **resource_attrs, **event_attrs}``.
    Resource attributes are merged first so an event attribute of the same name
    wins — the event is the more specific statement.
    """
    for resource_logs in payload.get("resourceLogs", []):
        resource = _attrs(resource_logs.get("resource", {}).get("attributes"))
        for scope in resource_logs.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                attrs = _attrs(record.get("attributes"))
                name = attrs.get("event.name") or _anyvalue(record.get("body"))
                if name not in KEPT_EVENTS:
                    continue
                yield {"kind": "event", "name": name, "ts_ns": _ts_ns(record),
                       **resource, **attrs}


def parse_metrics(payload: dict) -> Iterator[Dict[str, Any]]:
    """Yield one flat record per interesting metric data point.

    Sums and gauges are the only shapes Claude Code emits; a data point's value
    lives in ``asInt`` (a string) or ``asDouble``.
    """
    for resource_metrics in payload.get("resourceMetrics", []):
        resource = _attrs(resource_metrics.get("resource", {}).get("attributes"))
        for scope in resource_metrics.get("scopeMetrics", []):
            for metric in scope.get("metrics", []):
                name = metric.get("name")
                if name not in KEPT_METRICS:
                    continue
                points = (metric.get("sum") or metric.get("gauge") or {}).get("dataPoints", [])
                for point in points:
                    value = (as_num(point["asInt"]) if "asInt" in point
                             else as_num(point.get("asDouble")))
                    yield {"kind": "metric", "name": name, "ts_ns": _ts_ns(point),
                           "value": value, **resource, **_attrs(point.get("attributes"))}


def parse(payload: dict) -> List[Dict[str, Any]]:
    """Parse either payload shape. Returns a list so callers can count what arrived."""
    if "resourceLogs" in payload:
        return list(parse_logs(payload))
    if "resourceMetrics" in payload:
        return list(parse_metrics(payload))
    return []

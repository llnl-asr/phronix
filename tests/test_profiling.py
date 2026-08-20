"""Profiling: OTLP parsing, step attribution, retries, and the cross-check.

The value of a cost profile is entirely in whether its numbers are true. Each
test here pins one way they could quietly stop being true — an event attributed
to the wrong step, a retry counted as a fresh step, a warning that cries wolf
until nobody reads it.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from phronix.profiling import otlp
from phronix.profiling.aggregate import RunProfile, StepProfile
from phronix.profiling.collector import Collector, render_markdown


def _log(name: str, ts_ns: int = 0, **attrs):
    return {"resourceLogs": [{"resource": {"attributes": []}, "scopeLogs": [{"logRecords": [{
        "timeUnixNano": str(ts_ns or time.time_ns()),
        "attributes": [{"key": "event.name", "value": {"stringValue": name}}] + [
            {"key": k, "value": {"stringValue": str(v)}} for k, v in attrs.items()],
    }]}]}]}


def _api(cost=0.1, tin=1000, tout=100, agent="a", ts_ns=0):
    return _log("claude_code.api_request", ts_ns, cost_usd=cost, duration_ms=500,
                input_tokens=tin, output_tokens=tout, cache_read_tokens=0,
                cache_creation_tokens=0, model="claude-sonnet-5", **{"agent.name": agent})


def _metric(name: str, value: float):
    return {"resourceMetrics": [{"resource": {"attributes": []}, "scopeMetrics": [{"metrics": [{
        "name": name,
        "sum": {"dataPoints": [{"timeUnixNano": str(time.time_ns()),
                                "asDouble": value, "attributes": []}]},
    }]}]}]}


class TestOtlpParsing:
    def test_int64_arrives_as_a_string_and_is_coerced(self):
        """The protobuf JSON mapping renders int64 as a string to survive float53."""
        records = otlp.parse_logs(_log("claude_code.api_request", input_tokens="4000"))
        assert otlp.as_num(list(records)[0]["input_tokens"]) == 4000.0

    def test_uninteresting_events_are_dropped(self):
        assert list(otlp.parse_logs(_log("claude_code.something_else"))) == []

    def test_event_attributes_win_over_resource_attributes(self):
        payload = {"resourceLogs": [{
            "resource": {"attributes": [
                {"key": "model", "value": {"stringValue": "from-resource"}}]},
            "scopeLogs": [{"logRecords": [{
                "timeUnixNano": "1",
                "attributes": [
                    {"key": "event.name",
                     "value": {"stringValue": "claude_code.api_request"}},
                    {"key": "model", "value": {"stringValue": "from-event"}}]}]}]}]}
        assert list(otlp.parse_logs(payload))[0]["model"] == "from-event"

    def test_metric_datapoints_parse(self):
        records = list(otlp.parse_metrics(_metric("claude_code.cost.usage", 1.25)))
        assert records[0]["value"] == 1.25

    def test_parse_dispatches_on_payload_shape(self):
        assert otlp.parse({}) == []
        assert len(otlp.parse(_api())) == 1
        assert len(otlp.parse(_metric("claude_code.cost.usage", 1.0))) == 1

    def test_anyvalue_unwraps_every_union_arm(self):
        assert otlp._anyvalue({"boolValue": True}) is True
        assert otlp._anyvalue({"doubleValue": 1.5}) == 1.5
        assert otlp._anyvalue({"arrayValue": {"values": [{"intValue": "2"}]}}) == [2]


class TestStepAttribution:
    def test_an_event_lands_in_the_step_whose_window_contains_it(self):
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.close_step("one", ts_ns=200)
        profile.open_step("two", ts_ns=300)
        profile.close_step("two", ts_ns=400)

        for ts, expected in ((150, "one"), (350, "two")):
            record = list(otlp.parse_logs(_api(cost=1.0, ts_ns=ts)))[0]
            profile.absorb(record)
            assert profile.find(expected).cost_usd == 1.0
            profile.find(expected).cost_usd = 0.0  # reset for the next assertion

    def test_an_event_outside_every_window_is_kept_as_unattributed(self):
        """Silently dropping it would make the profile look complete while
        under-reporting the bill."""
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.close_step("one", ts_ns=200)
        profile.absorb(list(otlp.parse_logs(_api(cost=0.5, ts_ns=999)))[0])
        assert profile.unattributed.cost_usd == 0.5
        assert profile.totals()["cost_usd"] == 0.5

    def test_an_open_step_absorbs_events_immediately(self):
        """profile_status is meant to be useful mid-run, not only after close."""
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.absorb(list(otlp.parse_logs(_api(cost=0.25, ts_ns=150)))[0])
        assert profile.find("one").cost_usd == 0.25

    def test_totals_never_double_count(self):
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.close_step("one", ts_ns=200)
        for _ in range(3):
            profile.absorb(list(otlp.parse_logs(_api(cost=1.0, ts_ns=150)))[0])
        assert profile.totals()["cost_usd"] == 3.0


class TestRetries:
    def test_reopening_a_step_id_is_a_retry_not_a_new_step(self):
        """Otherwise one expensive step looks like several cheap ones."""
        profile = RunProfile(run_id="r")
        profile.open_step("build", ts_ns=100)
        profile.close_step("build", status="failed", ts_ns=200)
        again = profile.open_step("build", ts_ns=300)
        assert again.attempts == 2
        assert len(profile.steps) == 1

    def test_a_retry_accumulates_cost_onto_the_same_step(self):
        profile = RunProfile(run_id="r")
        profile.open_step("build", ts_ns=100)
        profile.absorb(list(otlp.parse_logs(_api(cost=0.3, ts_ns=150)))[0])
        profile.close_step("build", status="failed", ts_ns=200)
        profile.open_step("build", ts_ns=300)
        profile.absorb(list(otlp.parse_logs(_api(cost=0.2, ts_ns=350)))[0])
        profile.close_step("build", ts_ns=400)
        step = profile.find("build")
        assert step.attempts == 2
        assert abs(step.cost_usd - 0.5) < 1e-9


class TestToolAndErrorCounting:
    def test_mcp_tools_are_counted_separately(self):
        """The MCP share is the signal the complexity tier reads."""
        step = StepProfile(step="s")
        step.absorb({"name": "claude_code.tool_result",
                     "tool_name": "mcp__phronix__skill_load", "duration_ms": 10})
        step.absorb({"name": "claude_code.tool_result", "tool_name": "Edit", "duration_ms": 10})
        assert step.tool_calls == 2 and step.mcp_tool_calls == 1

    def test_a_string_false_counts_as_a_failure(self):
        """OTLP hands booleans through as strings often enough to matter."""
        step = StepProfile(step="s")
        step.absorb({"name": "claude_code.tool_result", "tool_name": "Edit",
                     "success": "false"})
        assert step.tool_failures == 1

    def test_api_errors_are_counted(self):
        step = StepProfile(step="s")
        step.absorb({"name": "claude_code.api_error", "duration_ms": 5})
        step.absorb({"name": "claude_code.api_retries_exhausted", "duration_ms": 5})
        assert step.api_errors == 2


class TestCrossCheck:
    def test_no_metric_stream_is_not_reported_as_dropped_events(self):
        """A permanent false alarm is the fastest way to train people to ignore
        a warning that will one day be real."""
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.absorb(list(otlp.parse_logs(_api(cost=1.0, ts_ns=150)))[0])
        cross = profile.drift()
        assert cross["events_dropped"] is False
        assert cross["checked"] is False

    def test_agreeing_totals_report_agreement(self):
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.absorb(list(otlp.parse_logs(_api(cost=1.0, ts_ns=150)))[0])
        profile.absorb(list(otlp.parse_metrics(_metric("claude_code.cost.usage", 1.0)))[0])
        cross = profile.drift()
        assert cross["checked"] and not cross["events_dropped"]

    def test_a_large_gap_is_flagged(self):
        profile = RunProfile(run_id="r")
        profile.open_step("one", ts_ns=100)
        profile.absorb(list(otlp.parse_logs(_api(cost=1.0, ts_ns=150)))[0])
        profile.absorb(list(otlp.parse_metrics(_metric("claude_code.cost.usage", 5.0)))[0])
        assert profile.drift()["events_dropped"] is True


class TestCollector:
    def test_rebinding_the_same_run_keeps_the_profile(self, tmp_path):
        """An agent re-binding defensively must not reset the accounting."""
        collector = Collector(tmp_path)
        collector.bind("r1")
        collector.step_begin("one")
        assert collector.bind("r1")["status"] == "already_bound"
        assert collector.status()["steps"] == 1

    def test_binding_a_different_run_starts_fresh(self, tmp_path):
        collector = Collector(tmp_path)
        collector.bind("r1")
        collector.step_begin("one")
        collector.bind("r2")
        assert collector.status()["steps"] == 0

    def test_ending_a_step_that_never_began_is_an_error_not_a_crash(self, tmp_path):
        collector = Collector(tmp_path)
        collector.bind("r1")
        result = collector.step_end("never-started")
        assert result["status"] == "error" and "never begun" in result["error"]

    def test_raw_events_are_captured_to_disk(self, tmp_path):
        """A crash should lose the aggregation, not the data."""
        collector = Collector(tmp_path)
        collector.bind("r1")
        collector.ingest(_api(cost=0.2))
        raw = tmp_path / "r1" / "otlp-raw.jsonl"
        assert raw.is_file()
        assert json.loads(raw.read_text().splitlines()[0])["name"] == "claude_code.api_request"

    def test_report_writes_markdown_and_json(self, tmp_path):
        collector = Collector(tmp_path)
        collector.bind("r1")
        collector.step_begin("one", agent="phronix-router", model_level="level_2")
        collector.ingest(_api(cost=0.2))
        collector.step_end("one")
        result = collector.report(write_mlflow=False)
        assert result["status"] == "ok"
        assert Path(result["report"]).is_file() and Path(result["json"]).is_file()
        assert result["mlflow"]["status"] == "skipped"

    def test_mlflow_key_is_always_present(self, tmp_path):
        """Skipped, disabled and failed must be distinguishable — an absent key
        collapses all three into the same KeyError."""
        collector = Collector(tmp_path)
        collector.bind("r1")
        assert collector.report(write_mlflow=False)["mlflow"]["status"] == "skipped"
        assert collector.report(write_mlflow=True)["mlflow"]["status"] == "disabled"

    def test_ingest_of_junk_is_harmless(self, tmp_path):
        collector = Collector(tmp_path)
        collector.bind("r1")
        assert collector.ingest({"nonsense": True}) == 0


class TestReportRendering:
    def _profile(self):
        collector = Collector(Path("/tmp"))
        collector.bind("r1")
        collector.step_begin("cheap", agent="a", model_level="level_1")
        collector.ingest(_api(cost=0.01))
        collector.step_end("cheap")
        collector.step_begin("dear", agent="b", model_level="level_4")
        collector.ingest(_api(cost=0.90))
        collector.step_end("dear", status="failed")
        collector.step_begin("dear", agent="b", model_level="level_4")
        collector.step_end("dear")
        return collector.profile.to_dict()

    def test_steps_are_ordered_most_expensive_first(self):
        body = render_markdown(self._profile())
        assert body.index("| dear") < body.index("| cheap")

    def test_a_retry_is_marked_in_the_table(self):
        assert "dear ×2" in render_markdown(self._profile())

    def test_the_model_level_appears_next_to_the_cost(self):
        """The pairing that makes the complexity tier falsifiable."""
        body = render_markdown(self._profile())
        assert "level_4" in body and "level_1" in body


class TestMlflowSink:
    def test_absent_mlflow_is_reported_not_raised(self, monkeypatch):
        from phronix.profiling import mlflow_sink

        monkeypatch.setattr(mlflow_sink, "available", lambda: False)
        result = mlflow_sink.write({"run_id": "r"}, "sqlite:///x.db")
        assert result["status"] == "unavailable"
        assert "pip install" in result["error"]

    def test_params_are_clipped_for_mlflow_limits(self):
        from phronix.profiling.mlflow_sink import _sanitise

        assert len(_sanitise("x" * 900)) == 250
        assert "\n" not in _sanitise("a\nb")


class TestClient:
    def test_no_collector_reports_disabled_with_a_hint(self, monkeypatch):
        """Profiling observes the work; it must never be why a session fails."""
        from phronix.profiling import client

        monkeypatch.setenv("PHRONIX_COLLECTOR_URL", "http://127.0.0.1:1")
        result = client.status()
        assert result["status"] == "disabled"
        assert "phronix_stack start" in result["hint"]

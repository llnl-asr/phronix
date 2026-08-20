"""Write a run profile to MLflow: one parent run, one nested run per step.

MLflow is the reporting surface, not the source of truth — the profile is
reconstructable from the raw capture on disk, and that matters because MLflow is
the part most likely to be unavailable (not installed, server down, wrong URI).
Every write here therefore degrades to a reported error rather than an exception,
and the profile stays intact and reportable without it.

The run shape:

* **Parent run** = the session. Tags identify the project and the phronix
  version; metrics are the totals; the raw capture is attached as an artifact.
* **Nested run per step** = one row you can sort by cost. Its params record the
  agent and the model *level* it ran at.

That last point is the phronix-specific reason this exists at all. Recording the
level alongside the cost is what lets you ask the question the complexity tier
raises but cannot answer on its own: *was that level the right call?* A step
pinned at ``level_4`` that spent most of its tokens on tool orchestration is
visible here and nowhere else.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

#: Metrics logged per step. Names are flat and MLflow-safe (no dots, which MLflow
#: permits but which read badly in its UI's metric picker).
_STEP_METRICS = (
    "cost_usd", "duration_s", "tokens_total", "tokens_input", "tokens_output",
    "tokens_cache_read", "tokens_cache_creation", "api_calls", "api_errors",
    "api_duration_s", "tool_calls", "tool_failures", "mcp_tool_calls",
    "tool_duration_s", "compactions", "prompts", "attempts",
)


def available() -> bool:
    try:
        import mlflow  # noqa: F401

        return True
    except Exception:
        return False


def _sanitise(value: Any, limit: int = 250) -> str:
    """MLflow rejects params over 500 chars and mangles newlines; clip early."""
    text = str(value).replace("\n", " ").strip()
    return text[:limit]


def write(
    profile: Dict[str, Any],
    tracking_uri: str,
    experiment: str = "phronix",
    artifacts: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """Write *profile* to MLflow. Never raises.

    Args:
        profile: the dict from :meth:`phronix.profiling.aggregate.RunProfile.to_dict`.
        tracking_uri: e.g. ``sqlite:///.../mlflow.db`` or ``http://127.0.0.1:5001``.
        experiment: MLflow experiment name.
        artifacts: files to attach to the parent run (the raw capture, the report).

    Returns ``{status, run_id, ui_hint}`` or ``{status: "error", error}``.
    """
    if not available():
        return {"status": "unavailable",
                "error": "mlflow is not installed — `pip install phronix[mlflow]`. "
                         "The profile itself is unaffected and still reportable."}
    try:
        import mlflow
    except Exception as exc:  # pragma: no cover - guarded by available()
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    try:
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment)
    except Exception as exc:
        return {"status": "error",
                "error": f"could not reach MLflow at {tracking_uri}: "
                         f"{type(exc).__name__}: {exc}"}

    totals = profile.get("totals", {})
    run_id = str(profile.get("run_id", "unknown"))

    try:
        with mlflow.start_run(run_name=run_id) as parent:
            from phronix import __version__

            mlflow.set_tags({
                "phronix.run_id": run_id,
                "phronix.version": __version__,
                **{f"phronix.{k}": _sanitise(v)
                   for k, v in (profile.get("tags") or {}).items()},
            })
            for key in _STEP_METRICS:
                if key in totals:
                    mlflow.log_metric(f"total_{key}", float(totals[key]))
            mlflow.log_metric("steps", len(profile.get("steps") or []))

            cross = profile.get("cross_check") or {}
            if cross:
                mlflow.log_metric("cross_check_gap_usd", float(cross.get("gap_usd", 0.0)))
                # A tag, not a metric: it is a yes/no fact about whether these
                # numbers can be trusted, and it should be filterable in the UI.
                mlflow.set_tag("phronix.events_dropped",
                               str(bool(cross.get("events_dropped"))))

            for path in artifacts or []:
                try:
                    if Path(path).is_file():
                        mlflow.log_artifact(str(path))
                except Exception:
                    continue  # an unattachable artifact must not lose the run

            for step in profile.get("steps") or []:
                _write_step(mlflow, step)

            parent_id = parent.info.run_id
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    return {
        "status": "ok",
        "run_id": parent_id,
        "experiment": experiment,
        "tracking_uri": tracking_uri,
        "ui_hint": ("Open the MLflow UI (`phronix_stack start` runs one) and sort the "
                    "nested runs by cost_usd to see where the session's money went."),
    }


def _write_step(mlflow: Any, step: Dict[str, Any]) -> None:
    """One nested run per step. Failures are swallowed per step, not per run."""
    try:
        with mlflow.start_run(run_name=step.get("step", "?"), nested=True):
            mlflow.log_params({
                "agent": _sanitise(step.get("agent", "")),
                "model_level": _sanitise(step.get("model_level", "")),
                "status": _sanitise(step.get("status", "")),
                "models": _sanitise(",".join(step.get("models") or {})),
            })
            if step.get("notes"):
                mlflow.set_tag("notes", _sanitise(step["notes"], 500))
            for key in _STEP_METRICS:
                if key in step:
                    mlflow.log_metric(key, float(step[key]))
    except Exception:
        # One malformed step must not abort the parent run and lose every other
        # step's numbers with it.
        return

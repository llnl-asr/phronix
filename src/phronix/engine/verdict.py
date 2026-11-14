"""A validator's verdict and the corrector loop's budget: the predictor -> validator -> corrector discipline every
capability follows. Deterministic: same input, same verdict, no model in the loop."""
from __future__ import annotations

from typing import Any, Dict


class Verdict:
    """A validator's findings: each check names what is wrong and how to fix it, so the agent need not re-diagnose. Same input, same verdict:
    no model in the loop. ``assume`` is what must hold for the checks to mean anything: when it does not, the result is inconclusive, never a failure."""

    def __init__(self, stage_name: str) -> None:
        self.stage, self.checks = stage_name, []

    def check(self, name: str, ok: bool, detail: str = "", fix: str = "") -> bool:
        self.checks.append({"name": name, "ok": bool(ok), "detail": detail[:400], "fix": "" if ok else fix[:400]})
        return bool(ok)

    def assume(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append({"name": name, "ok": True if ok else None, "detail": detail[:400], "fix": ""})
        return bool(ok)

    def inconclusive(self, name: str, detail: str) -> None:
        self.checks.append({"name": name, "ok": None, "detail": detail[:400], "fix": ""})

    def result(self) -> Dict[str, Any]:
        failed = [c for c in self.checks if c["ok"] is False]
        unknown = [c for c in self.checks if c["ok"] is None]
        return {"status": "fail" if failed else "inconclusive" if unknown else "pass", "stage": self.stage,
                "failed": failed, "unknown": unknown, "passed": sum(1 for c in self.checks if c["ok"]), "total": len(self.checks)}


START_ATTEMPTS, MAX_ATTEMPTS = 3, 5


def _attempts(s: Dict[str, Any], r: Dict[str, Any]) -> Dict[str, Any]:
    """The corrector loop's budget, from measured progress: a changed failure earns an attempt, the same failure twice ends it."""
    a = s.setdefault("attempts", {"count": 0, "budget": START_ATTEMPTS, "last": None})
    if r["status"] == "pass":
        a["last"] = None
        return {"state": "done", **a}
    if r["status"] == "inconclusive":
        return {"state": "inconclusive", **a}
    sig = sorted(f["name"] for f in r["failed"])
    a["count"] += 1
    if a["last"] == sig:
        return {"state": "stalled", **a}
    if a["last"] is not None and len(sig) < len(a["last"]):
        a["budget"] = min(MAX_ATTEMPTS, a["budget"] + 2)     # fewer checks fail: closer
    elif a["last"] is not None:
        a["budget"] = min(MAX_ATTEMPTS, a["budget"] + 1)     # a different failure: the idea moved
    a["last"] = sig
    return {"state": "exhausted" if a["count"] >= a["budget"] else "correcting", **a}


attempts = _attempts

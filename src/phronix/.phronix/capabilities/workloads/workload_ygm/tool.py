"""workload_ygm: DEPRECATED redirect stub (dftracer-agents' workload-ygm). YGM knowledge is split between software_ygm (the YGM
library, annotated BY dftracer) and workload_ygm_bench (ygm-bench, the traced benchmark). The predictor returns the redirect
and the split history; the validator flags proposals that try to put YGM-library or ygm-bench facts here."""
import json
import re

CAP = "workload_ygm"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "YGM (deprecated stub)",
    "deprecated": True,
    "redirect": {
        "software_ygm": "the YGM library itself: annotation caveats (header-only + split .ipp, include order), build/CMake linkage "
                        "to dftracer, Cray-clang-vs-spdlog compiler pitfall, smoke test. YGM is annotated BY dftracer, not a "
                        "traced scientific workload, hence software_* naming (feedback-software-vs-workload-naming)",
        "workload_ygm_bench": "ygm-bench (github.com/llnl/ygm-bench), the traced BENCHMARK run against the annotated YGM tree: build "
                              "steps, hot-loop over-annotation + selective-aggregation fix, MPI_Iallreduce rank-density collapse, "
                              "irecv buffer OOM/env-var-name pitfall, the confirmed >=10-minute scaled-run reference config "
                              "(same workload_* pattern as workload_ior / workload_h5bench)",
    },
    "history": [
        "2026-08-04: reconciled during the ygm/20260804_221748 session's final report pass into a single software-ygm file",
        "2026-08-04 (same day): split again per user correction: ygm-bench gets its own workload skill, as IOR/h5bench do",
    ],
    "policy": "do not re-add content here: edit software_ygm or workload_ygm_bench, matching which one owns the fact",
    "variants": {},
}

# this stub owns no facts: any proposal that carries YGM build/run content belongs to software_ygm or workload_ygm_bench
RULES = [
    {"id": "no_library_facts", "forbid": r"(?i)\.ipp\b|spdlog|include order|header-only|ygm/(?:comm|container)|-DYGM_|find_package\(ygm",
     "why": "YGM library facts (annotation, build/CMake linkage, compiler pitfalls) belong to software_ygm",
     "fix": "put this in software_ygm instead (capability_update software_ygm)"},
    {"id": "no_bench_facts", "forbid": r"(?i)around_the_world_ygm|barrier_bench|ygm-bench|FETCHCONTENT_SOURCE_DIR_YGM|YGM_COMM_IRECV|Iallreduce|DFTRACER_AGGREGATION",
     "why": "ygm-bench build/run/scaling facts belong to workload_ygm_bench",
     "fix": "put this in workload_ygm_bench instead (capability_update workload_ygm_bench)"},
]


# ---------------------------------------------------------------- shared logic (same in every workload_* capability)
def _commands(commands):
    if isinstance(commands, str):
        s = commands.strip()
        if s.startswith("[") or s.startswith("{"):
            try:
                commands = json.loads(s)
            except ValueError:
                commands = s.splitlines()
        else:
            commands = s.splitlines()
    if isinstance(commands, dict):
        flat = []
        for v in commands.values():
            flat += v if isinstance(v, list) else [v]
        commands = flat
    return [str(c) for c in (commands or []) if str(c).strip()]


def _check(commands):
    cmds = _commands(commands)
    if not cmds:
        return {"status": "inconclusive", "checks": [{"check": "input", "ok": False, "detail": "no commands given",
                                                      "fix": f"pass the proposed commands (e.g. {CAP}_recipe's configure/build/run)"}]}
    text = "\n".join(cmds)
    out = []
    for r in RULES:
        if "forbid" in r:
            hit = [c for c in cmds if re.search(r["forbid"], c)]
            out.append({"check": r["id"], "ok": not hit, "detail": (r["why"] + " | offending: " + hit[0][:160]) if hit else "ok",
                        "fix": r["fix"] if hit else ""})
        else:
            if r.get("when") and not re.search(r["when"], text):
                continue
            ok = bool(re.search(r["require"], text))
            out.append({"check": r["id"], "ok": ok, "detail": "ok" if ok else r["why"], "fix": "" if ok else r["fix"]})
    return {"status": "pass" if all(c["ok"] for c in out) else "fail", "checks": out}


def _recipe(variant=""):
    rec = dict(RECIPE)
    v = (variant or "").strip()
    if v:
        if v not in RECIPE.get("variants", {}):
            return {"status": "error", "error": f"unknown variant {v!r}", "variants": sorted(RECIPE.get("variants", {}))}
        rec["variants"] = {v: RECIPE["variants"][v]}
    return {"status": "ok", "capability": CAP, "recipe": rec,
            "rules": [{"id": r["id"], "why": r["why"], "fix": r["fix"]} for r in RULES]}




def register(mcp):
    @mcp.tool()
    def workload_ygm_recipe(variant: str = "") -> dict:
        """Predictor: DEPRECATED stub. Returns the redirect for YGM knowledge (software_ygm for the library, workload_ygm_bench
        for the traced benchmark), the split history (2026-08-04) and the policy not to add content here. Use when something
        still references workload-ygm. variant: optional (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_ygm_check(commands: list) -> dict:
        """Validator: check a proposed addition (recipe lines, commands or fact text) aimed at this deprecated stub: fails when it
        carries YGM-library facts (belong to software_ygm) or ygm-bench facts (belong to workload_ygm_bench). commands: list of
        lines (or a newline-separated string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

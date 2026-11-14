"""workload_ygm_bench: the ygm-bench (github.com/llnl/ygm-bench, traced benchmark of the YGM library) build/run recipe that
dftracer-agents' workload-ygm-bench skill verified on Tuolumne (build against the annotated YGM tree, selective aggregation,
rank density, irecv buffer env, the >=10-minute reference config), as structured data (predictor), and a deterministic check
of a proposed recipe or command list against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_ygm_bench"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "ygm-bench",
    "repo": "https://github.com/llnl/ygm-bench",
    "what": "the traced BENCHMARK that exercises YGM (same role as IOR/h5bench for their libraries); YGM itself is software_ygm",
    "build_system": "cmake",
    "systems": ["tuolumne"],
    "toolchain": "GNU toolchain, single MPI runtime",
    "configure": [
        "cmake -S ygm-bench -B build -DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source",
    ],
    "build": ["cmake --build build -j"],
    "build_notes": [
        "CMakeLists tries find_package(ygm CONFIG) first, else FetchContent_Declare(ygm GIT_REPOSITORY ...): the annotated YGM tree "
        "has no install()/export() rules, so find_package never succeeds and it would silently fetch a FRESH, UNANNOTATED ygm",
        "-DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source makes FetchContent_MakeAvailable(ygm) use the local annotated tree: "
        "no CMakeLists.txt patch in either repo (general FETCHCONTENT_SOURCE_DIR_<NAME> pattern, dftracer-annotation-lessons 2026-08-04)",
        "annotated YGM links dftracer_core_imported into its ygm INTERFACE target, so target_link_libraries(... ygm::ygm) picks up "
        "dftracer transitively: confirm with `ldd <binary> | grep dftracer`",
        "each ygm-bench entry point (around_the_world_ygm.cpp, barrier_bench.cpp, ...) needs its own DFTRACER_CPP_INIT()/"
        "DFTRACER_CPP_FINI() in main(): otherwise every DFTRACER_CPP_FUNCTION reached through YGM is a silent no-op",
        "the prerelease wheel (tools_dftracer) does not ship dftracer_service: for the node-counter daemon install a second "
        "from-source dftracer for that binary while linking the app against the dftracer matching its compiler ABI",
    ],
    "smoke": [
        "around_the_world_ygm -n 50 -t 2 -p   # 1 node / 4 ranks",
        "barrier_bench -b 500 -a 0 -t 2 -p    # 1 node / 4 ranks",
    ],
    "smoke_trace": {"rank_file_events": 8222, "CPP_APP": 3686, "p2p": 3361, "env": 772, "collective": 264, "POSIX": 69,
                    "dftracer(meta)": 32, "STDIO": 22, "comm": 16,
                    "meaning": "annotated comm/collective activity dominates, not init/POSIX noise"},
    "env": {
        "DFTRACER_ENABLE_AGGREGATION": "1",
        "DFTRACER_AGGREGATION_TYPE": "SELECTIVE",
        "DFTRACER_AGGREGATION_FILE": "<path-to-rules.yaml>",
        "DFTRACER_TRACE_INTERVAL_MS": "5000",
    },
    "aggregation_rules_yaml": "inclusion:\n  - \"dur < 1000\"\nexclusion: []\n",
    "hot_path_functions": ["local_progress", "local_wait_until", "process_receive_queue", "flush_next_send",
                           "check_completed_sends", "check_if_production_halt_required", "post_new_irecv",
                           "local_process_incoming", "handle_completed_send"],
    "run": ["flux run -N 4 --tasks-per-node=32 ygm-bench/src/around_the_world_ygm -n 5600 -t 1 -p"],
    "reference_run": {
        "date": "2026-08-04",
        "command": "ygm-bench/src/around_the_world_ygm -n 5600 -t 1 -p",
        "layout": "4 nodes x 32 ranks/node (128 total)",
        "result": "660.04 s (11.0 min), 716,800 hops, MAX_WAITSOME_IALLREDUCE=646 s, 55 MB trace over 128 rank files",
        "buffers": "default (YGM_COMM_NUM_IRECVS / YGM_COMM_IRECV_SIZE_KB unset)",
        "scaling": "n=500 -> 70.2 s, n=5000 -> 572 s, n=5600 -> 660 s at 128 ranks (roughly linear in -n with aggregation)",
    },
    "rank_density": {
        "untraced_4_ranks_1_node": "510K hops/s",
        "untraced_32_ranks_1_node": "1,229 hops/s (~400x collapse), MAX_WAITSOME_IALLREDUCE 130.2 s of 130.1 s",
        "advice": "32 ranks/node usable; 96 ranks/node -> tens of minutes + OOM risk",
    },
    "irecv_buffers": {
        "default": "YGM_COMM_NUM_IRECVS=8 x 1 GB = 8 GB/rank; at 96 ranks/node ~768 GB -> OOM (memory.peak ~476.87G cgroup ceiling)",
        "env_name": "YGM_COMM_IRECV_SIZE_KB (singular IRECV); YGM_COMM_IRECVS_SIZE_KB (plural) is only the JSON display label "
                    "(comm_environment.hpp ~169) and silently no-ops; getenv reads the singular (~112)",
        "too_small": "64 MB at 96 ranks/node avoided OOM but looked like a deadlock (~6 GB/501 GB used, no progress): likely the "
                     "Iallreduce collapse taken further, not confirmed",
        "safe": "32 ranks/node with default buffers (256 GB/node) worked reliably",
    },
    "variants": {},
    "notes": [
        "hot-loop over-annotation (9 progress-poll functions) made 128-rank traced runs 5-10x+ slower, wall time independent of -n; "
        "unaggregated attempt produced >1 GB PER RANK",
        "fix used: keep the annotations and enable selective aggregation (not a full strip): real dft_cnt counts on aggregated CPP_APP events",
        "MPI_Iallreduce collapse at high per-node rank density is a real Cray MPICH/system finding (measured with DFTRACER_ENABLE=0)",
    ],
}

RULES = [
    {"id": "fetchcontent_annotated", "require": r"-DFETCHCONTENT_SOURCE_DIR_YGM=\S+", "when": r"\bcmake\b.*ygm-bench|\bcmake\b.*-S",
     "why": "find_package(ygm) never succeeds on the annotated tree; FetchContent would silently clone a fresh UNANNOTATED ygm",
     "fix": "-DFETCHCONTENT_SOURCE_DIR_YGM=<ws>/annotated/source"},
    {"id": "irecv_env_name", "forbid": r"YGM_COMM_IRECVS_SIZE_KB",
     "why": "YGM_COMM_IRECVS_SIZE_KB (plural) is only the JSON output label; getenv reads YGM_COMM_IRECV_SIZE_KB, so it silently no-ops",
     "fix": "use YGM_COMM_IRECV_SIZE_KB (singular), or leave buffers at default with 32 ranks/node"},
    {"id": "rank_density", "forbid": r"(?:--tasks-per-node|--ntasks-per-node|-ppn|--ppn)[= ]\s*(?:3[3-9]|[4-9]\d|\d{3,})\b",
     "why": "MPI_Iallreduce collapses ~400x at high per-node rank density and default irecv buffers OOM at 96 ranks/node",
     "fix": "use 32 ranks/node (reference: 4 nodes x 32)"},
    {"id": "selective_aggregation", "require": r"DFTRACER_AGGREGATION_TYPE=SELECTIVE",
     "when": r"DFTRACER_ENABLE=1|around_the_world_ygm.*-n\s*\d{3,}",
     "why": "the annotated hot progress-poll path makes traced runs 5-10x+ slower and >1 GB/rank without aggregation",
     "fix": "export DFTRACER_ENABLE_AGGREGATION=1 DFTRACER_AGGREGATION_TYPE=SELECTIVE DFTRACER_AGGREGATION_FILE=<rules.yaml> DFTRACER_TRACE_INTERVAL_MS=5000"},
    {"id": "aggregation_file", "require": r"DFTRACER_AGGREGATION_FILE=\S+", "when": r"DFTRACER_AGGREGATION_TYPE=SELECTIVE",
     "why": "selective aggregation needs the rules file (inclusion: dur < 1000)", "fix": "DFTRACER_AGGREGATION_FILE=<path-to-rules.yaml>"},
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
    def workload_ygm_bench_recipe(variant: str = "") -> dict:
        """Predictor: the ygm-bench build/run recipe dftracer-agents verified on Tuolumne (FETCHCONTENT_SOURCE_DIR_YGM to the
        annotated YGM, per-entry-point INIT/FINI, selective-aggregation env + rules.yaml, 32 ranks/node, irecv buffer env name,
        the 4x32 / -n 5600 / 11-minute reference run) as structured JSON. Use before building or tracing ygm-bench. variant:
        optional (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_ygm_bench_check(commands: list) -> dict:
        """Validator: check a proposed ygm-bench recipe or command list against the skill's rules (FETCHCONTENT_SOURCE_DIR_YGM
        set, singular YGM_COMM_IRECV_SIZE_KB, <=32 ranks/node, selective aggregation for traced/scaled runs with a rules file).
        commands: list of shell lines (or a newline-separated string / JSON text). Returns
        {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

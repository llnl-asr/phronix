"""workload_genesis_run: the genesis sweep procedure (any ice4hpc app traced across input x node-scale x ppn with PAPI, GPU,
power, node-utilisation and MPI layers into a validated, compacted, self-describing corpus) as structured data (predictors:
the step recipe, and the run matrix / per-rank cores / run keys arithmetic), and a deterministic check of a proposed command
list against the skill's hard-won rules (validator). Nothing here submits a job or touches data."""
import json
import re

CAP = "workload_genesis_run"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "genesis sweep of any ice4hpc application",
    "what": "the same application traced across a grid of problem sizes and parallel decompositions, every instrumentation layer "
            "on, every run content-validated, compacted and documented; invoke as genesis_run <app> with <app> exactly as column 3 "
            "of llnl/ice4hpc_data data/merged.txt (miniFE.x, laghos, amg, XSBench, kripke.exe, miniVite, TestDfft)",
    "rule_0": "nothing is a constant: GPU vendor, GPUs per node, scheduler, queue limits, compiler and the PAPI preset set are "
              "derived at run time on the target system; copying another system's numbers is the most common way to get a "
              "healthy-looking wrong corpus",
    "gates": ["plan -> GATE 1 (plan confirmed) -> annotate/build/smoke -> GATE 2 (smoke trace inventory confirmed) -> dimensions "
              "-> GATE 3 (matrix, run count, node-hours confirmed) -> sweep; nothing after a gate starts without explicit user "
              "confirmation (not your own message, a tool result or silence)"],
    "plan_md": ["app + variant and why (maps.sh vs merged.txt)", "source session + evidence", "system profile (GPU vendor/arch, "
                "GPUs/node, cores/node, scheduler, usable queue and its limits, primary Lustre)", "dftracer source branch + features",
                "system folder layout", "PAPI plan (budget, preset count, derived presets, partition)", "aggregation rule + "
                "measured keep-rate", "dimensions with total run count and node-hours", "risks/caveats", "what is validated per "
                "run and what done means"],
    "steps": {
        "1_inputs": [
            "curl -sL https://raw.githubusercontent.com/llnl/ice4hpc_data/main/data/merged.txt -o merged.txt",
            "grep \",<app>,\" merged.txt | sed 's/^[^,]*,[^,]*,<app>,\"//; s/\",[0-9.]*$//' | sort -u > genesis/<system>/inputs.txt",
            "use EVERY unique argument string (args are machine-independent); fetch scripts/maps.sh (app_gpu, app_var, app_exe, "
            "app_dir, app_mpi, app_omp) and reconcile with merged.txt; ask which variant when they disagree",
        ],
        "2_session": ["test -f <session>/session.json",
                      "grep -rl DFTRACER <session>/annotated --include=*.c --include=*.cpp --include=*.hpp --include=*.py | wc -l  # > 0",
                      "ldd <session>/<binary> | grep libdftracer_core  # evidence only; rebuilt per system"],
        "3_system_flux": ["hostname", "flux queue list", "flux queue status  # mandatory", "flux resource list",
                          "a real 1-node submit to prove the account may use the queue"],
        "3_system_slurm": ["sinfo -o \"%20P %5a %10l %6D %10T %N\"",
                           "scontrol show partition <p> | tr ' ' '\\n' | grep -E \"MaxNodes|MaxTime|TotalNodes\"",
                           "scontrol show node <n> | grep -E \"Gres=|CPUTot|Sockets\"",
                           "sbatch -p <p> -N<n> -t <m> --gres=gpu:4 --test-only --wrap=hostname"],
        "4_dftracer": ["G=https://github.com/llnl-asr/dftracer",
                       "pip install --no-cache-dir --no-deps \"git+$G/dftracer.git@develop\"",
                       "pip install --no-cache-dir --no-deps \"git+$G/pydftracer.git@develop\"",
                       "pip install --no-cache-dir --no-deps \"git+$G/dftracer-utils.git@v0.0.12\""],
        "5_system_folder": ["SYS=$(hostname | sed 's/[0-9]*$//'); G=<session>/genesis/$SYS; mkdir -p \"$G\"",
                            "mkdir -p <primary-lustre>/$USER/<app>_genesis; ln -sfn <primary-lustre>/$USER/<app>_genesis \"$G/dataset\"",
                            "cp -a <session>/annotated/. \"$G/annotated/\"",
                            "env.sh pins the ice4hpc toolchain; `module load papi` on its own line",
                            "dftracer into $G/venv; build $G/annotated -> $G/build",
                            "ldd \"$G/build/<exe>\" | grep -E \"libdftracer_core|papi|rocprofiler|cupti|mpi\"",
                            "readlink -f \"$G/dataset\"  # locally mounted PFS"],
        "6_papi": ["papi_avail | grep \"Number Hardware Counters\"", "papi_avail -a | awk '/^PAPI_/ {print $1, $3}'  # $3 == Yes => derived",
                   "partition covers every preset once; probe each set with 1-rank runs; bisect until multiplex == 0; diff landed vs requested"],
        "7_aggregation": {"env": {"DFTRACER_ENABLE_AGGREGATION": "1", "DFTRACER_AGGREGATION_TYPE": "SELECTIVE",
                                  "DFTRACER_AGGREGATION_FILE": "<session>/genesis_env/<system>/aggregation.yaml"},
                          "yaml": "inclusion:\n  - \"dur < 100\"\nexclusion:\n  - \"cat IN {KERNEL_DISPATCH,MEMORY_COPY,PAGE_MIGRATION,"
                                  "SCRATCH_MEMORY,collective,comm,p2p,CPP_APP}\"",
                          "dsl": "fields cat,name,ts,dur,app,rank; ops == != >= <= > <, IN {a,b} (spaces around IN), LIKE, AND/OR/NOT; "
                                 "aggregated when inclusion matches and exclusion does not; cat==dftracer never aggregated; "
                                 "dur in microseconds; fold count field is dft_cnt"},
        "8_dimensions": "inputs (ALL) x node scales (bounded by queue node limit) x ppn (CPU: powers of 2 to cores; GPU: powers of 2 to "
                        "GPUs/GCDs per node) x PAPI sets; per-rank resources constant across ppn",
        "9_layout": "<session>/genesis/<system>/traces/<system>/<case>/nodes_<N>/ppn_<P>/{raw/papi_<set>/, raw/validation_<set>.json, "
                    "compacted/, compacted_check.json}; README.md",
        "10_run_flux": ["flux submit the service detached, pinned: -N<n> -n<n> -c1 --requires=host:<csv> --setattr=exclusive=false; poll pid files",
                        "flux run the app on the same hosts with genesis/<system>/build/<exe>, cwd inside genesis/<system>/dataset/",
                        "flux submit the service stop on the same hosts, let it flush"],
        "10_run_slurm": ["srun -N$N -n$N -c1 --nodelist=\"$SLICE\" --overlap bash -c '\"$SVC\" start \"$DIR\"; while [ ! -f \"$FLAG\" ]; "
                         "do sleep 1; done; \"$SVC\" stop \"$DIR\"; for _i in $(seq 1 60); do [ -s \"$OUT\" ] && break; sleep 1; done' &",
                         "srun -N$N -n$((N*P)) --nodelist=\"$SLICE\" --overlap --gres=gpu:4 -c$C --kill-on-bad-exit=1 \"$BINARY\" ...",
                         "touch \"$FLAG\"; wait \"$SVC_PID\""],
        "10_chain_flux": "flux batch -q \"$Q\" -N\"$N\" -t \"$T\" --bank=<bank> --job-name=genesis-$grp "
                         "--output=\"$G/artifacts/batch_${grp}_{{id}}.log\" --dependency=afterany:$prev \"$G/worker_$grp.sh\"",
        "10_chain_slurm": "genesis_slurm_chain.sh <part> <nodes> <min> <depth> <name>",
        "10a_checkpoint": ["<case>_N<nodes>_ppn<ppn>_<papiset> ok dt=<seconds>", "<case>_N<nodes>_ppn<ppn>_<papiset> SKIPPED <reason>",
                           "grep -v SKIPPED \"$STATE\" | awk '{print $1}' | sort -u | wc -l  # progress",
                           "exec 9>\"${STATE}.lock\"; flock -n 9 || exit 0  # one worker per state file"],
        "11_validate": ["app trace count == nodes*ppn, PR ranks == {0..n-1}", "SH cmdline matches the cell", "every trace has start and end",
                        "required categories + end.used", "PAPI landed == requested, multiplex == 0",
                        "one service trace per distinct host with sys/io/net + power", "grep the app completion marker before validating"],
        "12_publish": ["write raw/run_<set>.json after every run", "leaf seals -> move raw/ to archive (dcp) -> verify bytes+count -> "
                       "delete workspace raw/ -> compact in place in archive -> COMPACTION_NOT_RUN.md if not compacted -> chgperm",
                       "summary.json per leaf; genesis_validate_leaf.py <archive> --sets=N (workload_genesis_leaf_contract)"],
        "13_archive": ["module load mpifileutils", "flux run -N1 -n16 dcp <src> <archive>/dftracer-traces/<app>/<system>",
                       "S=$(find \"$SRC\" -type f -printf '%s\\n' | awk '{s+=$1} END{print s+0}'); same for $DST; compare",
                       "flux run -N1 -n16 dcmp \"$SRC\" \"$DST\"", "<archive>/chgperm.sh <archive>/dftracer-traces/<app>/<system>"],
    },
    "unique_inputs": {"amg": 16, "XSBench": 24, "miniFE.x": 49, "laghos": 186, "kripke.exe": 210, "miniVite": 288},
    "completion_markers": {"laghos": "Energy", "amg": "Figure of Merit", "kripke": "END", "miniFE": "Final Resid Norm",
                           "miniVite": "MODS", "XSBench": "Verification"},
    "script_env": {
        "GENESIS_SCHED": "flux|slurm (auto: Slurm if SLURM_JOB_ID or no live flux instance)",
        "GENESIS_INPUTS_FILE": "case<TAB>app args per line; GENESIS_ARGS_TEMPLATE with {case} for numeric apps",
        "GENESIS_GPU": "hip|cuda|none", "GENESIS_POWER": "variorum|nvml|none",
        "GENESIS_REQ_CATS/GENESIS_REQ_USED/GENESIS_NOFOLD_CATS": "validator required categories, end.used layers, aggregation-protected categories",
        "GENESIS_APP_MARKER/GENESIS_OK_RCS": "completion marker; exit codes accepted only with it",
        "GENESIS_COPY=cp, GENESIS_LEAF, GENESIS_CHGPERM, GENESIS_COMPACT_TMPDIR": "login-node publish without dcp; one leaf; archive perms; non-NFS split scratch",
        "GENESIS_KILL_ON_BAD_EXIT": "1 default; 0 for inputs that exit non-zero by design (XSBench XL/XXL)",
        "GENESIS_APP_TIMEOUT": "bounds a real hang", "GENESIS_AGG_FILE": "aggregation rules file (unset => aggregation vars unset)",
        "GENESIS_STATE": "the worker's own checkpoint file",
    },
    "scripts": ["genesis_run.sh", "genesis_driver.sh", "genesis_config.sh", "genesis_validate.py", "genesis_compact.sh",
                "genesis_check_compacted.py", "genesis_leaf_summary.py", "genesis_publish.sh", "genesis_finalize.sh",
                "genesis_readme.py", "genesis_audit.py", "genesis_slurm_chain.sh"],
    "variants": {},
    "notes": ["full step-by-step reference: docs/REFERENCE.md (verbatim); scripts: docs/scripts/; earlier skill text: docs/SKILL.previous.md",
              "project bank: gwisdom (verify membership with flux account view-user; probe with one 1-node 5-min job)"],
}

RULES = [
    {"id": "agg_type_uppercase", "forbid": r"DFTRACER_AGGREGATION_TYPE=[\"']?(?!SELECTIVE\b)[A-Za-z]*[a-z][A-Za-z]*\b|DFTRACER_AGGREGATION_TYPE=[\"']?selective",
     "why": "DFTRACER_AGGREGATION_TYPE is compared case-sensitively against SELECTIVE; anything else (incl. 'selective') silently falls back to FULL",
     "fix": "export DFTRACER_AGGREGATION_TYPE=SELECTIVE"},
    {"id": "agg_enabled", "require": r"DFTRACER_ENABLE_AGGREGATION=1", "when": r"DFTRACER_AGGREGATION_(TYPE|FILE)=",
     "why": "documenting aggregation is not enabling it: without DFTRACER_ENABLE_AGGREGATION=1 the corpus is unaggregated",
     "fix": "export DFTRACER_ENABLE_AGGREGATION=1 (and confirm folding in the smoke trace)"},
    {"id": "in_needs_spaces", "forbid": r"cat\s*IN\{|cat\s+IN\{|\bIN\{",
     "why": "the parser does trimmed.find(\" IN \"): IN needs spaces around it, else the rule mis-parses and everything is folded",
     "fix": "write cat IN {A,B}"},
    {"id": "service_not_flux_run", "forbid": r"\bflux\s+run\b[^\n]*dftracer_service[^\n]*\bstart\b",
     "why": "dftracer_service start under flux run never returns",
     "fix": "flux submit the service detached, pinned with --requires=host:<csv> --setattr=exclusive=false, then poll pid files"},
    {"id": "slurm_overlap", "require": r"--overlap", "when": r"\bsrun\b[^\n]*(dftracer_service|\$SVC|\$\{SVC\})",
     "why": "without --overlap the second step on shared nodes waits forever; the service trace comes back 0 bytes",
     "fix": "add --overlap (and --nodelist=<slice>) to the service step and the app step"},
    {"id": "flux_output_template", "forbid": r"\bflux\s+(batch|submit)\b[^\n]*--output=[^\s]*%j",
     "why": "%j is Slurm syntax; flux uses mustache {{id}}, so every job overwrites one log file",
     "fix": "use --output=<dir>/batch_<grp>_{{id}}.log"},
    {"id": "flux_batch_bank", "require": r"--bank=", "when": r"\bflux\s+batch\b",
     "why": "a genesis sweep must be charged to the project bank (gwisdom), not the default bank whose fair-share is discounted",
     "fix": "add --bank=<bank> after verifying membership (flux account view-user $USER) with one 1-node probe job"},
    {"id": "no_pkill_pattern", "forbid": r"\bpkill\s+-f\b",
     "why": "pkill -f <pattern> also matches your own monitoring shells / the shell running it",
     "fix": "collect PIDs first (ps -eo pid,lstart,args | grep genesis_[d]river), then kill by PID"},
    {"id": "no_cron", "forbid": r"\bcrontab\b",
     "why": "on multi-login-node sites crontab is node-local and crond may not run there",
     "fix": "use a flux batch / sbatch dependency chain (afterany)"},
    {"id": "count_keys_not_lines", "forbid": r"sort\s+-u\s+\"?\$\{?STATE\}?\"?\s*\|\s*wc\s+-l",
     "why": "retries append lines with different dt=, so sort -u over whole lines over-reports progress",
     "fix": "grep -v SKIPPED \"$STATE\" | awk '{print $1}' | sort -u | wc -l"},
    {"id": "utils_not_develop", "forbid": r"dftracer-utils(\.git)?@develop",
     "why": "dftracer-utils develop HEAD fails to compile (ConfigTree::Node incomplete type)",
     "fix": "install the newest tag (e.g. @v0.0.12), not PyPI"},
    {"id": "pip_no_deps", "require": r"--no-deps", "when": r"pip\s+install[^\n]*git\+[^\n]*dftracer",
     "why": "compute/login nodes often have no external DNS; pip cannot reach PyPI", "fix": "pip install --no-cache-dir --no-deps ... for each of the three packages"},
    {"id": "variorum_always", "forbid": r"DFTRACER_BUILD_VARIORUM=AUTO",
     "why": "AUTO can pick a system RPM that returns _ERROR_VARIORUM_UNSUPPORTED_PLATFORM and yields zero power events",
     "fix": "DFTRACER_BUILD_VARIORUM=ALWAYS and verify a gpu/power event lands (or DFTRACER_DISABLE_VARIORUM_POWER=1 where power is unreadable)"},
    {"id": "no_hip_env_ab", "forbid": r"DFTRACER_ENABLE_HIP_TRACING=0",
     "why": "rocprofiler registers at load time via rocprofiler_configure; the env var is inert, so an A/B with it 'proves' nothing",
     "fix": "rebuild dftracer with the feature OFF to exclude GPU tracing"},
    {"id": "exit_timeout_none", "require": r"exit-timeout=none", "when": r"\bflux\s+run\b[^\n]*genesis_compact",
     "why": "flux kills every task 30 s after the first exits; uneven compaction chunks then take the whole job down",
     "fix": "add -o exit-timeout=none to the flux run"},
    {"id": "grep_a_verification", "forbid": r"\bgrep\s+(?!(?:[^\n|]*\s)?-[A-Za-z]*a)[^\n|]*Verification: PASSED",
     "why": "split logs can contain a non-UTF8 byte; plain grep treats them as binary and reports no match",
     "fix": "grep -a 'Verification: PASSED'"},
    {"id": "split_not_raw", "forbid": r"\bdftracer_split\b[^\n]*\braw/?(\s|$|\")",
     "why": "dftracer_split does not recurse; traces live in raw/papi_*/, so pointing it at raw/ finds nothing and exits 1",
     "fix": "stage a flat directory of hardlinks inside the leaf (splice the set name into service_<host>.pfw.gz) and split that"},
    {"id": "no_du_verify", "forbid": r"\bdu\s+-[a-zA-Z]*s",
     "why": "PFS -> NFS is cross-filesystem: du differs on directory inodes and gives phantom mismatches",
     "fix": "compare regular-file bytes and counts with find -type f -printf '%s\\n', plus dcmp, while the source exists"},
    {"id": "no_hand_perms", "forbid": r"\b(chmod|chgrp)\b[^\n]*dftracer-traces",
     "why": "the archive (group genesis-wisdom, setgid dirs) has its own chgperm.sh", "fix": "run <archive>/chgperm.sh <archive>/dftracer-traces/<app>/<system>"},
    {"id": "no_rsync_archive", "forbid": r"\brsync\b[^\n]*dftracer-traces",
     "why": "hundreds of GB / hundreds of thousands of files: serial rsync/cp takes hours", "fix": "flux run -N1 -n16 dcp <src> <dst> (module load mpifileutils)"},
    {"id": "no_squeue_only_deadline", "forbid": r"DEADLINE=0[^\n]*$",
     "why": "a deadline of 0 meaning 'forever' when squeue returns empty dispatched a cell into the wall and killed the successor chain (a week idle)",
     "fix": "fall back to scontrol show job EndTime, then to now + requested walltime; RESERVE > longest single cell"},
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




# ---------------------------------------------------------------- matrix arithmetic (STEP 8, STEP 10, STEP 10a)
def _ints(v):
    if isinstance(v, str):
        v = [x for x in re.split(r"[,\s]+", v.strip()) if x]
    return [int(x) for x in (v or [])]


def _matrix(n_inputs, node_scales, ppns, papi_sets, cores_per_node=0, minutes_per_run=0.0, skipped=0):
    try:
        ni = int(n_inputs)
        ns, ps = _ints(node_scales), _ints(ppns)
        sets = [s.strip() for s in (papi_sets.split(",") if isinstance(papi_sets, str) else papi_sets or []) if str(s).strip()]
        cpn, skip = int(cores_per_node or 0), int(skipped or 0)
        mpr = float(minutes_per_run or 0)
    except (TypeError, ValueError) as e:
        return {"status": "error", "error": f"bad input: {e}"}
    if ni < 1 or not ns or not ps or not sets:
        return {"status": "error", "error": "need n_inputs >= 1 and non-empty node_scales, ppns, papi_sets"}
    bad_ppn = [p for p in ps if p & (p - 1)]
    total = ni * len(ns) * len(ps) * len(sets)
    node_runs = ni * len(ps) * len(sets) * sum(ns)
    out = {"status": "ok", "total_runs": total, "reachable_runs": total - skip, "leaves": ni * len(ns) * len(ps),
           "node_runs": node_runs,
           "formula": "inputs x node_scales x ppns x papi_sets (PAPI sets are runs, not a dimension: they collapse into one leaf)",
           "run_key": "<case>_N<nodes>_ppn<ppn>_<papiset>",
           "example_keys": [f"<case>_N{n}_ppn{p}_{sets[0]}" for n in ns[:2] for p in ps[:2]],
           "warnings": []}
    if mpr > 0:
        out["node_hours"] = round(node_runs * mpr / 60.0, 1)
    if bad_ppn:
        out["warnings"].append(f"ppn values not powers of two: {bad_ppn}")
    if cpn > 0:
        cpr = (cpn - 1) // max(ps)
        out["cores_per_rank"] = cpr
        out["cores_rule"] = "floor((cores_per_node - 1) / max_ppn), constant across the ppn ladder (the service daemon holds one core per node)"
        if cpr < 1:
            out["warnings"].append("max ppn leaves < 1 core per rank once the service core is reserved")
    return out


def register(mcp):
    @mcp.tool()
    def workload_genesis_run_recipe(variant: str = "") -> dict:
        """Predictor: the genesis sweep procedure as JSON: the three user gates, PLAN.md contents, per-step commands (inputs from
        merged.txt, session qualification, Flux/Slurm system discovery, dftracer install, self-contained system folder, PAPI
        partition probing, SELECTIVE aggregation, dimensions, layout, Flux/Slurm run triple, checkpoint, validation, publish,
        archive), unique-input counts, completion markers and the scripts' GENESIS_* variables. Use before planning or resuming a
        genesis sweep. variant: unused (none defined). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_genesis_run_matrix(n_inputs: int, node_scales: str, ppns: str, papi_sets: str, cores_per_node: int = 0,
                                    minutes_per_run: float = 0.0, skipped: int = 0) -> dict:
        """Predictor: the GATE 3 arithmetic for a genesis sweep: total runs = inputs x node_scales x ppns x papi_sets, reachable runs
        (minus SKIPPED impossible cells), leaves, node-runs and node-hours, per-rank cores floor((cores_per_node-1)/max_ppn) so the
        top ppn rung does not deadlock beside the service, and the checkpoint run-key format. n_inputs: count of unique merged.txt
        args; node_scales/ppns: comma lists of ints (e.g. "1,2,4,8"); papi_sets: comma list of set names; cores_per_node,
        minutes_per_run, skipped: optional. Returns {status, total_runs, reachable_runs, leaves, node_runs, node_hours?,
        cores_per_rank?, run_key, example_keys, warnings}."""
        return _matrix(n_inputs, node_scales, ppns, papi_sets, cores_per_node, minutes_per_run, skipped)

    @mcp.tool()
    def workload_genesis_run_check(commands: list) -> dict:
        """Validator: check a proposed genesis sweep command list / script lines against the skill's rules (SELECTIVE uppercase and
        aggregation enabled, ' IN ' spacing, service never under flux run, Slurm --overlap, flux {{id}} not %j, --bank on flux batch,
        no pkill -f, no cron, count distinct keys, dftracer-utils tag not develop, pip --no-deps, variorum ALWAYS, no HIP env A/B,
        exit-timeout=none for compaction, grep -a, dftracer_split not on raw/, no du verification, chgperm.sh, dcp not rsync, safe
        deadline). commands: list of shell lines (or one newline-separated string / JSON text). Returns {status:
        pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

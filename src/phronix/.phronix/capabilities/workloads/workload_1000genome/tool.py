"""workload_1000genome: the 1000genome-workflow (pegasus-isi/1000genome-workflow, Pegasus + PMC, pure-Python tasks) recipe that
dftracer-agents' workload-1000genome skill verified: task scripts, execution mode, run sizing, annotation scope and the
measured individuals.py optimization gates, as structured data (predictor), and a deterministic check of a proposed command
list against that skill's rules (validator). Nothing here runs."""
import json
import re

CAP = "workload_1000genome"

RECIPE = {
    "app": "1000genome-workflow",
    "repo": "pegasus-isi/1000genome-workflow",
    "what": "Pegasus workflow over 1000 Genomes VCF data: SNP frequency filtering, SIFT scoring, pairwise mutation overlap",
    "build_system": "none (pure-Python task scripts under bin/); Pegasus 5.0.7 + PMC from source per software_pegasus",
    "execution": "PMC only (Condor planning-only); ignore the README's HTCondor condorpool / Cori-Bosco / Decaf modes (no site Condor pool on Tuolumne)",
    "tasks": {
        "individuals.py": "dominant cost, 81.85% of baseline wall time: parse VCF by chromosome, filter SNPs by allele frequency, one output per individual, tar",
        "individuals_merge.py": "merges per-job tar.gz chunks for a chromosome (level-4 width-1 serialization barrier in the DAG)",
        "sifting.py": "reads VEP score files, writes scored SNP lists",
        "mutation_overlap.py": "untars chromosome data, reads population CSVs, pairwise SNP overlap, PNG heatmaps",
        "frequency.py": "random-sampling overlap-frequency analysis, matplotlib PNG (10.68% of baseline)",
        "individuals_mpi.py / individuals_merge_mpi.py": "MPI variants, not in the default PMC task set: leave unannotated unless needed",
        "daxgen.py": "workflow generator (DAX/YAML): never a traced task under PMC: exclude from annotation",
    },
    "sizing": {
        "readme_baseline": "single chromosome, 10 individuals-jobs ~3.9 h (individuals ~11,400 s / 81.85%, frequency 10.68%, rest ~5%)",
        "target": "~10-20 min: scope down with prepare_input.sh options and/or daxgen.py -i <num_individuals_jobs> (fewer jobs / fewer VCF rows)",
    },
    "annotate": {
        "tool": "python_annotate_project / python_annotate_file (FUNCTION mode) on the 5 target scripts",
        "targets": ["individuals.py", "individuals_merge.py", "sifting.py", "mutation_overlap.py", "frequency.py"],
        "exclude": ["daxgen.py", "individuals_mpi.py", "individuals_merge_mpi.py"],
        "module_level_io": "mutation_overlap.py and frequency.py run a top-level tarfile.open()/extractall()/close(): wrap by hand with "
                           "`with DFTracerFn(...):` (dftracer-annotation-lessons PP9)",
        "priority": "individuals.py VCF read loop and the per-individual write + tar-compress path",
        "expected_report": "5/5 files, 38/38 functions, 100% coverage",
    },
    "optimization": {
        "IND_ROW_PRECOMPUTE=1": "hoist row-invariant VCF parse into precompute_rows() + 1-byte/individual allele string: -93.4% standalone (90.65 s -> 6.00 s median, n=5)",
        "IND_TAR_STREAM=1": "in-memory tarfile.addfile(TarInfo, BytesIO), no 2504 scratch create/stat/read/unlink per task; with the above -99.5% (193x) standalone (90.65 s -> 0.47 s)",
        "unconditional": "remove dead write-only accumulator chrp_data: -25.8% peak RSS, wall-neutral, byte-identical",
        "rejected": "gc.disable()+gc.freeze(): +1.7% regression (acyclic object graph)",
        "gates_off": "baseline path bit-for-bit unchanged (+0.3% noise)",
        "workflow_result": "4-node PMC DAG 316.5 s -> 244.7 s (1.29x, 29.3%, 71.8 s saved), 46/46 tasks: capped by the merge barrier and untouched levels 5-7",
        "verify": "extract output tars member by member, per-member md5 vs pristine (2504/2504 identical) + diff -rq over the 2504 per-individual files",
    },
    "known_upstream_bug": "mutation_overlap.py pair_individuals includes self-intersections: reported, NOT fixed (changes results, breaks baseline comparison)",
}

RULES = [
    {"id": "no_condor_pool", "forbid": r"--sites?\s+condorpool|condorpool|bosco|decaf",
     "why": "this project runs Pegasus workflows through PMC only (no site-wide Condor pool on Tuolumne)",
     "fix": "plan with Condor planning-only and execute with pegasus-mpi-cluster (software_pegasus)"},
    {"id": "no_annotate_daxgen", "forbid": r"python_annotate_\w+\(.*daxgen\.py|annotate.*\bdaxgen\.py",
     "why": "daxgen.py is the workflow generator and never runs as a traced task under PMC", "fix": "exclude daxgen.py from annotation"},
    {"id": "no_fix_pair_individuals", "forbid": r"pair_individuals",
     "why": "the self-intersection in mutation_overlap.py pair_individuals is a known upstream bug left unfixed: fixing it changes "
            "numerical output and breaks the baseline/optimized comparison", "fix": "do not touch pair_individuals; report it only"},
    {"id": "no_gc_freeze", "forbid": r"gc\.disable\(\)|gc\.freeze\(\)",
     "why": "gc.disable()+gc.freeze() measured a +1.7% regression on individuals.py", "fix": "drop it"},
    {"id": "sized_run", "require": r"daxgen\.py\b.*\s-i\s*\d+|prepare_input\.sh\b", "when": r"daxgen\.py|pegasus-plan",
     "why": "the README baseline is ~3.9 h; a bounded smoke/baseline must target ~10-20 min",
     "fix": "scope down with daxgen.py -i <num_individuals_jobs> and/or prepare_input.sh options"},
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
    def workload_1000genome_recipe(variant: str = "") -> dict:
        """Predictor: the 1000genome-workflow recipe dftracer-agents verified: task scripts and their cost share, PMC-only
        execution, run sizing (~3.9 h README baseline -> 10-20 min), annotation targets/exclusions and the module-level tar I/O
        fixup, the measured individuals.py optimization gates (IND_ROW_PRECOMPUTE, IND_TAR_STREAM) and the known upstream bug.
        variant: optional (none defined; any value returns an unknown-variant error). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_1000genome_check(commands: list) -> dict:
        """Validator: check a proposed 1000genome command list against the skill's rules (PMC not condorpool, daxgen.py not
        annotated, pair_individuals not touched, no gc.disable/freeze, sized run via daxgen.py -i / prepare_input.sh).
        commands: list of shell/tool-call lines (or a newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

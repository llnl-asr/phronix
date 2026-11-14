"""workload_genesis_leaf_contract: the published-leaf contract of a genesis trace corpus (which artifacts every leaf in the
shared archive must carry, and why) as structured data (predictor), a deterministic check of a proposed publish command
list against the contract's rules, and a port of genesis_validate_leaf.py that checks published leaf directories on disk
(validators). Nothing here moves, compacts or deletes data."""
import glob
import json
import os
import re

CAP = "workload_genesis_leaf_contract"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "genesis corpus (any ice4hpc app swept by workload_genesis_run)",
    "what": "the published-leaf contract: every <archive>/<case>/nodes_<N>/ppn_<P>/ leaf must satisfy all clauses",
    "leaf_glob": "<archive>/*/nodes_*/ppn_*",
    "contract": {
        "DATA": {"requirement": "at least one copy of the traces: compacted chunks (*.pfw.gz at the leaf top level or in compacted/) "
                                "or raw/papi_*/**.pfw.gz",
                 "why": "a leaf with neither chunks nor raw/ is an empty directory impersonating data; happens when a publish is "
                        "interrupted between mkdir and the copy"},
        "NOTE": {"requirement": "no chunks => COMPACTION_NOT_RUN.md must exist; chunks => it must not",
                 "why": "a missing note on an uncompacted leaf leaves a reader no way to know raw/ is authoritative; a stale note on a "
                        "compacted leaf makes a finished leaf look unfinished, which is how work gets needlessly redone"},
        "SUMMARY": {"requirement": "summary.json present, parseable, its `leaf` ending in this cell's own <case>/nodes_<N>/ppn_<P>, "
                                   "and ranks == nodes*ppn",
                    "why": "catches a summary.json copied from another cell, or generated against the wrong (nodes, ppn)"},
        "RUN JSON": {"requirement": "one run_<set>.json per validated PAPI set",
                     "why": "one leaf is N runs (one per PAPI set); summary.json aggregates them and cannot say which run multiplexed or "
                            "which lost a rank: without the per-run record a defect is detectable but not locatable"},
        "VALIDATION": {"requirement": "one validation_<set>.json per set",
                       "why": "the capture-time content check travels with the data"},
        "EXACTNESS": {"requirement": "every run record reports multiplex of exactly 0",
                      "why": "multiplex != 0 means PAPI time-shared the counters and the values are scaled estimates, not measurements; "
                             "dftracer reports it in the trace but nothing refuses it"},
        "COMPLETE": {"requirement": "every run record reports app_files == ranks",
                     "why": "app_files < ranks is a missing rank; no later processing can reconstruct it, so it must fail at publish "
                            "time while a rerun is still cheap"},
    },
    "artifact_locations": [
        "run_<set>.json and validation_<set>.json live inside raw/ so they travel with the traces; when raw/ has been reclaimed "
        "after compaction they sit at the leaf top level: a checker must look in both",
        "compacted chunks in this archive are at the leaf top level (app-<n>_chunk0.pfw.gz), not in compacted/: checking only "
        "compacted/ wrongly stamps COMPACTION_NOT_RUN.md onto compacted leaves (measured, on a real publish)",
    ],
    "summary_json_keys": ["leaf", "ok", "app", "system", "input", "nodes", "ppn", "ranks", "sets[]", "n_sets", "n_app_traces",
                          "n_service_traces", "hosts[]", "app_categories{cat: count}", "service_categories{cat: count}", "papi[]",
                          "papi_multiplex[]", "gpu_power_csv", "gpu_power_rows", "compacted{chunk_filename: bytes}"],
    "checker": {
        "command": "genesis_validate_leaf.py <archive_root> [--sets=N] [--json]",
        "exit": "0 only when every leaf passes; one `FAIL <leaf>: <reasons>` line per violation",
        "sets": "--sets=N also asserts each leaf carries N run records (this machine's PAPI partition size): catches a leaf that sealed early",
        "when": "before declaring a corpus complete, and after any publish round",
        "measured": "amg/tuolumne corpus, --sets=9: 343/343 leaves satisfy the published-leaf contract",
        "source": "docs/scripts/genesis_validate_leaf.py (verbatim); workload_genesis_leaf_contract_leaf_check is its in-process port",
    },
    "negative_controls": [
        {"control": "verbatim good leaf", "expected": "pass", "result": "1/1 satisfy"},
        {"control": "summary.json deleted", "expected": "fail", "result": "missing summary.json"},
        {"control": "chunks and raw/ deleted", "expected": "fail", "result": "no data: neither compacted chunks nor raw/ traces"},
        {"control": "note added beside chunks", "expected": "fail", "result": "compacted but stale COMPACTION_NOT_RUN.md present"},
        {"control": "run record set to multiplex={1:5}, app_files=1", "expected": "fail",
         "result": "PAPI multiplexed (estimates); app_files 1 != ranks 2"},
    ],
    "variants": {},
    "notes": [
        "prose alone already failed: leaves were published with a stale COMPACTION_NOT_RUN.md, with 2 of 9 validation_*.json, and with "
        "summary.json reporting hosts: []; every one passed a human read-through",
        "summary.json is the established per-leaf file (laghos/* publishes it; its key names are what consumers read); run_<set>.json is "
        "an addition, not a replacement; check a neighbouring app's published leaves before adding any new file to a corpus",
        "re-run the negative controls whenever a clause is added or the checker is edited",
    ],
}

RULES = [
    {"id": "validate_before_complete", "require": r"genesis_validate_leaf(\.py)?\b|workload_genesis_leaf_contract_leaf_check",
     "when": r"genesis_finalize|genesis_readme|README\.md|rm\s+(-\w+\s+)*\S*STATUS\.md",
     "why": "a corpus is declared complete (README written / STATUS.md removed / finalize) without running the leaf-contract checker; "
            "hand review has already passed stale notes and 2-of-9 validation files",
     "fix": "run genesis_validate_leaf.py <archive_root> --sets=<N> (or workload_genesis_leaf_contract_leaf_check) first and stop on any FAIL"},
    {"id": "sets_asserted", "require": r"genesis_validate_leaf(\.py)?\b[^\n]*--sets[= ]\d+", "when": r"genesis_validate_leaf",
     "why": "without --sets=N a leaf that sealed early (fewer run records than the PAPI partition) passes",
     "fix": "add --sets=<number of PAPI sets on this machine> (wc -l of papi_sets.txt without comments)"},
    {"id": "no_compacted_only_note", "forbid": r"(-d\s+\S*compacted/?\s*\]|ls\s+\S*compacted/?\b).*COMPACTION_NOT_RUN",
     "why": "chunks sit at the leaf top level, not in compacted/: deciding the note from compacted/ alone stamps it on compacted leaves",
     "fix": "decide from *.pfw.gz at the leaf top level OR compacted/*.pfw.gz (as the checker does)"},
    {"id": "no_hand_perms", "forbid": r"\b(chmod|chgrp)\b[^\n]*dftracer-traces",
     "why": "the archive's permissions come from its own chgperm.sh (group rw/rws, setgid, chgrp to the archive group)",
     "fix": "run <archive_root>/chgperm.sh <archive>/<app>/<system> instead"},
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




# ---------------------------------------------------------------- the leaf checker (port of docs/scripts/genesis_validate_leaf.py)
def _leaf_errors(leaf, want_sets=None):
    errs = []
    case = os.path.basename(os.path.dirname(os.path.dirname(leaf)))
    nodes = int(os.path.basename(os.path.dirname(leaf))[len("nodes_"):])
    ppn = int(os.path.basename(leaf)[len("ppn_"):])
    ranks = nodes * ppn
    raw = os.path.join(leaf, "raw")
    chunks = glob.glob(os.path.join(leaf, "*.pfw.gz")) + glob.glob(os.path.join(leaf, "compacted", "*.pfw.gz"))
    raw_traces = glob.glob(os.path.join(raw, "papi_*", "*.pfw.gz"))
    note = os.path.join(leaf, "COMPACTION_NOT_RUN.md")
    if not chunks and not raw_traces:
        errs.append("no data: neither compacted chunks nor raw/ traces")
    if not chunks and not os.path.exists(note):
        errs.append("uncompacted but no COMPACTION_NOT_RUN.md")
    if chunks and os.path.exists(note):
        errs.append("compacted but stale COMPACTION_NOT_RUN.md present")
    sp = os.path.join(leaf, "summary.json")
    summ = None
    if not os.path.exists(sp):
        errs.append("missing summary.json")
    else:
        try:
            with open(sp) as fh:
                summ = json.load(fh)
        except Exception as e:  # noqa: BLE001
            errs.append(f"summary.json unparseable ({e})")
    if summ is not None:
        if not str(summ.get("leaf", "")).endswith(f"{case}/nodes_{nodes}/ppn_{ppn}"):
            errs.append(f"summary.leaf mismatch: {summ.get('leaf')!r}")
        if summ.get("ranks") != ranks:
            errs.append(f"summary.ranks {summ.get('ranks')} != nodes*ppn {ranks}")
    src = raw if os.path.isdir(raw) else leaf
    runs = sorted(set(glob.glob(os.path.join(src, "run_*.json")) + glob.glob(os.path.join(leaf, "run_*.json"))))
    vals = sorted(set(glob.glob(os.path.join(src, "validation_*.json")) + glob.glob(os.path.join(leaf, "validation_*.json"))))
    if not runs:
        errs.append("no run_<set>.json")
    if not vals:
        errs.append("no validation_<set>.json")
    if want_sets and len(runs) and len(runs) < want_sets:
        errs.append(f"only {len(runs)} run_*.json, expected {want_sets}")
    for rp in runs:
        try:
            with open(rp) as fh:
                r = json.load(fh)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{os.path.basename(rp)} unparseable ({e})")
            continue
        if r.get("status") == "SKIPPED":
            continue
        mux = r.get("multiplex") or {}
        if [k for k in mux if str(k) != "0"]:
            errs.append(f"{r.get('papi_set')}: PAPI multiplexed (estimates) {mux}")
        af = r.get("app_files")
        if af is not None and af != ranks:
            errs.append(f"{r.get('papi_set')}: app_files {af} != ranks {ranks}")
    return errs


_FIX = {"no data": "republish the leaf (the copy was interrupted): rerun genesis_publish.sh for it",
        "uncompacted but no": "write COMPACTION_NOT_RUN.md with the reason and say raw/ is authoritative",
        "stale COMPACTION_NOT_RUN": "delete the stale note (the leaf is compacted)",
        "summary": "regenerate summary.json for THIS cell (genesis_leaf_summary.py)",
        "run_<set>": "write/backfill run_<set>.json (reconstruct from state_*, artifacts/<key>.log, validation_<set>.json; backfilled: true)",
        "validation_<set>": "copy validation_<set>.json with the raw traces (raw/ or leaf top level)",
        "only ": "the leaf sealed early: unseal it and run the missing PAPI sets",
        "multiplexed": "rerun that PAPI set with a smaller, probe-verified set (workload_genesis_run STEP 6)",
        "app_files": "a rank is missing: rerun that set for the cell",
        "unparseable": "rewrite the file from its sources"}


def _leaf_check(archive_root, sets=0):
    root = str(archive_root or "")
    if not root or not os.path.isdir(root):
        return {"status": "inconclusive", "leaves": 0, "checks": [{"check": "input", "ok": False,
                "detail": f"archive_root {root!r} is not a directory", "fix": "pass <archive>/<app>/<system>"}]}
    leaves = [d for d in sorted(glob.glob(os.path.join(root, "*", "nodes_*", "ppn_*"))) if os.path.isdir(d)]
    if not leaves:
        return {"status": "inconclusive", "leaves": 0, "checks": [{"check": "input", "ok": False,
                "detail": "no leaf matches <case>/nodes_<N>/ppn_<P> under archive_root", "fix": "point at the <app>/<system> level"}]}
    want = int(sets) if str(sets).strip().isdigit() and int(sets) > 0 else None
    out = []
    for leaf in leaves:
        try:
            errs = _leaf_errors(leaf, want)
        except ValueError as e:
            errs = [f"leaf path not <case>/nodes_<int>/ppn_<int>: {e}"]
        rel = os.path.relpath(leaf, root)
        fixes = sorted({f for e in errs for k, f in _FIX.items() if k in e})
        out.append({"check": rel, "ok": not errs, "detail": "; ".join(errs) or "ok", "fix": " | ".join(fixes)})
    bad = sum(1 for c in out if not c["ok"])
    return {"status": "pass" if bad == 0 else "fail", "leaves": len(out), "failing": bad,
            "summary": f"{len(out) - bad}/{len(out)} leaves satisfy the published-leaf contract", "checks": out}


def register(mcp):
    @mcp.tool()
    def workload_genesis_leaf_contract_recipe(variant: str = "") -> dict:
        """Predictor: the genesis published-leaf contract as JSON: the seven clauses (DATA, NOTE, SUMMARY, RUN JSON, VALIDATION,
        EXACTNESS, COMPLETE) with why each exists, where run/validation records live, the summary.json keys, the checker command
        and its negative controls. Use before publishing a leaf or declaring a corpus complete. variant: unused (none defined).
        Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_genesis_leaf_contract_check(commands: list) -> dict:
        """Validator: check a proposed publish/finalize command list against the contract's rules (leaf checker run with --sets=N
        before a README/finalize/STATUS.md removal, note not decided from compacted/ alone, no hand chmod/chgrp in the archive).
        commands: list of shell lines (or one newline-separated string / JSON text). Returns {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

    @mcp.tool()
    def workload_genesis_leaf_contract_leaf_check(archive_root: str, sets: int = 0) -> dict:
        """Validator: check every published leaf <archive_root>/<case>/nodes_<N>/ppn_<P>/ on disk against the contract (in-process
        port of genesis_validate_leaf.py; reads only file names and the small JSON records, never trace contents). archive_root:
        the <app>/<system> directory of the archive; sets: expected PAPI sets per leaf (0 = do not assert). Returns {status:
        pass|fail|inconclusive, leaves, failing, summary, checks: [{check: leaf, ok, detail, fix}]}."""
        return _leaf_check(archive_root, sets)

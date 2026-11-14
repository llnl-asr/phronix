"""workload_h5bench: the h5bench (HDF5 I/O benchmark suite, CMake, C; fork hariharan-devarajan/h5bench) build/annotate/run recipe
that dftracer-agents' workload-h5bench skill verified on Tuolumne (binary names, -DH5BENCH_ALL=ON, chid_t HDF5 patch,
-ldftracer_core link fixes, INI configs, write-then-read, sizing, ROMIO/Lustre optimization history), as structured data
(predictor), and a deterministic check of a proposed recipe or command list against that skill's rules (validator)."""
import json
import re

CAP = "workload_h5bench"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "h5bench",
    "repo": "https://github.com/hariharan-devarajan/h5bench",
    "build_system": "cmake",
    "languages": ["C"],
    "systems": ["tuolumne"],
    "binaries": {"write": "h5bench_write", "read": "h5bench_read", "append": "h5bench_append", "overwrite": "h5bench_overwrite",
                 "write_unlimited": "h5bench_write_unlimited", "hdf5_iotest": "h5bench_hdf5_iotest", "exerciser": "h5bench_exerciser"},
    "not_in_this_fork": ["write_normal_dist", "h5bench_write_var_normal_dist"],
    "dependencies": {
        "hdf5": [
            "curl -fkL https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.3/src/hdf5-1.14.3.tar.gz -o hdf5-1.14.3.tar.gz   # GitHub 404s here",
            "tar xf hdf5-1.14.3.tar.gz && cd hdf5-1.14.3",
            "CC=mpicc ./configure --prefix=<ws>/hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production --with-zlib=/usr",
            "make -j8 && make install",
            "sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' <ws>/hdf5_1.14/include/H5Apublic.h   # still needed in 1.14.5 (line 926)",
            "point session.json at <ws>/hdf5_1.14 and re-run session_install_dftracer",
        ],
    },
    "configure": ["cmake -S source -B build -DH5BENCH_ALL=ON   # else exerciser/hdf5_iotest silently not built (5 of 7 binaries)"],
    "build": ["cmake --build build -j", "ls <WS>/build_ann/h5bench_*   # all 7 binaries present"],
    "annotated_link_fix": [
        "sed -i 's/-ldftracer\\b/-ldftracer_core/g' build_ann/CMakeCache.txt",
        "find build_ann/CMakeFiles -name link.txt -exec sed -i 's/-ldftracer\\b/-ldftracer_core/g' {} +",
        "grep -r 'ldftracer[^_]' build_ann/   # must return nothing",
        "-ldftracer_core AFTER all .o files, at the END of the same link.txt line (a line of its own is ignored)",
        "after editing CMakeCache.txt add MPI_C_WORKS:BOOL=TRUE and MPI_CXX_WORKS:BOOL=TRUE",
    ],
    "env": {
        "LD_LIBRARY_PATH": "/opt/cray/pe/cce/20.0.0/cce/x86_64/lib:/opt/cray/pe/cce/20.0.0/cce-clang/x86_64/lib:... (source setup_dftracer_env.sh before every run, not only the build)",
        "DFTRACER_ENABLE": "1", "DFTRACER_INIT": "FUNCTION", "DFTRACER_DATA_DIR": "all", "DFTRACER_LOG_FILE": "<trace prefix>",
    },
    "annotate": [
        "DFTRACER_C_INIT(NULL, NULL, NULL) (third arg -1 segfaults in initialize_main)",
        "DFTRACER_C_METADATA(dft_meta_app, \"app\", \"h5bench_write\") (3-arg, first a unique bare identifier)",
        "clang_add_braces breaks assert() and else-if in h5bench_write.c (fixed in source_parser.py _collect_braceless); hdf5_iotest.c and h5bench_exerciser.c annotate cleanly",
        "clang_syntax_check extra_include_dirs: <venv dftracer include> and <WS>/hdf5_1.14/include",
    ],
    "config_ini_example": ["MEM_PATTERN=CONTIG", "FILE_PATTERN=CONTIG", "TIMESTEPS=3", "DELAYED_CLOSE_TIMESTEPS=0", "COLLECTIVE_DATA=NO",
                           "COLLECTIVE_METADATA=NO", "NUM_DIMS=1", "DIM_1=1048576", "DIM_2=1", "DIM_3=1"],
    "smoke": ["mpirun -np 2 ./h5bench_write /tmp/h5bench.cfg /tmp/test.h5   # INI config, never the samples/*.json"],
    "read_two_phase": [
        "DFTRACER_ENABLE=0 ./h5bench_write write_for_read.cfg read.h5   # CONTIG/CONTIG, same NUM_DIMS/DIM_1 as read.cfg",
        "DFTRACER_ENABLE=1 DFTRACER_LOG_FILE=<prefix> ./h5bench_read read.cfg read.h5",
    ],
    "sizing": [
        ">50% of node memory moved per node (Tuolumne ~502 GiB/node): 192 ranks x DIM_1=33554432 x 4 B x 4 timesteps = 768 GiB ok; 16M = 384 GiB not",
        "verify real output with du -sh <out>.h5 at 1 process, 1 node, 8 nodes; trace-log size is NOT a proxy; poll flux jobs -a until CD",
        "target ~500-700 GB/run at 768 ranks, 10-15 min",
    ],
    "variants": {
        "write_opt_768": {"env": {"MPICH_MPIIO_HINTS": "*:romio_cb_write=enable:cb_nodes=16", "CRAY_CB_NODES_MULTIPLIER": "2"},
                          "lustre": "lfs setstripe -c 16 -S 4M on a FRESH output dir", "config": "DIM_1=2097152, INTERLEAVED/INTERLEAVED, ~575 GB/rep",
                          "result": "median POSIX BW 325.94 -> 1924.71 MB/s (+490.5%), wall ~12.1 -> ~1.4 min (2026-07-10)"},
        "write_minimal_romio_192": {"env": {"MPICH_MPIIO_HINTS": "*:romio_cb_write=enable:romio_ds_write=disable"}, "lustre": "lfs setstripe -c 16 -S 4m",
                                    "result": "586 MB/s -> 1.652 GB/s (+182%) at 2 nodes x 192 ranks, DIM_1=16M, 4 timesteps (2026-06-25)"},
        "hdf5_iotest_768": {"ini": "steps=24 arrays=5 rows=512 columns=512 process-rows=32 process-columns=24 scaling=weak dataset-rank=4 layout=contiguous mpi-io=collective",
                            "result": "~395 GB/rep, ~7-10 min"},
        "exerciser_768": {"cmd": "h5bench_exerciser --numdims 2 --minels 5523 5523 --nsizes 1", "result": "~383 GB/rep, ~20-21 min (shrink --minels to ~1500-2000)"},
        "read_768": {"config": "MEM_PATTERN=CONTIG FILE_PATTERN=CONTIG READ_OPTION=STRIDED TIMESTEPS=4 COLLECTIVE_DATA=YES COLLECTIVE_METADATA=YES NUM_DIMS=1 DIM_1=33554432", "note": "size not re-verified"},
    },
    "notes": [
        "grep run logs for HDF5-DIAG and read error storms (H5Sget_simple_extent_dims 'not a dataspace'): exit 0 + printed summary can be fabricated",
        "always write to a fresh output dir: reused large files inflate __lxstat ~100x (43 ms vs 450 us)",
        "read/append/overwrite are metadata bound; collective metadata is already unconditional in their set_pl(); cb_nodes combo and striping are wrong-shape there",
        "write_unlimited captures only ~162/768 processes per rep: root-cause before optimizing",
        "do not trust a 5-rep median alone on shared Lustre: confirm with a same-rep comparator",
        "MPICH 9.0.1 is outside brahma's tested range: MPI-IO interception disabled, POSIX and app-level tracing work",
    ],
}

# rule kinds: forbid (regex must not match any command), require (regex must match some command; only when `when` matches, if given)
RULES = [
    {"id": "all_benchmarks", "require": r"-DH5BENCH_ALL=ON|-DH5BENCH_EXERCISER=ON.*-DH5BENCH_METADATA=ON|-DH5BENCH_METADATA=ON.*-DH5BENCH_EXERCISER=ON",
     "when": r"\bcmake\s+(?:-S|\S*source|\.\.)",
     "why": "exerciser and hdf5_iotest default OFF: a plain configure silently builds 5 of 7 binaries",
     "fix": "add -DH5BENCH_ALL=ON (or -DH5BENCH_EXERCISER=ON -DH5BENCH_METADATA=ON) and ls build/h5bench_*"},
    {"id": "no_normal_dist", "forbid": r"normal_dist",
     "why": "write_normal_dist / h5bench_write_var_normal_dist do not exist in hariharan-devarajan/h5bench @ master",
     "fix": "use one of write, write_unlimited, overwrite, append, read, hdf5_iotest, exerciser"},
    {"id": "link_dftracer_core", "forbid": r"-ldftracer(?![_\w])",
     "why": "dftracer installs libdftracer_core.so: '/usr/bin/ld: cannot find -ldftracer'",
     "fix": "sed -i 's/-ldftracer\\b/-ldftracer_core/g' in CMakeCache.txt and every link.txt; keep it after the .o files on the same line"},
    {"id": "init_null_args", "forbid": r"DFTRACER_C_INIT\([^)]*-1",
     "why": "the third arg -1 becomes (int*)0xffff... and segfaults in initialize_main", "fix": "DFTRACER_C_INIT(NULL, NULL, NULL)"},
    {"id": "metadata_three_args", "forbid": r"DFTRACER_C(?:PP)?_METADATA\(\s*\"[^\"]*\"\s*,\s*\"[^\"]*\"\s*\)",
     "why": "DFTRACER_C_METADATA(name, key, val) is 3-arg with a bare identifier name: the 2-arg form does not compile",
     "fix": "DFTRACER_C_METADATA(dft_meta_app, \"app\", \"h5bench_write\")"},
    {"id": "ini_not_json", "forbid": r"h5bench_\w+\s+\S+\.json\b",
     "why": "the binaries need INI key=value; a samples/*.json (for h5bench.py) segfaults in fgets()",
     "fix": "write an INI config (MEM_PATTERN=..., DIM_1=...)"},
    {"id": "read_after_write", "require": r"h5bench_write\b", "when": r"h5bench_read\b",
     "why": "h5bench_read needs a pre-existing file shaped per its config; otherwise HDF5 error storm, exit 0, bogus trace",
     "fix": "phase 1 DFTRACER_ENABLE=0 h5bench_write write_for_read.cfg read.h5, phase 2 traced h5bench_read"},
    {"id": "no_delayed_close", "forbid": r"DELAYED_CLOSE_TIMESTEPS\s*=\s*[1-9]",
     "why": "DELAYED_CLOSE_TIMESTEPS>0 with MPI collective writes segfaults (2 nodes x 192 ranks, 2026-06-24)",
     "fix": "DELAYED_CLOSE_TIMESTEPS=0; tune ROMIO cb / striping for close bursts"},
    {"id": "hints_not_via_env_flag", "forbid": r"--env[= ]\S*MPICH_MPIIO_HINTS|flux\s+proxy\s+\S+\s+flux\s+run\b.*--env",
     "why": "flux proxy ... flux run --env with ;/:/* drops the binary ('job command and arguments are missing')",
     "fix": "export MPICH_MPIIO_HINTS inside a wrapper script (software_mpi pattern)"},
    {"id": "hints_colon_separated", "forbid": r"MPICH_MPIIO_HINTS=[\"']?\*:[^\"'\s]*(?:;|,[a-z_]+=)",
     "why": "Cray MPICH 9.0.1 separates hints with colons; ';' or ',' makes the whole tail the value of the first key",
     "fix": "\"*:key1=val1:key2=val2\" (commas only between filename patterns)"},
    {"id": "no_romio_no_indep_rw", "forbid": r"romio_no_indep_rw",
     "why": "not a Cray MPICH 9.0.1 hint key (OpenMPI/OMPIO only): silently dropped", "fix": "drop it"},
    {"id": "no_striping_hints", "forbid": r"MPICH_MPIIO_HINTS=\S*striping_(?:factor|unit)",
     "why": "striping_factor/unit hints with lfs setstripe already set conflict at large sizes (segfault with cb_nodes=16, 2026-06-25)",
     "fix": "let lfs setstripe set the layout; omit striping_* hints"},
    {"id": "no_align_lustre", "forbid": r"^\s*ALIGN\s*=\s*1\b",
     "why": "H5Pset_alignment 4 MB on Lustre + ROMIO collective writes: -29% / -24% / -12% (2026-06-25)",
     "fix": "keep ALIGN=0 on Lustre"},
    {"id": "no_page_buffer_with_coll_md", "forbid": r"(?=.*COLLECTIVE_METADATA=YES)(?=.*(?:page_buffer|FSPACE_STRATEGY_PAGE))",
     "why": "H5Fcreate fails: 'collective metadata writes are not supported with page buffering' (HDF5 1.14.x)",
     "fix": "no page buffering with COLLECTIVE_METADATA=YES"},
    {"id": "write_oversized", "forbid": r"(?=.*DIM_1=33554432)(?=.*NUM_DIMS=2)",
     "why": "the sample write.cfg (DIM_1=33554432, NUM_DIMS=2, DIM_2=2, TIMESTEPS=6) at 768 ranks writes ~1.6-1.7 TB/rep in 35-40+ min",
     "fix": "shrink DIM_1 (/16 or more, e.g. 2097152) and du-verify at 1 proc / 1 node / 8 nodes"},
    {"id": "data_dir_all", "require": r"DFTRACER_DATA_DIR=all|data_dir\s*=\s*[\"']?all", "when": r"DFTRACER_ENABLE=1",
     "why": "without DFTRACER_DATA_DIR=all events for /tmp, /scratch and other non-workspace paths are excluded",
     "fix": "DFTRACER_DATA_DIR=all (data_dir=\"all\" in session_run_with_dftracer)"},
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
    def workload_h5bench_recipe(variant: str = "") -> dict:
        """Predictor: the h5bench recipe dftracer-agents verified (binary names, -DH5BENCH_ALL=ON, HDF5 1.14 from source with the
        chid_t patch, -ldftracer_core link fixes, run env, annotation rules, INI config, write-then-read, sizing rules) as
        structured JSON. variant: optional, one of write_opt_768, write_minimal_romio_192, hdf5_iotest_768, exerciser_768,
        read_768 (measured configs). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_h5bench_check(commands: list) -> dict:
        """Validator: check a proposed h5bench recipe, INI config lines or command list against the skill's rules (H5BENCH_ALL,
        no normal_dist, -ldftracer_core, INIT(NULL,NULL,NULL), 3-arg METADATA, INI not JSON, write before read, no
        DELAYED_CLOSE, colon-separated hints not via --env, no romio_no_indep_rw / striping hints / ALIGN on Lustre, no page
        buffering with collective metadata, oversized write.cfg, DATA_DIR=all). commands: list of lines (or one newline-separated
        string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

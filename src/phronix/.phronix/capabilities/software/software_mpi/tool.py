"""software_mpi: MPI and MPI-IO (ROMIO) knowledge for dftracer work: ROMIO hints files vs Cray MPICH MPICH_MPIIO_HINTS (pattern:key=value:key=value format), the confirmed hint set on cray-mpich 9.0.1, storage-specific guidance (cb_read hurts and ds_write=disable is fatal on VAST NVMe), cb_nodes being accepted but ignored on Cray MPICH without CRAY_CB_NODES_MULTIPLIER, env propagation through mpirun -x / flux run --env / wrapper scripts, building dftracer with DFTRACER_ENABLE_MPI, the mpi.h include-path issue in clang_syntax_check, mpi4py on Cray MPICH (libmpi.so.12 vs libmpi_cray.so.12), and reading MPI_Barrier as a load-imbalance sink. Load for any MPI or collective I/O work, or on: MPICH_MPIIO_HINTS lost/binary missing under flux run --env, 'unrecognized value' for a hint, hints echoed but aggregator count stuck at 2, 'fatal error: mpi.h: No such file or directory', 'RuntimeError: cannot load MPI library ... libmpi.so.12', no MPI_File_* events in the trace, MPI_Barrier dominating a profile."""
import json
import re


def _flatten(v):
    if isinstance(v, str):
        return v.splitlines()
    if isinstance(v, dict):
        return [x for i in v.values() for x in _flatten(i)]
    if isinstance(v, list):
        return [x for i in v for x in _flatten(i)]
    return []


def _SOFTWARE_MPI_judge(commands, rules):
    """Apply the rules (forbid / require / require_if / forbid_if regexes) to the proposed commands."""
    items = commands
    if isinstance(commands, str):
        s = commands.strip()
        if s[:1] in "[{":
            try:
                items = json.loads(s)
            except ValueError:
                items = s
    lines = [ln for ln in _flatten(items) if ln.strip()]
    if not lines:
        return {"status": "inconclusive", "checks": [], "verdicts": {},
                "detail": "no commands given: pass the proposed command lines or recipe"}
    text = "\n".join(lines)
    out, verdicts = [], {}
    for r in rules:
        fl = re.I if "i" in r.get("flags", "") else 0
        pat = re.compile(r["pattern"], fl)
        when = re.compile(r["when"], fl) if r.get("when") else None
        kind = r["kind"]
        applies = when is None or bool(when.search(text))
        ok, detail = True, "not applicable"
        if applies and kind in ("forbid", "forbid_if"):
            bad = [ln for ln in lines if pat.search(ln)]
            ok = not bad
            detail = ("found: " + bad[0][:160]) if bad else "absent, as required"
        elif applies and kind in ("require", "require_if"):
            ok = bool(pat.search(text))
            detail = "present" if ok else "missing: " + r["pattern"]
        verdicts[r["id"]] = "n/a" if not applies else ("pass" if ok else "fail")
        out.append({"check": r["id"], "ok": ok, "detail": detail if ok else detail + " -- " + r["why"],
                    "fix": "" if ok else r["fix"]})
    return {"status": "fail" if any(not c["ok"] for c in out) else "pass", "checks": out, "verdicts": verdicts}


def register(mcp):

    @mcp.tool()
    def software_mpi_recipe(section: str = "") -> str:
        """The build/run/env recipe software_mpi knows, as structured JSON: barrier_analysis, cb_nodes_tuolumne_lustre5, citations, clang_syntax_check_cray, cray_aggregators, cray_mpich_9_0_1_hints, cray_mpich_hints, dftracer_mpi, env_propagation, generic_romio, mpi4py_cray, numa, romio_hints_file, storage_guidance.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (barrier_analysis, cb_nodes_tuolumne_lustre5, citations, clang_syntax_check_cray, cray_aggregators, cray_mpich_9_0_1_hints, cray_mpich_hints, dftracer_mpi, env_propagation, generic_romio, mpi4py_cray, numa, romio_hints_file, storage_guidance); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_mpi_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_MPI_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_mpi", "sections": sorted(_SOFTWARE_MPI_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_MPI_RULES]})

    @mcp.tool()
    def software_mpi_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_mpi's rules: no_mpiio_hints_via_flux_env; mpiio_hints_have_pattern; mpiio_hints_colon_separated; no_romio_no_indep_rw; no_ds_write_disable_on_vast; no_cb_read_on_vast; cray_cb_nodes_needs_multiplier; mpirun_forwards_dftracer_env; mpi4py_cray_abi; no_mpi4py_no_binary.

        Use on a proposed recipe or command list before running it, and after software_mpi_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_MPI_judge(commands, _SOFTWARE_MPI_RULES))


_SOFTWARE_MPI_RECIPE = {'romio_hints_file': {'env': 'ROMIO_HINTS=<WS>/romio_hints.txt',
                      'content': ['cb_buffer_size 67108864',
                                  'romio_cb_read enable',
                                  'romio_ds_read enable',
                                  'romio_ds_write enable',
                                  'cb_nodes <num_nodes>']},
 'cray_mpich_hints': {'env': 'MPICH_MPIIO_HINTS',
                      'format': "pathname_pattern:key=value:key=value[,pattern2:...]; '*' = all files",
                      'example': '*:romio_cb_write=enable:cb_buffer_size=67108864:cb_nodes=16:romio_ds_write=disable:striping_factor=16:striping_unit=4194304',
                      'display': 'MPICH_MPIIO_HINTS_DISPLAY=1',
                      'discover': 'strings <cray-mpich>/ofi/<compiler>/<ver>/lib/libmpi_cray.so | grep -E '
                                  "'^romio_|^cb_|^striping_|^ind_|^ds_' | sort -u",
                      'flux_delivery': 'wrapper script (never flux run --env)'},
 'cray_mpich_9_0_1_hints': {'romio_cb_write': 'enable (collective buffering writes)',
                            'romio_cb_read': 'enable (disable on VAST/NVMe)',
                            'romio_ds_write': 'disable (forces 2-phase on Lustre; FATAL on VAST)',
                            'romio_ds_read': 'disable',
                            'cb_buffer_size': '67108864',
                            'cb_nodes': '16 (match stripe count; ignored without CRAY_CB_NODES_MULTIPLIER)',
                            'cb_config_list': '*:1',
                            'striping_factor': '16 (match lfs getstripe)',
                            'striping_unit': '4194304',
                            'ind_rd_buffer_size': '4194304',
                            'ind_wr_buffer_size': '4194304',
                            'romio_lustre_cb_lock_ahead_write': 'enable',
                            'romio_lustre_cb_lock_ahead_read': 'enable',
                            'romio_lustre_cb_lock_ahead_num_extents': '4',
                            'romio_no_indep_rw': 'NOT SUPPORTED (unrecognized value)'},
 'generic_romio': {'cb_buffer_size': '67108864',
                   'romio_cb_read': 'enable (Lustre; hurts VAST)',
                   'romio_cb_write': 'enable',
                   'romio_ds_read': 'enable',
                   'romio_ds_write': 'enable (disabling FATAL on VAST)',
                   'cb_nodes': '<num_nodes>'},
 'storage_guidance': {'vast_nvme': {'romio_cb_write=enable': '+58% write BW',
                                    'romio_cb_read=enable': '-70% read BW (avoid)',
                                    'romio_ds_write=disable': 'FATAL 352 -> 95 MiB/s'},
                      'lustre': 'collective read buffering helps (high latency)',
                      'check_first': 'FS_TYPE'},
 'cb_nodes_tuolumne_lustre5': {'setup': '28 OSTs, 2 nodes x 192 ranks, DIM_1=16M, 4 TS',
                               'contiguous_fixed_writes': 'do not set (default 2)',
                               'variable_size_writes': 'do not set (pwrite p95 +2650%)',
                               'reads': 'untested; 2x stripe_count per literature',
                               'tested': {'cb_nodes=16+cb_buffer_size+striping': 'segfault (h5bench)',
                                          'cb_nodes=32 alone, 16-OST write': 'neutral (open -49%, overall 0%)',
                                          'cb_nodes=56 alone, 28-OST ND': 'neutral (close -96%, pwrite p95 +2650%)'}},
 'cray_aggregators': {'fact': 'cb_nodes alone accepted but ignored (2 aggregators)',
                      'raise_with': ['cb_nodes=<n>',
                                     'CRAY_CB_NODES_MULTIPLIER=<k>',
                                     'Lustre stripe count wide enough (lfs setstripe)'],
                      'verify': 'count distinct pids with pwrite/write ret >= 1048576 in POSIX events',
                      'flashx_2026_07_08': {'no_hints': '2 aggr, 6.80 s, 1.05 MB',
                                            'cb_nodes=8': '2 aggr, 5.53 s, 1.05 MB',
                                            'cb_nodes=16+MULTIPLIER=2+16x4MB stripes': '16 aggr, 1.45 s, 3.76 MB'},
                      'precondition': 'app must write in parallel first'},
 'env_propagation': {'mpirun': 'export VAR; mpirun -np N -x VAR ... (no automatic forwarding)',
                     'mpirun_vars': ['DFTRACER_ENABLE',
                                     'DFTRACER_INIT',
                                     'DFTRACER_DATA_DIR',
                                     'DFTRACER_LOG_FILE',
                                     'MPICH_MPIIO_HINTS',
                                     'LD_LIBRARY_PATH',
                                     'LD_PRELOAD'],
                     'flux': 'flux proxy <JOBID> flux run -N 2 -n 192 --env DFTRACER_ENABLE=1 --env '
                             'DFTRACER_LOG_FILE=<prefix> --env DFTRACER_DATA_DIR=all --env DFTRACER_INC_METADATA=1 '
                             '--env DFTRACER_INIT=FUNCTION --env LD_LIBRARY_PATH=<libs> <command>',
                     'flux_rule': 'export before flux proxy does NOT propagate; colon-bearing values via wrapper '
                                  'script'},
 'dftracer_mpi': {'build': 'cmake -DDFTRACER_ENABLE_MPI=ON ...',
                  'verify': 'grep DFTRACER_MPI_ENABLE <prefix>/include/dftracer/core/dftracer_config.hpp  -> #define '
                            'DFTRACER_MPI_ENABLE 1',
                  'runtime_match': 'strings libdftracer_core.so | grep include  (must match the system mpi.h path)'},
 'clang_syntax_check_cray': {'issue': 'mpicc --showme:incdirs returns -I/path',
                             'fix': 'extra_include_dirs=[<cray-mpich>/ofi/<compiler>/<ver>/include, '
                                    '<venv>/lib/python3.*/site-packages/dftracer/include]',
                             'find_path': "mpicc -show | grep -o '\\-I[^ ]*' | head -1"},
 'mpi4py_cray': {'symptom': 'RuntimeError: cannot load MPI library ... libmpi.so.12',
                 'cause': 'manylinux wheel expects libmpi.so.12; Cray PE has libmpi_cray.so.12',
                 'steps': ['pip download mpi4py --python-version 313 --no-deps -d <ws>/tmp',
                           'unzip the wheel',
                           'patchelf --set-rpath "<venv>/lib:<cray-mpich>/ofi/crayclang/20.0/lib" '
                           'mpi4py/MPI.mpich.cpython-313-x86_64-linux-gnu.so',
                           'ln -sf <cray-mpich>/ofi/crayclang/20.0/lib/libmpi_cray.so.12 <venv>/lib/libmpi.so.12',
                           'zip -q -r mpi4py-patched.whl mpi4py/ mpi4py-*.dist-info/',
                           'MPI4PY_MPIABI=mpich pip install --force-reinstall --no-deps mpi4py-patched.whl',
                           "python -c 'from mpi4py import MPI; print(MPI.Get_version())'"],
                 'persist_env': {'MPI4PY_MPIABI': 'mpich',
                                 'LD_LIBRARY_PATH': '<venv>/lib:<cray-mpich>/ofi/crayclang/20.0/lib:$LD_LIBRARY_PATH'},
                 'known_good': 'Python 3.13, cray-mpich 9.1.0, mpi4py 4.1.2',
                 'avoid': '--no-binary=mpi4py on Python 3.13 + NFS'},
 'numa': {'inspect': 'numactl --hardware',
          'bind': 'numactl --cpunodebind=0 --membind=0 <cmd>',
          'openmpi': 'mpirun --map-by numa:pe=<cores_per_node>'},
 'barrier_analysis': {'sink_tell': 'per-barrier mean rises while wall clock falls (ScaFFold 262 -> 657 ms mean, '
                                   'train 1.97 -> 1.64 s)',
                      'min_run': '>= ~10 min training at fixed budget',
                      'harness_examples': ['IOR timing loop', 'RAJAPerf KernelBase::startTimer/stopTimer'],
                      'only_lever_for_harness': 'MPICH_SHARED_MEM_COLL_OPT=1 (Tuolumne IOR prior: no_change -1.6%)',
                      'metrics': 'mean/p95/p99 + wall clock, not comparator p50'},
 'citations': {'WisIO': 'Yildirim et al., ICS 2025, https://dl.acm.org/doi/10.1145/3721145.3730395',
               'Drishti': 'Bez et al., PDSW 2022, https://ieeexplore.ieee.org/document/10027503',
               'collectives': 'Thakur et al., IJHPCA 19(1) 2005, https://doi.org/10.1177/1094342005051521',
               'algorithm_selection': 'Nuriyev & Lastovetsky, https://arxiv.org/pdf/2004.11062v1'}}

_SOFTWARE_MPI_RULES = [{'id': 'no_mpiio_hints_via_flux_env',
  'kind': 'forbid',
  'pattern': '--env[= ][\'\\"]?MPICH_MPIIO_HINTS=',
  'why': 'Colons/semicolons in MPICH_MPIIO_HINTS make flux run lose the binary argument.',
  'fix': 'Export MPICH_MPIIO_HINTS in a wrapper script ending in exec "$@" and run flux run ... bash wrapper.sh '
         '<binary>.'},
 {'id': 'mpiio_hints_have_pattern',
  'kind': 'forbid',
  'pattern': 'MPICH_MPIIO_HINTS=[\'\\"]?[a-z_]+=',
  'why': 'MPICH_MPIIO_HINTS needs a pathname pattern first: pattern:key=value:key=value.',
  'fix': "Prefix with '*:' (all files) or a file pattern."},
 {'id': 'mpiio_hints_colon_separated',
  'kind': 'forbid',
  'pattern': 'MPICH_MPIIO_HINTS=[\'\\"]?[^\'\\"\\s]*;',
  'why': 'Key=value pairs are colon-separated; patterns are comma-separated. Semicolons are not part of the format.',
  'fix': 'Use *:k1=v1:k2=v2.'},
 {'id': 'no_romio_no_indep_rw',
  'kind': 'forbid',
  'pattern': 'romio_no_indep_rw',
  'why': "Not supported on cray-mpich 9.0.1: silently dropped with 'unrecognized value'.",
  'fix': 'Remove romio_no_indep_rw.'},
 {'id': 'no_ds_write_disable_on_vast',
  'kind': 'forbid_if',
  'pattern': 'romio_ds_write[= ]disable',
  'when': 'vast',
  'flags': 'i',
  'why': 'Disabling data-sieving writes on VAST collapsed write BW 352 -> 95 MiB/s.',
  'fix': 'Keep romio_ds_write enabled (default) on VAST.'},
 {'id': 'no_cb_read_on_vast',
  'kind': 'forbid_if',
  'pattern': 'romio_cb_read[= ]enable',
  'when': 'vast',
  'flags': 'i',
  'why': 'Collective read buffering cut read BW -70% on VAST NVMe.',
  'fix': 'Use romio_cb_read=disable (or leave unset) on VAST.'},
 {'id': 'cray_cb_nodes_needs_multiplier',
  'kind': 'require_if',
  'pattern': 'CRAY_CB_NODES_MULTIPLIER=\\d',
  'when': 'MPICH_MPIIO_HINTS=[^\\n]*cb_nodes=',
  'why': 'Cray MPICH accepts and echoes cb_nodes but keeps 2 aggregators unless CRAY_CB_NODES_MULTIPLIER is set too.',
  'fix': 'Add export CRAY_CB_NODES_MULTIPLIER=<k> (and a wide Lustre stripe); verify aggregators from the trace.'},
 {'id': 'mpirun_forwards_dftracer_env',
  'kind': 'require_if',
  'pattern': 'mpirun\\b[^\\n]*-x\\s+DFTRACER_ENABLE\\b',
  'when': '(?s)DFTRACER_ENABLE=1.*\\bmpirun\\b',
  'why': 'mpirun does not forward the shell environment; ranks run untraced.',
  'fix': 'Pass -x DFTRACER_ENABLE -x DFTRACER_INIT -x DFTRACER_DATA_DIR -x DFTRACER_LOG_FILE -x LD_LIBRARY_PATH -x '
         'LD_PRELOAD.'},
 {'id': 'mpi4py_cray_abi',
  'kind': 'require_if',
  'pattern': 'MPI4PY_MPIABI=mpich',
  'when': '(?s)(cray-mpich|libmpi_cray).*pip\\s+install[^\\n]*mpi4py|pip\\s+install[^\\n]*mpi4py.*(cray-mpich|libmpi_cray)',
  'why': 'The mpi4py wheel expects libmpi.so.12; on Cray MPICH it needs the patched wheel + MPI4PY_MPIABI=mpich.',
  'fix': 'Patch the wheel (patchelf RPATH + libmpi.so.12 symlink) and install with MPI4PY_MPIABI=mpich.'},
 {'id': 'no_mpi4py_no_binary',
  'kind': 'forbid',
  'pattern': '--no-binary[= ]?:?\\S*mpi4py',
  'why': "On Python 3.13 + NFS the build succeeds but pip's atomic rename onto NFS fails.",
  'fix': 'Download and extract the wheel manually, patch, re-zip, install.'}]

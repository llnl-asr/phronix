"""software_posix: POSIX I/O optimization by layer - L1 application (buffering/coalescing, access ordering, fd reuse, async I/O, stat caching), L2 software hints (posix_fadvise, MALLOC_ARENA_MAX, OMP/MKL threads), L3 OS/filesystem (Lustre lfs setstripe ONLY on Lustre, near-node flash / Rabbit, block-device readahead, vm dirty/page cache sysctls, I/O scheduler) - plus dftracer DFTRACER_DATA_DIR for capturing POSIX events and manual proposals for posix_*_ops_slope metrics. Load for any POSIX I/O bottleneck (small_io_pct, rand_pct, read/write_time_pct, metadata_time_pct, posix_*_ops_slope), on dftracer `Code 2001` with DFTRACER_DATA_DIR=all, `lfs` errors on non-Lustre mounts, or a 4x write regression from romio_ds_write=disable on VAST."""
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


def _SOFTWARE_POSIX_judge(commands, rules):
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
    def software_posix_recipe(section: str = "") -> str:
        """The build/run/env recipe software_posix knows, as structured JSON: bottleneck_map, dftracer, l1, l2, l3_lustre, l3_near_node_flash, l3_readahead, l3_scheduler, l3_vm, slope_metrics.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (bottleneck_map, dftracer, l1, l2, l3_lustre, l3_near_node_flash, l3_readahead, l3_scheduler, l3_vm, slope_metrics); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_posix_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_POSIX_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_posix", "sections": sorted(_SOFTWARE_POSIX_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_POSIX_RULES]})

    @mcp.tool()
    def software_posix_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_posix's rules: data_dir_not_all; lfs_only_on_lustre; no_ds_write_disable_vast; readahead_only_local; preload_needs_data_dir.

        Use on a proposed recipe or command list before running it, and after software_posix_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_POSIX_judge(commands, _SOFTWARE_POSIX_RULES))


_SOFTWARE_POSIX_RECIPE = {'l1': {'small_io_pct': ['staging buffer coalescing',
                         'batch writes to pre-allocated buffer',
                         'readv/writev',
                         'Python: larger chunk_size, np.fromfile'],
        'rand_pct': ['sort accesses by file offset',
                     'posix_fadvise SEQUENTIAL',
                     'mmap for random access',
                     'DL: sort by file size, shuffle indices'],
        'read_write_time_pct': ['keep fds open',
                                'O_DIRECT for low reuse',
                                'io_uring / aiofiles / asyncio',
                                'fallocate before write'],
        'metadata_time_pct': ['cache stat()',
                              'open once per epoch',
                              'pre-built file lists',
                              'try/except over os.path.exists']},
 'l2': {'fadvise': ['posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL)', 'posix_fadvise(fd, 0, 0, POSIX_FADV_WILLNEED)'],
        'env': {'MALLOC_ARENA_MAX': '2',
                'OMP_NUM_THREADS': '<physical_core_count>',
                'MKL_NUM_THREADS': '<physical_core_count>',
                'HBWMALLOC_POLICY': 'transparent'}},
 'l3_lustre': {'only_when': 'FS_TYPE=lustre',
               'never_on': ['vast', 'nfs', 'gpfs', 'beegfs', 'local'],
               'stripe_count': 'lfs setstripe -c <N> <dir>  # N=OST count; <=8 for <1GB files, 16+ large; rollback '
                               '-c 1',
               'stripe_size': 'lfs setstripe -S 4m <dir>  # rollback -S 1m',
               'per_file': 'lfs setstripe -c 4 -S 4m <dir>/<file>',
               'dne': 'lfs mkdir -c <N> <dir>  # admin'},
 'l3_near_node_flash': {'tuolumne_rabbit': 'flux ... -S "#DW jobdw type=<xfs|gfs2|lustre> ..."',
                        'tier_order': ['SHM', 'XFS', 'GFS2', 'Lustre']},
 'l3_readahead': {'only_when': 'local_nvme or local_hdd',
                  'set': 'sudo blockdev --setra <KB> /dev/<dev>',
                  'default': 128,
                  'recommended': '4096-16384',
                  'check': 'blockdev --getra /dev/<dev>',
                  'rollback': 'sudo blockdev --setra 128 /dev/<dev>'},
 'l3_vm': {'vm.dirty_ratio': 20,
           'vm.dirty_background_ratio': 5,
           'vm.dirty_expire_centisecs': 3000,
           'vm.dirty_writeback_centisecs': 500,
           'vm.vfs_cache_pressure': '50 (read-heavy; default 100)'},
 'l3_scheduler': {'check': 'cat /sys/block/<dev>/queue/scheduler',
                  'nvme': 'none',
                  'hdd': 'mq-deadline',
                  'rollback': 'echo <original> | sudo tee /sys/block/<dev>/queue/scheduler'},
 'dftracer': {'DFTRACER_DATA_DIR': {'all_io': '/',
                                    'tmp': '/tmp',
                                    'multiple': '/data:/scratch',
                                    'never': 'all (Code 2001 in C++)'}},
 'slope_metrics': {'posix_data_ops_slope': 'larger transfer (L1); ROMIO hints (L2); stripe tuning (L3)',
                   'posix_close_ops_slope': 'stagger closes (L1); ind_wr_buffer_size (L2); client cache (L3)',
                   'posix_metadata_ops_slope': 'shared file not file-per-process (L1); pre-create (L2); DNE (L3)',
                   'posix_seek_ops_slope': 'larger transfer + romio_cb_write=enable (L2)'},
 'bottleneck_map': {'small_io_pct': 'buffer (L1)',
                    'rand_pct/seq_pct low': 'sort access order (L1)',
                    'read_time_pct': 'async I/O, O_DIRECT (L1/L2)',
                    'write_time_pct': 'async write, fallocate (L1/L2)',
                    'metadata_time_pct': 'cache stat, open once (L1)',
                    'posix_seek_ops_slope': 'ROMIO cb_write, larger -t (L2)'}}

_SOFTWARE_POSIX_RULES = [{'id': 'data_dir_not_all',
  'kind': 'forbid',
  'pattern': 'DFTRACER_DATA_DIR=[\\"\']?all\\b',
  'why': "'all' is only understood by the Python helper; the C++ runtime fails with Code 2001.",
  'fix': 'DFTRACER_DATA_DIR=/ (or real colon-separated paths).'},
 {'id': 'lfs_only_on_lustre',
  'kind': 'forbid_if',
  'pattern': '\\blfs\\s+(setstripe|mkdir)\\b',
  'when': 'FS_TYPE=[\\"\']?(vast|nfs|gpfs|beegfs|local\\w*)',
  'flags': 'i',
  'why': 'lfs commands are no-ops or errors on non-Lustre mounts.',
  'fix': 'Skip Lustre L3 settings; use the tuning for the actual filesystem.'},
 {'id': 'no_ds_write_disable_vast',
  'kind': 'forbid_if',
  'pattern': 'romio_ds_write\\s*[= ]\\s*disable',
  'when': 'vast',
  'flags': 'i',
  'why': 'romio_ds_write=disable is a 4x write regression on VAST NVMe.',
  'fix': 'Leave data-sieving writes at the default on VAST.'},
 {'id': 'readahead_only_local',
  'kind': 'forbid_if',
  'pattern': 'blockdev\\s+--setra',
  'when': 'FS_TYPE=[\\"\']?(lustre|vast|nfs|gpfs|beegfs)',
  'flags': 'i',
  'why': 'Kernel block-device readahead tuning applies only to local NVMe/HDD, not network filesystems.',
  'fix': 'Use posix_fadvise (L2) or filesystem-level settings instead.'},
 {'id': 'preload_needs_data_dir',
  'kind': 'require_if',
  'pattern': 'DFTRACER_DATA_DIR=',
  'when': 'libdftracer_preload',
  'why': 'POSIX events are captured only for paths under DFTRACER_DATA_DIR.',
  'fix': "export DFTRACER_DATA_DIR=/ (or the app's data directories)."}]

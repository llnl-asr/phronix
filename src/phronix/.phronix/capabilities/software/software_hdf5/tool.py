"""software_hdf5: HDF5 for dftracer sessions: ALWAYS build HDF5 1.14.5 from source into the session workspace (never the cray-hdf5 / cray-hdf5-parallel or any site HDF5 module), the dftracer-compatible exact series (1.8.23, 1.10.5, 1.12.3, 1.14.5), fetching tarballs from the HDF Group FTP because GitHub releases 404 on Cray PE, the H5Apublic.h `chid_t` typo patch, building dftracer with -DDFTRACER_ENABLE_HDF5=ON, HDF5_DIR / LD_LIBRARY_PATH, and L2 tuning (chunk/cache/metadata/alignment, collective IOR flags, Lustre stripe = collective buffer). Load for any HDF5 or parallel I/O work, or on: a 404 from github.com/HDFGroup/hdf5/releases, `chid_t` compile errors in H5Apublic.h from dftracer/brahma C++, H5Fcreate/H5Dwrite events absent from traces, L2 HDF5 optimizations with zero effect (HDF5 1.10), small aggregated writes (~1 MB) on Lustre, or an app 'collective' flag that leaves one rank writing everything."""
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


def _SOFTWARE_HDF5_judge(commands, rules):
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
    def software_hdf5_recipe(section: str = "") -> str:
        """The build/run/env recipe software_hdf5 knows, as structured JSON: build, detect, dftracer, download, env, ior_hdf5_flags, l2_chunk_cache, l2_metadata, lustre_stripe, source_policy, verify_collective, versions.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (build, detect, dftracer, download, env, ior_hdf5_flags, l2_chunk_cache, l2_metadata, lustre_stripe, source_policy, verify_collective, versions); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_hdf5_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_HDF5_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_hdf5", "sections": sorted(_SOFTWARE_HDF5_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_HDF5_RULES]})

    @mcp.tool()
    def software_hdf5_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_hdf5's rules: no_cray_hdf5_module; no_github_hdf5_tarball; parallel_hdf5_min_1_14; dftracer_enable_hdf5; hdf5_lib_on_ld_path; patch_chid_t_1_14_3.

        Use on a proposed recipe or command list before running it, and after software_hdf5_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_HDF5_judge(commands, _SOFTWARE_HDF5_RULES))


_SOFTWARE_HDF5_RECIPE = {'versions': {'compatible_exact': ['1.8.23', '1.10.5', '1.12.3', '1.14.5'],
              'preferred': '1.14.5',
              'parallel_io_min': '1.14.x',
              'bad_for_parallel_l2': '1.10.x (page buffer no-op with MPI-IO VFD, H5Fcreate_async synchronous)',
              'needs_chid_t_patch': ['1.14.3', 'cray-hdf5 module']},
 'source_policy': {'build_from_source': True,
                   'never_link': ['cray-hdf5', 'cray-hdf5-parallel', 'any site HDF5 module'],
                   'modules_only_for': 'compiler/MPI toolchain (mpicc, mpicxx)',
                   'prefix': '<ws>/hdf5_1.14 (or <ws>/install_hdf5)'},
 'download': {'cray_pe': 'curl -fkL '
                         'https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-<major>.<minor>/hdf5-<ver>/src/hdf5-<ver>.tar.gz '
                         '-o hdf5-<ver>.tar.gz',
              'non_cray': 'wget https://github.com/HDFGroup/hdf5/releases/download/hdf5_<ver>/hdf5-<ver>.tar.gz',
              'github_on_cray': '404 (firewall) - do not use'},
 'build': {'configure': 'CC=mpicc ./configure --prefix=<ws>/hdf5_1.14 --enable-parallel --enable-shared '
                        '--enable-build-mode=production --with-zlib=/usr',
           'make': 'make -j$(nproc) && make install',
           'verify': "h5cc -showconfig | grep 'Version:'  # 1.14.x",
           'patch_chid_t': "sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' "
                           '<ws>/hdf5_1.14/include/H5Apublic.h'},
 'env': {'HDF5_DIR': '<ws>/hdf5_1.14',
         'LD_LIBRARY_PATH': '<ws>/hdf5_1.14/lib:$LD_LIBRARY_PATH',
         'scope': 'every subsequent shell command',
         'cmake_flag_for_apps': '-DHDF5_DIR=<ws>/hdf5_1.14'},
 'dftracer': {'cmake_flags': ['-DDFTRACER_ENABLE_HDF5=ON', '-DHDF5_ROOT=<ws>/hdf5_1.14'],
              'symptom_if_missing': 'no H5Fcreate/H5Dwrite events in traces'},
 'detect': {'commands': ['h5cc --version', 'h5dump --version', 'pkg-config --modversion hdf5'],
            'session_detect_keys': ['hdf5_system.compatible', 'hdf5_system.recommended']},
 'l2_chunk_cache': {'when': 'small_io_pct high (bandwidth/iops)',
                    'calls': ['H5Pset_chunk(dcpl, 1, {1048576})',
                              'H5Pset_coll_metadata_write(fapl, 1)',
                              'H5Pset_all_coll_metadata_ops(fapl, 1)',
                              'H5Pset_cache(fapl, 0, 521, 64*1024*1024, 1.0)',
                              'H5Pset_alignment(fapl, 0, stripe_size)']},
 'l2_metadata': {'when': 'metadata_time_pct high (metadata_ops)',
                 'calls': ['H5Pget_mdc_config(fapl,&cfg); cfg.evictions_enabled = FALSE; '
                           'H5Pset_mdc_config(fapl,&cfg)',
                           'H5Pset_object_track_times(dcpl, 0)']},
 'ior_hdf5_flags': {'flags': '-a HDF5 -b 64m -t 16m -s 4 -c -Y',
                    '-c': 'collective I/O',
                    '-Y': 'collective HDF5 metadata writes',
                    'pairs_with': 'romio_cb_write=enable'},
 'lustre_stripe': {'commands': ['lfs setstripe -c 16 -S 4M /p/lustre5/$USER/<app>/<run>',
                                'lfs getstripe -d /p/lustre5/$USER/<app>/<run>'],
                   'rules': ['stripe the directory before the first file is created',
                             'fresh directory per iteration',
                             'striping_unit == stripe size',
                             'cb_buffer_size multiple of stripe size',
                             'stripe count >= aggregator count'],
                   'measured_2026_07_08': {'before': '8 x 1MB: 1.05 MB writes, 2 aggregators, 5.53 s',
                                           'after': '16 x 4MB: 3.76 MB writes, 16 aggregators, 1.45 s'}},
 'verify_collective': 'trace: few ranks issuing large (>= stripe size) pwrite; ~one rank with nearly all bytes = '
                      'serial'}

_SOFTWARE_HDF5_RULES = [{'id': 'no_cray_hdf5_module',
  'kind': 'forbid',
  'pattern': '\\b(module\\s+(load|add|swap)|ml)\\b[^\\n]*\\bcray-hdf5',
  'flags': 'i',
  'why': 'HDF5 must be built from source for dftracer sessions; Cray HDF5 has header typos and a drifting version '
         'outside the compatible series.',
  'fix': "Drop the cray-hdf5 module; build HDF5 1.14.5 from source with the toolchain's mpicc and point HDF5_DIR at "
         'it.'},
 {'id': 'no_github_hdf5_tarball',
  'kind': 'forbid',
  'pattern': 'github\\.com/HDFGroup/hdf5/releases/download',
  'why': 'GitHub HDF5 release downloads 404 on Cray PE systems (firewall).',
  'fix': 'Download from '
         'https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-<maj>.<min>/hdf5-<ver>/src/hdf5-<ver>.tar.gz with curl '
         '-fkL.'},
 {'id': 'parallel_hdf5_min_1_14',
  'kind': 'forbid_if',
  'pattern': 'hdf5[-_/]1\\.(8|10)\\.\\d',
  'when': '--enable-parallel|CC=mpicc|H5FD_MPIO|-a\\s+HDF5',
  'why': 'HDF5 1.8/1.10 silently disable L2 parallel optimizations (page buffer no-op with MPI-IO VFD, async create '
         'synchronous).',
  'fix': 'Use HDF5 1.14.5 for parallel I/O.'},
 {'id': 'dftracer_enable_hdf5',
  'kind': 'require_if',
  'pattern': '-DDFTRACER_ENABLE_HDF5=(ON|1|TRUE)',
  'when': 'cmake[^\\n]*-DDFTRACER_[^\\n]*-DHDF5_(ROOT|DIR)=|cmake[^\\n]*-DHDF5_(ROOT|DIR)=[^\\n]*-DDFTRACER_',
  'why': 'Without DFTRACER_ENABLE_HDF5=ON dftracer records no H5Fcreate/H5Dwrite events even when annotated.',
  'fix': 'Add -DDFTRACER_ENABLE_HDF5=ON to the dftracer cmake line.'},
 {'id': 'hdf5_lib_on_ld_path',
  'kind': 'require_if',
  'pattern': 'LD_LIBRARY_PATH=[^\\n]*hdf5[^\\n:]*/lib',
  'when': 'export\\s+HDF5_DIR=',
  'why': 'After a source build HDF5_DIR and LD_LIBRARY_PATH=<prefix>/lib must be set in every subsequent command.',
  'fix': 'export LD_LIBRARY_PATH=<hdf5 prefix>/lib:$LD_LIBRARY_PATH next to HDF5_DIR.'},
 {'id': 'patch_chid_t_1_14_3',
  'kind': 'require_if',
  'pattern': 'sed[^\\n]*chid_t[^\\n]*hid_t',
  'when': 'hdf5[-_]1\\.14\\.3',
  'why': 'HDF5 1.14.3 ships the `chid_t` typo in H5Apublic.h that breaks dftracer/brahma C++.',
  'fix': "sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' <prefix>/include/H5Apublic.h (or use "
         '1.14.5).'}]

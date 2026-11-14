"""software_gcc: GCC / GNU toolchain, site-neutral: probing which GCC versions a site offers (module -t avail gcc, multiple module families), pairing GCC with an MPI wrapper (Cray per-compiler wrapper dirs vs site MPI modules that follow the loaded GCC), compiler -> MPI -> CC/CXX load order, switching compilers on an existing CMake/autotools/venv build, and GCC as the libstdc++ header provider for clang-based compilers ('Selected GCC installation:'). Points to the system_* capability that holds each site's module names. Load for any build that needs GCC/GNU instead of the site default compiler, or on mpicc using a different compiler than the gcc on PATH, CMake refusing a compiler change in CMakeCache.txt, or clang/hipcc failing on missing/old C++ standard-library headers."""
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


def _SOFTWARE_GCC_judge(commands, rules):
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
    def software_gcc_recipe(section: str = "") -> str:
        """The build/run/env recipe software_gcc knows, as structured JSON: clang_libstdcxx, expect, mpi_pairing, probes, sites, switch_compiler.

        Use before building, configuring or running anything this capability covers, to get its facts as data instead
        of re-reading prose. section: one top-level key of the recipe (clang_libstdcxx, expect, mpi_pairing, probes, sites, switch_compiler); blank = all of it. Returns JSON
        {status, capability, sections, recipe, checks: [{id, why}] (what software_gcc_check enforces)} or
        {status: "error", error} for an unknown section.
        """
        recipe = _SOFTWARE_GCC_RECIPE
        if section:
            if section not in recipe:
                return json.dumps({"status": "error", "error": "unknown section %r; one of %s" % (section, sorted(recipe))})
            recipe = {section: recipe[section]}
        return json.dumps({"status": "ok", "capability": "software_gcc", "sections": sorted(_SOFTWARE_GCC_RECIPE), "recipe": recipe,
                           "checks": [{"id": r["id"], "why": r["why"]} for r in _SOFTWARE_GCC_RULES]})

    @mcp.tool()
    def software_gcc_check(commands: str = "") -> str:
        """Check a proposed recipe or command list against software_gcc's rules: mpi_after_compiler; cc_from_mpi_wrapper; tuolumne_gnu_mpich_11_2.

        Use on a proposed recipe or command list before running it, and after software_gcc_recipe to rule on what was
        planned. commands: newline-separated command lines / script text, a JSON list of them, or a JSON object (its
        string values are checked). Deterministic regex rules; nothing runs. Returns JSON {status: pass|fail|inconclusive,
        checks: [{check, ok, detail, fix}], verdicts: {rule id: pass|fail|n/a}}; inconclusive when nothing was given.
        """
        return json.dumps(_SOFTWARE_GCC_judge(commands, _SOFTWARE_GCC_RULES))


_SOFTWARE_GCC_RECIPE = {'probes': ['module -t avail gcc',
            'which gcc g++ gfortran',
            'gcc --version | head -1',
            'module -t avail <mpi-module>',
            'ls <mpi-root>/<mpi-version>/<fabric>/gnu/'],
 'expect': ['more than one GCC module family (vendor/PE and site toolchain)',
            'bare-shell gcc = newest site toolchain GCC, possibly without MPI wrapper',
            'installed GCC version != MPI build available'],
 'mpi_pairing': {'cray_style': 'one wrapper dir per compiler family+version: '
                               '<mpi-root>/<mpi-version>/<fabric>/<family>/<compiler-version>/bin/mpicc; only '
                               'versions present there are usable',
                 'site_mpi_module': 'e.g. MVAPICH2: resolves to the build matching the loaded GCC when the compiler '
                                    'is loaded first',
                 'order': ['module load/swap <compiler>',
                           'module load <mpi>',
                           'export CC=$(which mpicc) CXX=$(which mpicxx)']},
 'switch_compiler': {'cmake': 'rm -rf <build_dir> (compiler pinned in CMakeCache.txt), reconfigure',
                     'autotools': 're-run ./configure with new CC, make clean',
                     'python_venv': 'rebuild compiled wheels, do not mix compilers'},
 'clang_libstdcxx': {'applies_to': ['Cray clang', 'hipcc', 'amdclang'],
                     'verify': "mpicxx -v | grep 'Selected GCC installation:'",
                     'action': 'choose the GCC toolset deliberately (site path in system_tuolumne)'},
 'sites': {'tuolumne': {'pe': 'Cray PE, AMD MI300A, Flux',
                        'families': {'cray_pe': 'gcc-native 10.3-13.2', 'site': 'gcc 10.3.1-13.3.1'},
                        'bare_shell_gcc': '13.3.1',
                        'cray_mpich_gnu_wrapper': 'gnu/11.2 only (9.0.1 and 9.1.0)',
                        'gnu_plus_mpi': ['PrgEnv-gnu', 'gcc-native/11.2'],
                        'see': 'system_tuolumne'},
           'dane': {'pe': 'CPU-only Sapphire Rapids, Slurm',
                    'site_gcc': '10.3.1-13.3.1',
                    'dftracer_pairing': 'GCC 12.1.1 toolchain module + MVAPICH2 module (auto-selects matching build)',
                    'see': 'system_dane'},
           'matrix': {'pe': 'H100 + Sapphire Rapids, Slurm',
                      'site_gcc': 'same set as Dane',
                      'cuda_cap': 'CUDA 12.6 supports GCC <= 13; pick GCC for CUDA first, MPI second',
                      'see': 'system_matrix'},
           'tioga': {'pe': 'AMD GPU, Cray PE',
                     'default_compiler': 'Cray (not GCC)',
                     'gnu_pairing': 'not yet recorded',
                     'see': 'system_tioga'},
           'container': {'compiler': 'from the image, not modules', 'see': 'system_container'},
           'unknown': 'run probes, system_save, add a row; never invent a pairing'}}

_SOFTWARE_GCC_RULES = [{'id': 'mpi_after_compiler',
  'kind': 'forbid',
  'pattern': 'module\\s+load\\s+[^\\n]*(cray-mpich|mvapich|openmpi|mpich)[^\\n]*\\s(gcc|gcc-native|PrgEnv-gnu)(/\\S*)?(\\s|$)',
  'why': 'The compiler must be loaded before the MPI module so the MPI module resolves the matching per-compiler '
         'build.',
  'fix': 'Load/swap the compiler first, then the MPI module, then export CC/CXX.'},
 {'id': 'cc_from_mpi_wrapper',
  'kind': 'require_if',
  'pattern': 'CC=\\$\\(which\\s+mpicc\\)|CC=\\S*mpicc',
  'when': 'module\\s+load\\s+[^\\n]*(cray-mpich|mvapich|openmpi|mpich)',
  'why': 'After loading compiler then MPI, CC/CXX must point at the MPI wrapper or the build uses the bare-shell '
         'gcc.',
  'fix': 'export CC=$(which mpicc) CXX=$(which mpicxx).'},
 {'id': 'tuolumne_gnu_mpich_11_2',
  'kind': 'forbid',
  'pattern': 'gcc-native/(?!11\\.2)\\d+[^\\n]*cray-mpich|cray-mpich[^\\n]*gcc-native/(?!11\\.2)\\d+',
  'why': 'On Cray PE (Tuolumne) cray-mpich ships a GNU wrapper dir for gnu/11.2 only.',
  'fix': 'Use PrgEnv-gnu + gcc-native/11.2 with cray-mpich.'}]

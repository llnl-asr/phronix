"""workload_gromacs: the GROMACS (molecular dynamics, CMake, C++/HIP) build/run recipe that dftracer-agents' workload-gromacs
skill verified on Tuolumne, as structured data (predictor), and a deterministic check of a proposed recipe or command list
against that skill's rules (validator). Nothing here runs a build or a job."""
import json
import re

CAP = "workload_gromacs"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "GROMACS",
    "what": "GROningen MAchine for Chemical Simulations: molecular dynamics simulation package",
    "build_system": "cmake",
    "languages": ["C++", "CUDA/HIP", "Fortran", "Python bindings"],
    "systems": ["tuolumne"],
    "modules": ["cmake/3.29.2"],
    "env": {},
    "requirements": [
        "CMake 3.28+ (system default 3.24.2 is too old): module load cmake/3.29.2 on Tuolumne",
        "HDF5 optional but recommended for checkpoint I/O; GROMACS rejects the system HDF5 1.10.5 (needs 1.10.7+): build HDF5 1.14.x from source (software_hdf5)",
        "MPI via -DGMX_MPI=ON; AMD MI300A GPU via -DGMX_GPU=HIP (ROCm)",
    ],
    "dependencies": {
        "hdf5": [
            "curl -fkL https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.14/hdf5-1.14.3/src/hdf5-1.14.3.tar.gz -o hdf5-1.14.3.tar.gz",
            "tar xf hdf5-1.14.3.tar.gz && cd hdf5-1.14.3",
            "CC=mpicc ./configure --prefix=$PWD/../hdf5_1.14 --enable-parallel --enable-shared --enable-build-mode=production --with-zlib=/usr",
            "make -j8 && make install",
            "cd .. && sed -i 's/H5Aread_async(chid_t attr_id/H5Aread_async(hid_t attr_id/' hdf5_1.14/include/H5Apublic.h",
        ],
    },
    "configure": [
        "cmake -S source -B build -DCMAKE_INSTALL_PREFIX=<install_dir> -DCMAKE_BUILD_TYPE=RelWithDebInfo -DGMX_MPI=ON "
        "-DGMX_GPU=HIP -DGMX_OPENMP=ON -DGMX_DOUBLE=OFF -DBUILD_TESTING=OFF -DGMX_BUILD_HELP=OFF -DGMX_BUILD_MANUAL=OFF "
        "-DGMX_INSTALL_LEGACY_API=ON -DHDF5_DIR=<session_hdf5_prefix> "
        "-DMPI_C_COMPILER=/opt/cray/pe/mpich/9.0.1/ofi/crayclang/20.0/bin/mpicc "
        "-DMPI_CXX_COMPILER=/opt/cray/pe/mpich/9.0.1/ofi/crayclang/20.0/bin/mpicxx",
    ],
    "cmake_flags": {
        "CMAKE_BUILD_TYPE": "RelWithDebInfo", "GMX_MPI": "ON", "GMX_GPU": "HIP", "GMX_OPENMP": "ON", "GMX_DOUBLE": "OFF",
        "BUILD_TESTING": "OFF", "GMX_BUILD_HELP": "OFF", "GMX_BUILD_MANUAL": "OFF", "GMX_INSTALL_LEGACY_API": "ON",
        "HDF5_DIR": "<session_hdf5_prefix> (HDF5 1.14 built from source)",
    },
    "build": ["cmake --build build -j", "cmake --install build"],
    "smoke": ["TBD: a typical GROMACS smoke test uses `gmx mdrun` on a small test system (to be added after the first successful build)"],
    "run": [],
    "variants": {},
    "notes": [
        "-DGMX_BUILD_HELP=OFF only disables HTML help, not the PDF manual: without -DGMX_BUILD_MANUAL=OFF make install fails building "
        "the PDF manual (sphinx_copybutton missing) (2026-08-07, Tuolumne, GROMACS main)",
        "do not install sphinx_copybutton into the system Python (no sudo) and do not edit docs/manual/CMakeLists.txt (diverges from upstream)",
    ],
}

# rule kinds: forbid (regex must not match any command), require (regex must match some command; only when `when` matches, if given)
RULES = [
    {"id": "manual_off", "require": r"-DGMX_BUILD_MANUAL=OFF", "when": r"\bcmake\b.*-S|\bcmake\b.*-DGMX_",
     "why": "the PDF manual target builds during make install and needs sphinx_copybutton (not in the system Python): "
            "'sphinx.errors.ExtensionError: Could not import extension sphinx_copybutton'",
     "fix": "add -DGMX_BUILD_MANUAL=OFF to the cmake configure line"},
    {"id": "help_off", "require": r"-DGMX_BUILD_HELP=OFF", "when": r"\bcmake\b.*-S|\bcmake\b.*-DGMX_",
     "why": "the help build also pulls the Sphinx docs", "fix": "add -DGMX_BUILD_HELP=OFF"},
    {"id": "cmake_version", "forbid": r"module\s+load\s+cmake/3\.(?:[0-9]|1[0-9]|2[0-7])(?:\.|\b)",
     "why": "GROMACS needs CMake 3.28+; the Tuolumne default 3.24.2 is too old", "fix": "module load cmake/3.29.2"},
    {"id": "no_system_hdf5", "forbid": r"HDF5_DIR=/usr\b|hdf5[-/]1\.10\.[0-6]\b",
     "why": "system HDF5 1.10.5 is detected but rejected (GROMACS needs 1.10.7+)",
     "fix": "build HDF5 1.14.x from source in the session (software_hdf5) and pass -DHDF5_DIR=<that prefix>"},
    {"id": "no_sphinx_install", "forbid": r"pip\s+install\s+.*sphinx[_-]copybutton",
     "why": "installing sphinx_copybutton into the system Python is not allowed (no sudo); the fix is the CMake flag",
     "fix": "drop the pip install; use -DGMX_BUILD_MANUAL=OFF"},
    {"id": "no_docs_cmake_edit", "forbid": r"docs/manual/CMakeLists\.txt",
     "why": "editing GROMACS's docs/manual/CMakeLists.txt diverges from upstream", "fix": "use -DGMX_BUILD_MANUAL=OFF instead"},
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
    def workload_gromacs_recipe(variant: str = "") -> dict:
        """Predictor: the GROMACS build/run recipe dftracer-agents verified (modules, CMake flags incl. -DGMX_BUILD_MANUAL=OFF,
        HDF5 1.14 from-source steps, configure/build/smoke commands, notes) as structured JSON. Use before configuring or
        running GROMACS. variant: optional variant name (none defined yet). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_gromacs_check(commands: list) -> dict:
        """Validator: check a proposed GROMACS recipe or command list against the skill's rules (manual/help off, CMake 3.28+,
        no system HDF5 1.10.x, no sphinx install, no docs CMake edits). commands: list of shell lines (or one newline-separated
        string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

"""VPIC-Kokkos (TauferLab/vpic-kokkos, C++/CMake, Kokkos OpenMP, per-input deck compiled with <build>/bin/vpic deck.cxx):
deterministic steps - CMake configure args, the run command line, a sized I/O-enabled copy of the short_pulse deck and
a check of a build tree."""
import json
import re
from pathlib import Path

CRAY_BIN = "/opt/cray/pe/craype/2.7.35/bin"


def _int(v, d):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return d


def cmake_args(cc="", cxx="", dftracer_cmake_dir="", dftracer_include="", hdf5_root=""):
    cc = cc or f"{CRAY_BIN}/cc"
    cxx = cxx or f"{CRAY_BIN}/CC"
    args = [f"-DCMAKE_C_COMPILER={cc}", f"-DCMAKE_CXX_COMPILER={cxx}", "-DBUILD_INTERNAL_KOKKOS=ON",
            "-DENABLE_KOKKOS_OPENMP=ON", "-DENABLE_KOKKOS_CUDA=OFF", "-DVPIC_USE_LEGACY_PARTICLE_ARRAY=ON",
            "-DCMAKE_BUILD_TYPE=Release"]
    if hdf5_root:
        args += [f"-DHDF5_ROOT={hdf5_root}", "-DHDF5_NO_FIND_PACKAGE_CONFIG_FILE=ON"]
    if dftracer_cmake_dir:
        args.append(f"-Ddftracer_DIR={dftracer_cmake_dir}")
    if dftracer_include:
        args.append(f"-DCMAKE_CXX_FLAGS=-I{dftracer_include}")  # one token, no spaces
    return {"status": "ok", "args": args,
            "notes": ["mpicxx from the MCP env fails (crayCC not found): use the Cray cc/CC wrappers",
                      "compile a deck with <build>/bin/vpic deck.cxx, NOT install/bin/vpic (its paths point "
                      "to install/deck and install/src which do not exist)",
                      "annotated tree: add find_package(dftracer), libdftracer_core + rpath to "
                      "VPIC_CXX_LIBRARIES and dftracer::dftracer_core to target_link_libraries(vpic)",
                      "write_functions branch (HDF5): build HDF5 1.14 parallel from source with the session tools, "
                      "pass hdf5_root; annotate with compile flag -DVPIC_ENABLE_HDF5; put <hdf5>/lib on "
                      "LD_LIBRARY_PATH at run time (vpic_run_command hdf5_lib_dir)"]}


def run_command(deck_binary, ranks="4", threads="24", dftracer_lib_dir="", hdf5_lib_dir=""):
    ranks, threads = _int(ranks, 4), _int(threads, 24)
    if not str(deck_binary).startswith("/"):
        return {"status": "error", "error": "deck_binary must be an absolute path (scheduler shells have a different cwd/PATH)"}
    ld = "/opt/cray/pe/lib64:/opt/cray/pe/papi/default/lib64"
    for extra in (dftracer_lib_dir, hdf5_lib_dir):
        if extra:
            ld += f":{extra}"
    cmd = (f"flux run -N1 -n{ranks} -c{threads} env GLIBC_TUNABLES=glibc.rtld.optional_static_tls=1000000 "
           f"LD_LIBRARY_PATH={ld} OMP_PROC_BIND=spread OMP_PLACES=cores {deck_binary} --tpp {threads}")
    return {"status": "ok", "command": cmd}


def _sub(text, name, value):
    m = re.search(r"^(\s*(?:(?:double|int)\s+)?" + name + r"\s*=\s*)([^;/\n]*?)(\s*;.*)$", text, re.M)
    if not m:
        return text, None
    return text[:m.start()] + m.group(1) + str(value) + m.group(3) + text[m.end():], [m.group(2).strip(), str(value)]


def deck_prepare(src_deck, out_deck, nx, nz, nppc, num_step, field_interval, restart_interval, energies_interval,
                 enable_particle_dump):
    src = Path(src_deck)
    if not src.is_file():
        return {"status": "error", "error": f"no deck at {src_deck}"}
    t, changed = src.read_text(), {}
    vals = {"nx": nx, "nz": nz, "nppc": nppc, "num_step": num_step, "field_interval": field_interval,
            "restart_interval": restart_interval, "quota_check_interval": field_interval,
            "energies_interval": energies_interval}
    for k, v in vals.items():
        t, ch = _sub(t, k, _int(v, 0))
        if ch:
            changed[k] = ch
    t, ch = _sub(t, "particle_interval", "2*field_interval")
    if ch:
        changed["particle_interval"] = ch
    if str(enable_particle_dump).strip().lower() not in ("", "0", "false", "no", "off"):
        lines = t.split("\n")
        for i, ln in enumerate(lines):
            if ln.strip() == "#if 0" and any("dump_particles" in x or "species_t * sp" in x for x in lines[i:i + 12]):
                lines[i] = ln.replace("#if 0", "#if 1")
                changed["particle_dump_block"] = [f"line {i + 1}: #if 0", "#if 1"]
                break
        t = "\n".join(lines)
    Path(out_deck).parent.mkdir(parents=True, exist_ok=True)
    Path(out_deck).write_text(t)
    return {"status": "ok", "out_deck": str(out_deck), "changed": changed,
            "not_found": [k for k in vals if k not in changed]}


def build_check(build_dir):
    b = Path(build_dir)
    cache = b / "CMakeCache.txt"
    if not cache.is_file():
        return {"status": "fail", "faults": [{"what": f"no CMakeCache.txt in {build_dir}", "fix": "configure with vpic_cmake_args"}]}
    faults = []
    m = re.search(r"^CMAKE_BUILD_TYPE:\w+=(.*)$", cache.read_text(), re.M)
    if not m or m.group(1).strip() != "Release":
        faults.append({"what": f"CMAKE_BUILD_TYPE={m.group(1) if m else 'unset'}", "fix": "-DCMAKE_BUILD_TYPE=Release (the deck wrapper adds -O3 only for Release; otherwise ~25x slower)"})
    if not (b / "bin" / "vpic").is_file():
        faults.append({"what": "bin/vpic missing", "fix": "build the tree; compile decks with <build>/bin/vpic, not install/bin/vpic"})
    if not (b / "libvpic.a").is_file():
        faults.append({"what": "libvpic.a missing in the build dir", "fix": "finish the build"})
    return {"status": "fail" if faults else "pass", "faults": faults}


# ---------------------------------------------------------------- v3: recipe + rules merged from dftracer-agents' workload-vpic-kokkos
CAP = "workload_vpic_kokkos"

RECIPE = {
    "app": "VPIC-Kokkos",
    "repos": {"devel": "TauferLab/vpic-kokkos devel (write_functions adds HDF5, excludes ghost cells)", "lanl": "github.com/lanl/vpic-kokkos"},
    "build_system": "cmake (two-stage: CMake builds libvpic.a + a vpic deck-compiler wrapper; each deck .cxx compiled into its own executable)",
    "backend": "CPU-only by default (Kokkos Serial+OpenMP, bundled Kokkos submodule): do not assume HIP/CUDA offload because the node has GPUs",
    "cmake_flags": ["-DBUILD_INTERNAL_KOKKOS=ON", "-DENABLE_KOKKOS_OPENMP=ON", "-DENABLE_KOKKOS_CUDA=OFF", "-DVPIC_USE_LEGACY_PARTICLE_ARRAY=ON",
                    "-DCMAKE_BUILD_TYPE=Release", "Cray cc/CC as CMAKE_C/CXX_COMPILER (see vpic_cmake_args)"],
    "deck_compile": "<build>/bin/vpic deck.cxx (invokes the MPI C++ compiler with deck + deck/main.cc + deck/wrapper.cc, links libvpic.a); "
                    "install/bin/vpic points at missing install/deck and install/src",
    "annotated_install": [
        "symlink install_ann/deck -> annotated deck/ sources (main.cc/wrapper.h install to share/vpic/, not always deck/)",
        "symlink install_ann/src -> annotated src/ (header search path of the deck compile)",
        "symlink install_ann/libvpic.a at the install root if the wrapper's -L list lacks lib/",
        "add -I<dftracer include> -L<dftracer lib> -Wl,-rpath,<dftracer lib> -ldftracer_core to the generated vpic wrapper script "
        "(VPIC's CMake has no dftracer awareness)",
    ],
    "io_layer": "src/util/checkpt/checkpt_io.cc (CheckPtIO), not FileIO.h (header-only template, skipped by the cost filter); main loop "
                "vpic_simulation::advance() in src/vpic/advance.cc, called from deck/main.cc while (simulation->advance())",
    "annotate": {
        "functions": "DFTRACER_CPP_FUNCTION() + DFTRACER_CPP_FUNCTION_UPDATE(\"comp\", ...) at the top of every non-main function (RAII, no END)",
        "main": "DFTRACER_CPP_INIT + DFTRACER_CPP_REGION_START(main) at entry; DFTRACER_CPP_REGION_END(main) + DFTRACER_CPP_FINI() before the single return",
        "region_arg": "bare identifier (token-pasted ##name), never a string literal",
        "comp_labels": "a name-based comp= is not evidence: dump_energies (comp=io) is 99.7% MPI_Allreduce",
        "files_devel": ["src/vpic/dump.cc", "src/vpic/vpic.cc", "src/util/checkpt/checkpt.cc"],
    },
    "decks": {
        "smoke": "sample/Weibel/Weibel.cxx: nppc=200, nx=64, ny=nz=1 (12,800 particles), num_step=1000, topology_x = nproc(): < 1 min at 4-16 ranks",
        "io_sized": "sample/short_pulse.cxx via vpic_deck_prepare: 640x640, nppc 100, 80 steps, ~5 GB in ~12 s on 1 node (4 ranks)",
        "portability_test_xN-yM-zK": "FULL PRODUCTION SCALE (~80M particles/rank, 5302 steps); requires exactly N*M*K ranks",
        "benchmark.cxx": "#define ENABLE_OUTPUT 0 compiles all dumps out: flip to 1 and relink the deck (~1 min) to measure I/O",
    },
    "diagnosis": {
        "weibel_16r_1n": "MPI-communication-bound: 82% of advance() is MPI_Allreduce (dump_energies, 1.65 s / 3008 calls) unioned with "
                         "boundary_p_kokkos (MPI_Wait); Kokkos compute ~18%; POSIX/STDIO < 0.2%",
        "benchmark_io_128r_8n": "ENABLE_OUTPUT=1: 340.85M POSIX ops, 325.0 MB, 196.9 MB/s, 1.65 s I/O of 210.2 s: small-I/O pattern but negligible",
    },
    "optimization": {
        "patch1_species": "IMPLEMENTED 2026-07-14: energy_p_local() + one mp_allsum_d for all species in dump_energies: energies byte-identical, "
                          "no measurable time change on 2 species (124.29 s vs 124.03 s)",
        "patch1_field": "REVERTED 2026-07-14: growing field_advance_kernels_t segfaults ~35 s into every 128-rank run",
        "patch2": "MPI_Iallreduce for the coalesced energy reduction (Hoefler SC 2007): next to try, without growing the struct",
        "cheap": "check OMP_NUM_THREADS/OMP_PROC_BIND/OMP_PLACES at runtime",
        "not_worth": ["pinned memory / cross-NUMA (MI300A unified HBM)", "flux cpu-affinity (no effect, twice)", "I/O/ROMIO/Lustre striping"],
    },
    "variants": {},
}

RULES = [
    {"id": "release_build", "require": r"-DCMAKE_BUILD_TYPE=Release\b", "when": r"\bcmake\b.*-D",
     "why": "the deck wrapper adds -O3 only for Release (session_configure forces RelWithDebInfo: decks ~25x slower)",
     "fix": "-DCMAKE_BUILD_TYPE=Release (vpic_cmake_args)"},
    {"id": "kokkos_openmp", "require": r"-DENABLE_KOKKOS_OPENMP=ON", "when": r"\bcmake\b.*-D",
     "why": "VPIC-Kokkos is built CPU-only with the bundled Kokkos OpenMP backend", "fix": "-DBUILD_INTERNAL_KOKKOS=ON -DENABLE_KOKKOS_OPENMP=ON -DENABLE_KOKKOS_CUDA=OFF"},
    {"id": "no_mpicxx_compiler", "forbid": r"-DCMAKE_CXX_COMPILER=\S*mpicxx",
     "why": "mpicxx from the MCP env fails (crayCC not found)", "fix": "use the Cray CC wrapper (vpic_cmake_args)"},
    {"id": "region_bare_identifier", "forbid": r"DFTRACER_CPP_REGION_(?:START|END)\(\s*\"",
     "why": "REGION_START/END token-paste ##name: a string literal fails with \"expected ';' after expression\"",
     "fix": "DFTRACER_CPP_REGION_START(main) / DFTRACER_CPP_REGION_END(main)"},
    {"id": "no_grow_field_kernels", "forbid": r"field_advance_kernels_t",
     "why": "adding any member to field_advance_kernels_t (even an unused void* pad) segfaults ~35 s into every 128-rank run (2026-07-14)",
     "fix": "do not change that struct; expose a local field-energy variant as a free function dispatched in dump.cc"},
    {"id": "tpp_threads", "require": r"--tpp\s+\d+", "when": r"\.Linux\b",
     "why": "VPIC takes threads via --tpp, not OMP_NUM_THREADS", "fix": "append --tpp <threads> (vpic_run_command)"},
    {"id": "static_tls", "require": r"GLIBC_TUNABLES=glibc\.rtld\.optional_static_tls=", "when": r"\.Linux\b",
     "why": "libsci_cray_mp.so needs the static TLS tunable", "fix": "env GLIBC_TUNABLES=glibc.rtld.optional_static_tls=1000000"},
    {"id": "no_flux_cpu_affinity", "forbid": r"cpu-affinity",
     "why": "flux cpu-affinity had no measurable effect on this system (twice, different workloads)", "fix": "tune with OMP_PLACES/OMP_PROC_BIND"},
]

_DECOMP = re.compile(r"portability_test_x(\d+)-y(\d+)-z(\d+)")
_RANKS = re.compile(r"(?:\s-n\s*|\s-n|--ntasks[= ]|-np\s+)(\d+)")


def _decomposition(commands):
    """Extra check: a portability_test_xN-yM-zK deck run with a rank count other than N*M*K fails 'Bad domain decompostion'."""
    out = []
    for c in commands:
        d, r = _DECOMP.search(c), _RANKS.search(c)
        if d and r:
            need = int(d.group(1)) * int(d.group(2)) * int(d.group(3))
            ok = int(r.group(1)) == need
            out.append({"check": "deck_decomposition", "ok": ok,
                        "detail": "ok" if ok else f"deck needs exactly {need} ranks, command has {r.group(1)}: 'Bad domain decompostion' "
                                                  "(src/grid/partition.cc); these decks are production scale, not smoke decks",
                        "fix": "" if ok else f"run with {need} ranks, or use sample/Weibel/Weibel.cxx for a smoke"})
    return out


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
    def workload_vpic_kokkos_recipe(variant: str = "") -> dict:
        """Predictor: the VPIC-Kokkos recipe as structured JSON: CMake flags (CPU-only Kokkos OpenMP, Release), the two-stage deck
        compile and annotated-install symlinks, I/O layer and annotation rules (bare-identifier REGION macros), deck choice
        (Weibel smoke, sized short_pulse, production portability_test decks, benchmark.cxx ENABLE_OUTPUT), the measured
        MPI-bound diagnosis and optimization history. variant: optional (none defined; any value returns an unknown-variant
        error). Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_vpic_kokkos_check(commands: list) -> dict:
        """Validator: check a proposed VPIC-Kokkos command list against the rules (Release build, Kokkos OpenMP, no mpicxx
        compiler, bare-identifier REGION macros, never grow field_advance_kernels_t, --tpp and the static TLS tunable on deck
        runs, no flux cpu-affinity, portability_test deck rank count = N*M*K). commands: list of shell lines (or a
        newline-separated string / JSON text). Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        res = _check(commands)
        if res["status"] == "inconclusive":
            return res
        res["checks"] += _decomposition(_commands(commands))
        res["status"] = "pass" if all(c["ok"] for c in res["checks"]) else "fail"
        return res

    @mcp.tool()
    def vpic_cmake_args(cc: str = "", cxx: str = "", dftracer_cmake_dir: str = "", dftracer_include: str = "",
                        hdf5_root: str = "") -> str:
        """Configure args that build VPIC-Kokkos fast on a Cray system (Cray cc/CC wrappers, Kokkos OpenMP, Release).

        Use for every configure (smoke and annotated). Release is mandatory: VPIC's deck wrapper adds -O3 only for
        Release and session_configure forces RelWithDebInfo (decks ~25x slower). dftracer_cmake_dir/dftracer_include:
        for the annotated tree. hdf5_root: parallel HDF5 install for the write_functions branch. Returns JSON
        {status, args:[...], notes}.
        """
        return json.dumps(cmake_args(cc, cxx, dftracer_cmake_dir, dftracer_include, hdf5_root))

    @mcp.tool()
    def vpic_run_command(deck_binary: str, ranks: str = "4", threads: str = "24", dftracer_lib_dir: str = "",
                         hdf5_lib_dir: str = "") -> str:
        """flux run line for one node, ranks x threads, for a compiled VPIC deck (<deck>.Linux).

        Use to run the deck untraced or traced. VPIC takes threads via --tpp (not OMP_NUM_THREADS); libsci_cray_mp.so
        needs the static TLS tunable. deck_binary must be absolute. Returns JSON {status, command}.
        """
        return json.dumps(run_command(deck_binary, ranks, threads, dftracer_lib_dir, hdf5_lib_dir))

    @mcp.tool()
    def vpic_deck_prepare(src_deck: str, out_deck: str, nx: str = "640", nz: str = "640", nppc: str = "100",
                          num_step: str = "80", field_interval: str = "20", restart_interval: str = "40",
                          energies_interval: str = "10", enable_particle_dump: str = "true") -> str:
        """Write a copy of sample/short_pulse.cxx sized for 1 node (4 ranks x 24 threads, ~5 GB output in ~12 s) with all
        I/O on: field/hydro dumps, particle dump (the '#if 0' block), restart, energies. The original is not changed.

        Use to make the deck of the baseline and optimized runs. Returns JSON {status, out_deck, changed, not_found}.
        """
        return json.dumps(deck_prepare(src_deck, out_deck, nx, nz, nppc, num_step, field_interval, restart_interval,
                                       energies_interval, enable_particle_dump))

    @mcp.tool()
    def vpic_build_check(build_dir: str) -> str:
        """Check a configured/built VPIC tree: CMAKE_BUILD_TYPE=Release (so -O3 reaches decks), bin/vpic, libvpic.a.

        Use after configure/build and before compiling a deck. Returns JSON {status: pass|fail, faults:[{what, fix}]}.
        """
        return json.dumps(build_check(build_dir))

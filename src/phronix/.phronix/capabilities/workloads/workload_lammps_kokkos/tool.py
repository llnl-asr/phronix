"""workload_lammps_kokkos: the LAMMPS + KOKKOS/HIP (lammps/lammps on AMD MI300A APUs, Cray PE, Flux, ROCm 7.x) build,
annotation and run recipe that dftracer-agents' workload-lammps-kokkos skill verified, as structured data (predictor), and a
deterministic check of a proposed recipe or command list against that skill's rules (validator). Nothing here runs."""
import json
import re

CAP = "workload_lammps_kokkos"

# ---------------------------------------------------------------- what the skill knows (data only)
RECIPE = {
    "app": "LAMMPS (KOKKOS package, HIP)",
    "repo": "https://github.com/lammps/lammps",
    "build_system": "cmake (preset cmake/presets/elcapitan_kokkos.cmake)",
    "languages": ["C++", "HIP"],
    "systems": ["tuolumne (MI300A, Cray PE, Flux, ROCm 7.x)"],
    "configure": [
        "cmake -C <src>/cmake/presets/elcapitan_kokkos.cmake -DPKG_KOKKOS=ON -DBUILD_MPI=ON <src>/cmake "
        "(preset sets Kokkos_ENABLE_HIP, Kokkos_ARCH_AMD_GFX942_APU, CMAKE_CXX_COMPILER=hipcc, FFT_KOKKOS=HIPFFT, Cray MPICH link line; "
        "Kokkos_ENABLE_OPENMP stays OFF)",
    ],
    "link_fix": [
        "-L<mpich-9.0.1>/ofi/crayclang/20.0/lib -lmpi",
        "-L/opt/cray/pe/mpich/9.1.0/gtl/lib -lmpi_gtl_hsa -Wl,-rpath,/opt/cray/pe/mpich/9.1.0/gtl/lib",
    ],
    "gtl_probe": "for v in /opt/cray/pe/mpich/*/gtl/lib/libmpi_gtl_hsa.so; do echo \"$v -> $(objdump -p $v | grep -o 'libamdhip64.so.[0-9]')\"; done",
    "build": ['flux run -N1 -n1 -c 96 bash -c "cd <build> && make -j 96"   # on a compute node: ~514 objects, hipcc two-pass codegen'],
    "env": {"HSA_XNACK": "1", "MPICH_GPU_SUPPORT_ENABLED": "1"},
    "run": {
        "input": "copy bench/in.lj and edit 'run' (hardcoded; cannot be overridden with -var); atoms = 4*(20x)(20y)(20z) via -var x/y/z",
        "launch": "flux run -N2 -n8 -g1 -c22 env HSA_XNACK=1 MPICH_GPU_SUPPORT_ENABLED=1 <build>/lmp -k on g 1 -sf kk -in in.lj -var x 4 -var y 4 -var z 4",
        "measured": "1,024,000 atoms x 1000 steps on 2 nodes x 4 GPUs (8 ranks): 4.2 s loop time, 241.8 Matom-step/s",
    },
    "annotate": {
        "main_cpp": "rename LAMMPS' file-local static finalize() (e.g. lmp_local_finalize) at its definition and 7 call sites; INIT right after MPI_Init; REGION_END + FINI before finalize() on all 7 exits (6 catch blocks + fall-through), by hand",
        "scope": "50 files (37 core + 13 KOKKOS): main/lammps/input/run/finish/update/output/thermo/timer, domain/atom/atom_vec*/comm*/irregular, neighbor/neigh_list/nbin*/npair, integrate/verlet/modify/fix/fix_nve, force/pair/pair_lj_cut, read_*/write_*/dump*, and *_kokkos.cpp counterparts; never lib/kokkos/",
        "exclude_functions": ["closest_image", "remap", "remap_near", "unmap", "minimum_image", "lattice2box", "create_atom"],
        "add_back": ["CommKokkos::forward_comm", "CommKokkos::reverse_comm", "NeighborKokkos::build",
                     "ModifyKokkos::initial_integrate", "ModifyKokkos::final_integrate"],
        "post_checks": ["strip macros inside KOKKOS_INLINE_FUNCTION / KOKKOS_FUNCTION bodies",
                        "include line below the first macro line on every file (move it after the FIRST #include; neighbor.cpp)",
                        "read the skipped list, not only the annotated count"],
    },
    "variants": {},
    "notes": [
        "cray-mpich/9.0.1 GTL needs libamdhip64.so.6 but ROCm 7.x ships .so.7: binary fails to start (pristine too)",
        "dropping -lmpi_gtl_hsa -> 'cxil_map: write error' (XNACK APU: all buffers device-accessible); '-pk kokkos ... comm host' does not avoid it",
        "lattice2box and create_atom: 2,721,792 and 1,024,000 events (89% of app events at 1M atoms)",
        "tracing overhead: loop 4.23 s traced vs 0.94 s DFTRACER_ENABLE=0 (~4.5x), final thermo bit-identical",
        "PAPI_TOT_CYC,PAPI_TOT_INS,PAPI_FP_OPS,PAPI_FP_INS multiplex 0 (read it from the compute-node trace)",
    ],
}

RULES = [
    {"id": "no_kokkos_openmp", "forbid": r"-DKokkos_ENABLE_OPENMP=(ON|on|On|1|TRUE|true)",
     "why": "Kokkos_ENABLE_OPENMP is incompatible with hipcc's second pass", "fix": "keep Kokkos_ENABLE_OPENMP=OFF"},
    {"id": "elcapitan_preset", "require": r"elcapitan_kokkos\.cmake", "when": r"\bcmake\b.*PKG_KOKKOS",
     "why": "the El Capitan preset (same MI300A APU) sets HIP, GFX942_APU arch, hipcc, HIPFFT and the Cray MPICH link line",
     "fix": "cmake -C <src>/cmake/presets/elcapitan_kokkos.cmake -DPKG_KOKKOS=ON -DBUILD_MPI=ON"},
    {"id": "no_extra_packages", "forbid": r"-DPKG_(MOLECULE|KSPACE)=ON",
     "why": "in.lj needs no extra packages", "fix": "drop MOLECULE/KSPACE"},
    {"id": "gtl_kept", "require": r"-lmpi_gtl_hsa", "when": r"-lmpi\b",
     "why": "without GPU-aware MPI the run dies with 'cxil_map: write error' on the XNACK APU",
     "fix": "link -lmpi_gtl_hsa from the GTL whose libamdhip64 soname matches ROCm (mpich 9.1.0 for ROCm 7.x)"},
    {"id": "gtl_soname", "forbid": r"mpich/9\.0\.1/gtl",
     "why": "cray-mpich/9.0.1's GTL needs libamdhip64.so.6; ROCm 7.x ships .so.7: 'error while loading shared libraries: libamdhip64.so.6'",
     "fix": "take only the GTL from /opt/cray/pe/mpich/9.1.0/gtl/lib (keep libmpi from the MPI you compiled against)"},
    {"id": "xnack", "require": r"HSA_XNACK=1", "when": r"\blmp\b.*-k on",
     "why": "Kokkos_ARCH_AMD_GFX942_APU needs XNACK for host allocations from device", "fix": "export HSA_XNACK=1"},
    {"id": "gpu_support", "require": r"MPICH_GPU_SUPPORT_ENABLED=1", "when": r"\blmp\b.*-k on",
     "why": "GPU-aware Cray MPICH must be enabled at run time", "fix": "export MPICH_GPU_SUPPORT_ENABLED=1"},
    {"id": "gpus_per_rank", "forbid": r"-g\s*1\b.*-k on g [2-9]",
     "why": "'Requested GPU with id '3' but only 1GPU(s) available!': -k on g N must match GPUs per rank",
     "fix": "use -k on g 1 under flux run -g1"},
    {"id": "hot_exclusions", "require": r"lattice2box", "when": r"clang_annotate_(file|project)",
     "why": "per-atom/per-lattice-point functions (domain remap/closest_image/..., lattice2box, create_atom) bury the timestep signal",
     "fix": "exclude_functions=[closest_image, remap, remap_near, unmap, minimum_image*, lattice2box, create_atom]"},
    {"id": "no_lib_kokkos", "forbid": r"clang_annotate_\w+\(.*lib/kokkos",
     "why": "lib/kokkos is not annotated: brahma and rocprofiler capture MPI/POSIX/STDIO and GPU layers", "fix": "leave lib/kokkos/ alone"},
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
    def workload_lammps_kokkos_recipe(variant: str = "") -> dict:
        """Predictor: the LAMMPS+KOKKOS/HIP recipe dftracer-agents verified on MI300A - elcapitan preset configure, the GTL/ROCm
        soname link fix, compute-node build, HSA_XNACK/MPICH_GPU_SUPPORT_ENABLED env, the 2-node -k on g 1 launch, in.lj sizing,
        and annotation scope/exclusions/add-backs/main.cpp finalize rename. variant: optional (none defined).
        Returns {status, capability, recipe, rules}."""
        return _recipe(variant)

    @mcp.tool()
    def workload_lammps_kokkos_check(commands: list) -> dict:
        """Validator: check a proposed LAMMPS-KOKKOS recipe or command list against the skill's rules (no Kokkos OpenMP,
        elcapitan preset, no extra packages for in.lj, GTL kept and from the matching mpich, HSA_XNACK=1,
        MPICH_GPU_SUPPORT_ENABLED=1, -k on g matches -g, hot setup functions excluded, lib/kokkos not annotated).
        commands: list of shell lines / tool calls (or one newline-separated string / JSON text).
        Returns {status: pass|fail|inconclusive, checks: [{check, ok, detail, fix}]}."""
        return _check(commands)

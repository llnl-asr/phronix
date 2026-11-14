"""iPIC3D (KTH-HPC/iPIC3D, 3D particle-in-cell plasma code, C++/CMake, MPI + parallel HDF5/VTK I/O): everything we
learnt running it, as deterministic steps - MPI topology for a rank count, a run-ready input deck (copy) and its check,
the CMake configure arguments that build, a check (and an applier) for the known source fixes, and which Rabbit storage
each of its output kinds goes to."""
import json
import os
import re
from pathlib import Path

KEY_RX = r"^(\s*{key}\s*=\s*)([^#\n]*?)(\s*(#.*)?)$"
NFS_TYPES = ("nfs", "nfs4")


def _get(text, key):
    m = re.search(KEY_RX.format(key=re.escape(key)), text, re.M)
    return m.group(2).strip() if m else None


def _set(text, key, value):
    rx = re.compile(KEY_RX.format(key=re.escape(key)), re.M)
    if rx.search(text):
        return rx.sub(lambda m: f"{m.group(1)}{value}{m.group(3)}", text, count=1)
    return text.rstrip("\n") + f"\n{key} = {value}\n"


def _where(path):
    """'pfs' for a site parallel filesystem (/p/... - Lustre, or VAST even though it is mounted over NFS), 'rabbit' for
    a Rabbit mount, 'nfs-home' for the NFS home/project space (slow for a run's output), else the fs type."""
    p = os.path.abspath(os.path.expandvars(os.path.expanduser(path)))
    if p.startswith("/mnt/nnf/") or "$DW_JOB_" in path:
        return "rabbit"
    if p.startswith("/p/"):
        return "pfs"
    t = _fstype(p)
    return "nfs-home" if t in NFS_TYPES else t


def _fstype(path):
    """Filesystem type that holds `path` (its nearest existing parent), from /proc/mounts."""
    p = Path(os.path.abspath(os.path.expandvars(os.path.expanduser(path))))
    while not p.exists() and p != p.parent:
        p = p.parent
    real, best = str(p.resolve()), ("", "")
    try:
        for ln in open("/proc/mounts"):
            parts = ln.split()
            if len(parts) > 2 and (real == parts[1] or real.startswith(parts[1].rstrip("/") + "/")) and len(parts[1]) >= len(best[0]):
                best = (parts[1], parts[2])
    except OSError:
        pass
    return best[1]


def topology(ranks, nxc, nyc, nzc):
    """XLEN x YLEN x ZLEN == ranks, each dividing its cell count; least halo surface per subdomain wins."""
    cands = []
    for x in range(1, ranks + 1):
        if ranks % x or nxc % x:
            continue
        for y in range(1, ranks // x + 1):
            if (ranks // x) % y or nyc % y:
                continue
            z = ranks // (x * y)
            if nzc % z:
                continue
            a, b, c = nxc / x, nyc / y, nzc / z
            cands.append(((a * b + b * c + a * c), -x, -y, (x, y, z)))
    if not cands:
        return {"status": "error", "error": f"no XLEN*YLEN*ZLEN = {ranks} divides the grid {nxc}x{nyc}x{nzc}: change the rank "
                                           "count or the cell counts (each must be divisible by its XLEN/YLEN/ZLEN)"}
    cands.sort()
    x, y, z = cands[0][3]
    return {"status": "ok", "XLEN": x, "YLEN": y, "ZLEN": z, "cells_per_rank": [nxc // x, nyc // y, nzc // z],
            "alternatives": [list(c[3]) for c in cands[1:4]]}


def check_input(text, ranks):
    faults, notes = [], []
    lens = [_get(text, k) for k in ("XLEN", "YLEN", "ZLEN")]
    cells = [_get(text, k) for k in ("nxc", "nyc", "nzc")]
    try:
        x, y, z = (int(float(v)) for v in lens)
        if x * y * z != ranks:
            faults.append({"what": f"XLEN*YLEN*ZLEN = {x}*{y}*{z} = {x * y * z}, but the job runs {ranks} ranks",
                           "fix": "ipic3d_topology(ranks, nxc, nyc, nzc), then ipic3d_input with that rank count "
                                  "(else: 'N processes cant be mapped into X x Y x Z matrix')"})
        cx, cy, cz = (int(float(v)) for v in cells)
        for n, c, l in (("x", cx, x), ("y", cy, y), ("z", cz, z)):
            if c % l:
                faults.append({"what": f"n{n}c={c} is not divisible by {n.upper()}LEN={l}", "fix": "pick a topology that divides the grid"})
    except (TypeError, ValueError):
        faults.append({"what": "XLEN/YLEN/ZLEN or nxc/nyc/nzc missing or not numbers", "fix": "start from a deck in inputfiles/"})
    for key in ("SaveDirName", "RestartDirName"):
        d = _get(text, key)
        if not d:
            faults.append({"what": f"{key} is missing", "fix": f"set {key} to a directory on the parallel filesystem"})
        elif not os.path.isabs(os.path.expandvars(d)):
            notes.append(f"{key}={d} is relative: it lands in the run directory")
        elif _where(d) == "nfs-home":
            faults.append({"what": f"{key}={d} is on the NFS home/project space", "fix": "write output to the site parallel "
                           "filesystem (/p/<fs>/<user>/..., see system_<machine>) or a Rabbit mount ($DW_JOB_<name>)"})
        elif d.startswith("/p/") and not os.path.exists("/" + "/".join(Path(d).parts[1:3])):
            faults.append({"what": f"{key}={d}: {'/' + '/'.join(Path(d).parts[1:3])} does not exist on this machine",
                           "fix": "use this machine's parallel filesystem (system_<machine> probe lists them)"})
        elif os.path.isabs(os.path.expandvars(d)) and "$DW_JOB_" not in d and not os.path.isdir(os.path.expandvars(d)):
            faults.append({"what": f"{key}={d} does not exist on disk yet", "fix": "ipic3d_input creates it now; if you "
                           "wrote the deck another way, mkdir -p it before running (H5Fcreate does not create directories: "
                           "'unable to open file ... No such file or directory')"})
    wm = (_get(text, "WriteMethod") or "").split()[0] if _get(text, "WriteMethod") else ""
    if wm not in ("shdf5", "pvtk", "nbcvtk", "phdf5", "pdf5", "H5hut"):
        notes.append(f"WriteMethod={wm or 'unset'} is unusual")
    if wm != "shdf5":
        notes.append(f"WriteMethod={wm}: the HDF5 output path (phdf5.cpp / ParallelIO.cpp HDF5 branch) is not exercised; "
                     "use shdf5 when the run must trace or tune HDF5 I/O")
    return {"status": "fail" if faults else "pass", "faults": faults, "notes": notes}


def cmake_args(hdf5_root, dftracer_cmake_dir="", mpicc="", mpicxx=""):
    a = ["-DUSE_HDF5=ON",                                  # upstream default OFF: find_package(HDF5) never runs
         "-DCMAKE_POLICY_DEFAULT_CMP0074=NEW",             # else HDF5_ROOT is ignored
         f"-DHDF5_ROOT={hdf5_root}", "-DHDF5_PREFER_PARALLEL=ON",
         f"-DCMAKE_CXX_FLAGS=-I{hdf5_root}/include",        # else the system 1.10.5 headers win: version-mismatch abort
         "-DCMAKE_CXX_FLAGS_RELWITHDEBINFO=-O2",            # drop -DNDEBUG: asserts.h only defines builtin_expect without it
         "-DCMAKE_CXX_FLAGS_RELEASE=-O2", "-DCMAKE_BUILD_TYPE=RelWithDebInfo"]
    if mpicc:
        a.append(f"-DMPI_C_COMPILER={mpicc}")
    if mpicxx:
        a.append(f"-DMPI_CXX_COMPILER={mpicxx}")
    if dftracer_cmake_dir:
        a.append(f"-DCMAKE_PREFIX_PATH={dftracer_cmake_dir}")   # else 'Could not find dftracerConfig.cmake'
    return a


def source_check(src):
    root = Path(src)
    cm = root / "CMakeLists.txt"
    pio = root / "inputoutput" / "ParallelIO.cpp"
    if not cm.exists():
        return {"status": "error", "error": f"no CMakeLists.txt in {src}: give the iPIC3D source root"}
    t = cm.read_text(errors="replace")
    fixes = []
    creates = re.search(r"add_library\s*\(\s*hdf5::hdf5", t)
    fixes.append({"fix": "guard hdf5:: target creation", "ok": (not creates) or bool(re.search(r"if\s*\(\s*(NOT\s+)?TARGET\s+hdf5::hdf5", t)),
                  "how": "wrap iPIC3D's add_library(hdf5::hdf5 ...) / hdf5::hdf5_hl in if(NOT TARGET ...) (FindHDF5 already creates them)"})
    blk = re.search(r"target_link_libraries\s*\(\s*iPIC3Dlib([^)]*)\)", t, re.S)
    pub = bool(blk and re.search(r"PUBLIC\s+\$\{HDF5_C_HL_TARGET\}|PUBLIC\s+\$\{HDF5_C_LIBRARIES\}|PUBLIC\s+hdf5", blk.group(1)))
    fixes.append({"fix": "link HDF5 PUBLIC in iPIC3Dlib", "ok": pub,
                  "how": "target_link_libraries(iPIC3Dlib PUBLIC MPI::MPI_CXX PUBLIC ${HDF5_C_HL_TARGET} PUBLIC ${HDF5_C_LIBRARIES}) "
                         "(PRIVATE gives 'undefined reference to H5*' at the executable link)"})
    if pio.exists():
        p = pio.read_text(errors="replace")
        clash = bool(re.search(r"\bsize\s*\(\s*T\s*\(\s*&\s*\)", p)) or bool(re.search(r"(?<![\w.:>])size\s*\(\s*(\w+)\s*\)", p) and "array_size" not in p)
        fixes.append({"fix": "rename free size() to array_size() in ParallelIO.cpp", "ok": not clash,
                      "how": "the free template size(T(&)[n]) clashes with std::size ('call to size is ambiguous'): rename "
                             "its definition and calls to array_size - apply with ipic3d_source_fix(src_dir, apply=true)"})
    annotated = any("DFTRACER_C" in f.read_text(errors="replace") for f in list(root.glob("*.cpp"))[:5] + list((root / "inputoutput").glob("*.cpp")))
    if annotated:
        fixes.append({"fix": "dftracer in CMakeLists (annotated tree)", "ok": "find_package(dftracer" in t,
                      "how": "add find_package(dftracer REQUIRED) and link PUBLIC dftracer_core into iPIC3Dlib; configure with "
                             "-DCMAKE_PREFIX_PATH=<dftracer lib64/cmake/dftracer>"})
    missing = [f for f in fixes if not f["ok"]]
    return {"status": "fail" if missing else "pass", "annotated": annotated, "fixes": fixes}


_DEF_RX = re.compile(r"\bint\s+size\s*\(\s*T\s*\(\s*&\s*\)\s*\[\s*sz\s*\]\s*\)")
_CALL_RX = re.compile(r"(?<![\w.:>])size\s*\(\s*(fieldtags|momentstags)\s*\)")


def source_fix(src, apply=False):
    """Rename the free size(T(&)[sz]) template in inputoutput/ParallelIO.cpp (and its calls) to array_size."""
    pio = Path(src) / "inputoutput" / "ParallelIO.cpp"
    if not pio.exists():
        return {"status": "error", "error": f"no inputoutput/ParallelIO.cpp in {src}: give the iPIC3D source root (or annotated copy)"}
    t = pio.read_text(errors="replace")
    t2, nd = _DEF_RX.subn("int array_size(T(&)[sz])", t)
    t2, nc = _CALL_RX.subn(lambda m: f"array_size({m.group(1)})", t2)
    changed = nd + nc
    if apply and changed:
        pio.write_text(t2)
    return {"status": "ok", "file": str(pio), "definitions": nd, "calls": nc, "applied": bool(apply and changed),
            "note": "already fixed" if not changed else ("applied" if apply else "dry run: pass apply=true to write")}


def rabbit_mapping(nodes, usable):
    """Output kinds of an iPIC3D run -> storage (measured: restart 3.7x and proc 7.1x on Rabbit XFS, VTK 2.8x on shared
    GFS2 vs global Lustre on one node; paper: restart -> XFS, field/moment -> Rabbit Lustre)."""
    usable = set(usable)
    shared = ("gfs2" if "gfs2" in usable and nodes <= 16 else "lustre" if "lustre" in usable else None)
    rows = [{"files": "restart<rank>.hdf (file per process, large sequential)", "set_in": "RestartDirName (OutputWrapperFPP.cpp)",
             "storage": "xfs" if "xfs" in usable else "global-lustre"},
            {"files": "proc<rank>.hdf (file per process)", "set_in": "SaveDirName (OutputWrapperFPP.cpp)",
             "storage": "xfs" if "xfs" in usable else "global-lustre"},
            {"files": "<SimulationName>_*.vtk (one shared file per step, collective MPI-IO, metadata heavy)",
             "set_in": "col->getSaveDirName() at the VTK filename sites in ParallelIO.cpp",
             "storage": {"gfs2": "gfs2 profile=shared (all nodes in ONE chassis: --coral2-chassis=1, <= 16 nodes)",
                         "lustre": "Rabbit lustre (spans chassis)"}.get(shared, "global-lustre")},
            {"files": "settings.hdf, text logs (tiny)", "set_in": "SaveDirName", "storage": "global-lustre"}]
    notes = []
    if nodes > 16 and shared != "lustre":
        notes.append("more than 16 nodes: gfs2 cannot be shared across chassis and Rabbit lustre is not usable - VTK stays on global Lustre")
    return {"status": "ok", "nodes": nodes, "usable": sorted(usable), "mapping": rows, "notes": notes}


def register(mcp):
    @mcp.tool()
    def ipic3d_topology(ranks: int, nxc: int, nyc: int, nzc: int) -> str:
        """MPI decomposition for iPIC3D: XLEN x YLEN x ZLEN equal to `ranks`, each dividing its cell count (nxc, nyc, nzc),
        with the least halo surface per subdomain.

        Use before every run whose rank count differs from the deck's (iPIC3D aborts with "N processes cant be mapped
        into X x Y x Z matrix"). Returns JSON {status, XLEN, YLEN, ZLEN, cells_per_rank, alternatives} or {status:"error"}.
        """
        return json.dumps(topology(int(ranks), int(nxc), int(nyc), int(nzc)))

    @mcp.tool()
    def ipic3d_input(base_inp: str, out_inp: str, ranks: int, save_dir: str = "", restart_dir: str = "",
                     write_method: str = "", ncycles: int = 0) -> str:
        """Write a run-ready COPY of an iPIC3D input deck (the original is never changed): topology for `ranks`, output
        directories, WriteMethod and cycle count set; then check it (ipic3d_input_check). Any save_dir/restart_dir given
        (not a $DW_JOB_ Rabbit mount, which is created by the job) is created on disk now with mkdir -p, since iPIC3D's
        PSKhdf5adaptor/phdf5 never create their own output directory and H5Fcreate aborts with errno=2 if it is missing.

        Use to make the deck of a smoke, baseline or optimized run. base_inp/out_inp: deck paths ($PROJECT_ROOT-relative
        or absolute); save_dir/restart_dir: output dirs on Lustre or a Rabbit mount (blank = keep); write_method: shdf5 to
        exercise HDF5 I/O, pvtk/nbcvtk for VTK (blank = keep); ncycles: 0 = keep. Returns JSON {status, out_inp,
        changed:{key: [old, new]}, created_dirs, check}.
        """
        src = Path(os.path.expandvars(base_inp))
        if not src.exists():
            return json.dumps({"status": "error", "error": f"no input deck {base_inp}"})
        t = src.read_text()
        cells = [_get(t, k) for k in ("nxc", "nyc", "nzc")]
        try:
            topo = topology(int(ranks), *(int(float(c)) for c in cells))
        except (TypeError, ValueError):
            return json.dumps({"status": "error", "error": "the deck has no numeric nxc/nyc/nzc"})
        if topo["status"] != "ok":
            return json.dumps(topo)
        want = {"XLEN": topo["XLEN"], "YLEN": topo["YLEN"], "ZLEN": topo["ZLEN"]}
        if save_dir:
            want["SaveDirName"] = save_dir
        if restart_dir:
            want["RestartDirName"] = restart_dir
        if write_method:
            want["WriteMethod"] = write_method
        if ncycles:
            want["ncycles"] = int(ncycles)
        changed = {}
        for k, v in want.items():
            old = _get(t, k)
            if str(old).split()[0:1] != [str(v)]:
                changed[k] = [old, v]
            t = _set(t, k, v)
        out = Path(os.path.expandvars(out_inp))
        if out.resolve() == src.resolve():
            return json.dumps({"status": "error", "error": "out_inp must differ from base_inp (the original deck is kept)"})
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(t)
        created_dirs = []
        for d in (save_dir, restart_dir):
            if d and "$DW_JOB_" not in d:
                dp = os.path.expandvars(os.path.expanduser(d))
                if os.path.isabs(dp):
                    os.makedirs(dp, exist_ok=True)
                    created_dirs.append(dp)
        return json.dumps({"status": "ok", "out_inp": str(out), "changed": changed, "created_dirs": created_dirs,
                            "check": check_input(t, int(ranks))})

    @mcp.tool()
    def ipic3d_input_check(inp: str, ranks: int) -> str:
        """Check an iPIC3D input deck against a run of `ranks` ranks: topology equals the rank count and divides the grid,
        output dirs set, not on NFS and existing on disk, and whether WriteMethod exercises HDF5 I/O.

        Use right before submitting any iPIC3D run. Returns JSON {status: pass|fail, faults:[{what, fix}], notes}.
        """
        p = Path(os.path.expandvars(inp))
        if not p.exists():
            return json.dumps({"status": "error", "error": f"no input deck {inp}"})
        return json.dumps(check_input(p.read_text(), int(ranks)))

    @mcp.tool()
    def ipic3d_cmake_args(hdf5_root: str, dftracer_cmake_dir: str = "", mpicc: str = "", mpicxx: str = "") -> str:
        """The CMake configure arguments that build iPIC3D with parallel HDF5 1.14 (and dftracer for an annotated tree).

        Use for every configure; after a configure that found the wrong HDF5, delete build/CMakeCache.txt and
        build/CMakeFiles first (the cache keeps HDF5_LIBRARIES). hdf5_root: HDF5 1.14 install prefix (find it with
        session_deps); dftracer_cmake_dir: <dftracer>/lib64/cmake/dftracer for the annotated build. Returns JSON {status, args:[...]}.
        """
        return json.dumps({"status": "ok", "args": cmake_args(hdf5_root, dftracer_cmake_dir, mpicc, mpicxx)})

    @mcp.tool()
    def ipic3d_source_check(src_dir: str) -> str:
        """Check an iPIC3D source tree for the fixes it needs to build here: hdf5:: target guard, HDF5 linked PUBLIC in
        iPIC3Dlib, the size()/std::size clash renamed, and (annotated tree) dftracer in CMakeLists.

        Use before configuring a fresh checkout or an annotated copy. Returns JSON {status: pass|fail, annotated,
        fixes:[{fix, ok, how}]}.
        """
        return json.dumps(source_check(os.path.expandvars(src_dir)))

    @mcp.tool()
    def ipic3d_source_fix(src_dir: str, apply: bool = False) -> str:
        """Apply the deterministic source fix ipic3d_source_check reports for 'call to size is ambiguous': rename the free
        template size(T(&)[sz]) in inputoutput/ParallelIO.cpp and its calls (fieldtags, momentstags) to array_size.

        Use instead of sed/Edit on the tree, on source/ and on the annotated copy. Idempotent. src_dir: iPIC3D source root;
        apply: false = dry run (counts only), true = write. Returns JSON {status, file, definitions, calls, applied, note}.
        """
        return json.dumps(source_fix(os.path.expandvars(src_dir), bool(apply)))

    @mcp.tool()
    def ipic3d_rabbit_mapping(nodes: int, usable_json: str = "[\"xfs\", \"gfs2\", \"lustre\"]") -> str:
        """Which storage each iPIC3D output kind goes to, and where in the code its directory is set: per-process restart/
        proc HDF5 -> Rabbit XFS, the shared VTK -> shared GFS2 (one chassis, <= 16 nodes) or Rabbit Lustre, tiny files ->
        global Lustre - restricted to the Rabbit types that are usable now.

        Use when planning the optimized run. usable_json: types that work now (ropt_alloc_probe_result.usable).
        Returns JSON {status, mapping:[{files, set_in, storage}], notes}.
        """
        return json.dumps(rabbit_mapping(int(nodes), json.loads(usable_json)))

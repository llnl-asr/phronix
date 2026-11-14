"""Tuolumne (LLNL, AMD MI300A, Cray PE, flux, one Rabbit per 16-node chassis) and the systems of its family that share
the software stack (hetchy): the runtime library path a Cray-MPICH binary needs, Rabbit capacity sizing, and a check of
a planned Rabbit job against the rules learnt running on it."""
import glob
import json
import math
import os
import re

GIB = 1024 ** 3


def _vkey(p):
    return [int(x) for x in re.findall(r"\d+", p.split("/papi/")[1].split("/")[0])] or [0]


def runtime_dirs(extra=None):
    """Cray PE runtime dirs that exist here (the PAPI 'default' link, else the newest version), then `extra`."""
    dirs = [d for d in ("/opt/cray/pe/lib64", "/opt/cray/lib64") if os.path.isdir(d)]
    papi = "/opt/cray/pe/papi/default/lib64"
    if not os.path.isdir(papi):
        found = sorted(glob.glob("/opt/cray/pe/papi/*/lib64"), key=_vkey)
        papi = found[-1] if found else ""
    if papi:
        dirs.append(papi)
    return dirs + [e for e in (extra or []) if e]


def capacity(fs_type, nodes, ppn, bytes_per_rank, copies=1, margin=1.25):
    """#DW capacity: per compute node for xfs/gfs2/raw (ppn ranks write there), total for lustre; margin covers
    metadata and repeated iterations (an undersized request ends in ENOSPC or 'Access denied')."""
    per_node = ppn * bytes_per_rank * copies * margin
    need = per_node * (nodes if fs_type == "lustre" else 1)
    gib = max(1, math.ceil(need / GIB))
    return {"status": "ok", "fs_type": fs_type, "capacity": f"{gib}GiB", "scope": "total for the job" if fs_type == "lustre"
            else "per compute node", "bytes_needed": int(need)}


def check_job(nodes, queue, purpose, fs, flags):
    faults, notes = [], []
    fs = [dict(f) for f in fs]
    if purpose == "evidence" and queue != "pbatch":
        faults.append({"what": f"evidence runs for the corpus go on pbatch, not {queue}", "fix": "queue=pbatch"})
    if purpose in ("reproducer", "validation", "smoke") and queue not in ("pdebug", ""):
        notes.append(f"{purpose} runs usually go on pdebug (short); {queue} is fine only if pdebug cannot hold it")
    chassis = -(-nodes // 16)
    for f in fs:
        if f.get("type") == "gfs2" and f.get("profile") == "shared":
            if nodes > 16:
                faults.append({"what": f"shared gfs2 on {nodes} nodes: gfs2 is shared only within one chassis (16 nodes)",
                               "fix": "<= 16 nodes on --coral2-chassis=1, or Rabbit lustre for more"})
        if f.get("type") == "lustre" and f.get("profile") not in (None, "", "default", "shared"):
            faults.append({"what": f"lustre profile={f['profile']}: production systems have only the default profile",
                           "fix": "omit profile= (or profile=default)"})
        if f.get("name") and re.search(r"[A-Z]", f["name"]):
            notes.append(f"the mount env var is DW_JOB_{f['name'].replace('-', '_')} - case-sensitive, use it exactly")
    fl = " ".join(flags)
    if fs and "--coral2-chassis" not in fl:
        faults.append({"what": "a Rabbit job without --coral2-chassis", "fix": f"--coral2-chassis={chassis} (ceil(nodes/16))"})
    for m in re.finditer(r"(?:^|\s)-x\s+([A-Za-z_][A-Za-z0-9_]*)", fl):
        faults.append({"what": f"`-x {m.group(1)}`: -x is --exclusive in flux, so {m.group(1)} becomes the command to run",
                       "fix": f"--env={m.group(1)}"})
    if "--requires=-badrabbit" in fl:
        notes.append("--requires=-badrabbit is redundant: the site plugin already adds 'not badrabbit' to every job")
    if fs and "--exclusive" not in fl and not re.search(r"(?:^|\s)-x(?:\s|$)", fl):
        notes.append("Rabbit jobs are submitted --exclusive")
    return {"status": "fail" if faults else "pass", "chassis": chassis, "faults": faults, "notes": notes}


def register(mcp):
    @mcp.tool()
    def tuolumne_runtime_env(extra_dirs_json: str = "") -> str:
        """LD_LIBRARY_PATH for a Cray-MPICH binary run outside a module-loaded shell (detached submitters, flux batch jobs
        from a bare environment): the Cray PE runtime dirs that exist on this node (PAPI default, else newest), then
        extra dirs (HDF5 lib, dftracer lib64, the app's libs).

        Use for every traced or Rabbit run of a compiled app (else "libmpi_cray.so.12: cannot open shared object file",
        and flux may still report the job COMPLETED). extra_dirs_json: JSON list. Returns JSON {status, dirs,
        LD_LIBRARY_PATH}.
        """
        d = runtime_dirs(json.loads(extra_dirs_json) if extra_dirs_json else None)
        return json.dumps({"status": "ok", "dirs": d, "LD_LIBRARY_PATH": ":".join(d)})

    @mcp.tool()
    def tuolumne_dw_capacity(fs_type: str, nodes: int, ppn: int, bytes_per_rank: int, copies: int = 1,
                             margin: float = 1.25) -> str:
        """The #DW jobdw capacity for a run: xfs/gfs2/raw per compute node (ppn x bytes_per_rank x copies x margin), lustre
        total for the job (x nodes), rounded up to GiB.

        Use whenever a Rabbit filesystem is requested for an app or benchmark. bytes_per_rank: bytes one rank writes
        there; copies: iterations or checkpoints kept. Returns JSON {status, fs_type, capacity, scope, bytes_needed}.
        """
        if fs_type not in ("xfs", "gfs2", "raw", "lustre"):
            return json.dumps({"status": "error", "error": "fs_type must be xfs, gfs2, raw or lustre"})
        return json.dumps(capacity(fs_type, int(nodes), int(ppn), int(bytes_per_rank), int(copies), float(margin)))

    @mcp.tool()
    def tuolumne_check_job(nodes: int, queue: str, purpose: str = "run", filesystems_json: str = "", flags_json: str = "") -> str:
        """Check a planned job on Tuolumne (or a system of its family) against the rules learnt there: queue by purpose
        (evidence -> pbatch, reproducers/validation -> pdebug), shared gfs2 only within one 16-node chassis, Rabbit jobs
        with --coral2-chassis=ceil(nodes/16), only the default Lustre profile, `-x VAR` misuse, redundant
        --requires=-badrabbit, case-sensitive DW_JOB_ names.

        Use before submitting. purpose: run|evidence|reproducer|validation|smoke; filesystems_json: JSON list of {type,
        profile, name}; flags_json: JSON list of the flux options. Returns JSON {status: pass|fail, chassis,
        faults:[{what, fix}], notes}.
        """
        return json.dumps(check_job(int(nodes), queue, purpose, json.loads(filesystems_json) if filesystems_json else [],
                                    json.loads(flags_json) if flags_json else []))

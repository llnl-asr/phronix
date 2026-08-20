"""Where the benchmark puts its data — the parallel filesystem, never ``$HOME``.

A run produces tens of gigabytes: SWE-bench container images, the dataset cache,
per-attempt transcripts and patches, store snapshots. All of it goes on the PFS.

``$HOME`` is NFS-backed, quota-limited and shared, so filling it degrades every
session on the node — and NFS is the wrong substrate for container overlay
storage whatever the space situation. The workspace filesystem is not a fallback
either; it was 95% full when this was set up, against 35P free on lustre.

**There is deliberately no silent fallback.** If no PFS root can be found,
:func:`data_root` raises with the variable to set. A fallback to ``$HOME`` would
work on the machine where it was written and quietly fill somebody's quota
everywhere else — and the failure would surface as an unrelated job dying.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

#: Site PFS roots, most specific first. Each is joined with the username.
_PFS_CANDIDATES = ("/p/lustre5", "/p/lustre4", "/p/lustre3", "/p/lustre2",
                   "/p/lustre1", "/p/vast1")

#: Everything the benchmark writes lives under this, on the PFS.
_SUBDIR = "phronix-bench"


class NoDataRoot(RuntimeError):
    """No parallel filesystem location could be resolved."""


def _username() -> str:
    return (os.environ.get("USER") or os.environ.get("LOGNAME")
            or Path.home().name or "unknown")


def candidates() -> List[Path]:
    user = _username()
    return [Path(base) / user for base in _PFS_CANDIDATES]


def data_root(explicit: Optional[str] = None, create: bool = True) -> Path:
    """The benchmark's data root on the PFS.

    Resolution order: an explicit argument, then ``PHRONIX_BENCH_DATA``, then the
    first writable site PFS path. Never ``$HOME``.
    """
    if explicit:
        root = Path(explicit).expanduser()
    elif os.environ.get("PHRONIX_BENCH_DATA"):
        root = Path(os.environ["PHRONIX_BENCH_DATA"]).expanduser()
    else:
        root = None
        for candidate in candidates():
            if candidate.is_dir() and os.access(candidate, os.W_OK):
                root = candidate / _SUBDIR
                break
        if root is None:
            raise NoDataRoot(
                "no writable parallel-filesystem root found (tried "
                f"{', '.join(str(c) for c in candidates())}). Set PHRONIX_BENCH_DATA "
                "to a path with tens of GB free. Refusing to fall back to $HOME: it "
                "is quota-limited and NFS-backed, and filling it degrades every "
                "session on this node.")

    if _is_under_home(root):
        raise NoDataRoot(
            f"{root} is inside $HOME. The benchmark writes tens of GB — container "
            "images, dataset cache, per-attempt transcripts — and $HOME is "
            "quota-limited, NFS-backed and shared. Point PHRONIX_BENCH_DATA at the "
            "PFS instead.")

    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def _is_under_home(path: Path) -> bool:
    try:
        Path(path).expanduser().resolve().relative_to(Path.home().resolve())
        return True
    except (ValueError, OSError):
        return False


#: Node-local scratch, in preference order. Container images go here, NOT on the
#: PFS — see :func:`image_store`.
_LOCAL_SCRATCH = ("/tmp", "/var/tmp")


def image_store(explicit: Optional[str] = None) -> dict:
    """``--root``/``--runroot`` for podman, on **node-local** disk.

    This is the one thing that does not go on the PFS, and the reason is a hard
    site constraint rather than a preference: **no filesystem on this node
    supports user extended attributes** — not lustre, not the workspace, not even
    ``/dev/shm``. Container image extraction sets xattrs (the SWE-bench images
    carry file capabilities under ``/boot``), so a pull onto any of them fails
    with ``lsetxattr: operation not supported``. The ``vfs`` driver fails
    differently on lustre, with a permission error creating its pivot directory.

    Local ``/tmp`` works, and has hundreds of GB. Images are a *cache* — fully
    regenerable from the registry — so putting them on ephemeral local disk costs
    a re-pull after a reboot and nothing else. Everything that is actual data,
    and that a result depends on, still lives on the PFS via :func:`data_root`.

    Overridable with ``PHRONIX_BENCH_IMAGES`` for a machine where the PFS does
    support xattrs.
    """
    if explicit or os.environ.get("PHRONIX_BENCH_IMAGES"):
        base = Path(explicit or os.environ["PHRONIX_BENCH_IMAGES"]).expanduser()
    else:
        base = None
        for candidate in _LOCAL_SCRATCH:
            path = Path(candidate) / _username()
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            if os.access(path, os.W_OK):
                base = path / "phronix-images"
                break
        if base is None:
            raise NoDataRoot(
                "no writable node-local scratch found (tried "
                f"{', '.join(_LOCAL_SCRATCH)}). Container images cannot live on the "
                "PFS here: no filesystem on this node supports user xattrs, which "
                "image extraction requires. Set PHRONIX_BENCH_IMAGES to a local path.")

    if _is_under_home(base):
        raise NoDataRoot(f"{base} is inside $HOME; image stores are tens of GB")

    storage = base / "storage"
    runroot = base / "run"
    storage.mkdir(parents=True, exist_ok=True)
    runroot.mkdir(parents=True, exist_ok=True)
    return {"root": str(storage), "runroot": str(runroot)}


def supports_xattr(path: Path) -> bool:
    """Whether a plain ``user.*`` xattr can be set under *path*.

    **This does not predict whether image extraction works, and must not be used
    to choose an image store.** It is kept only as a filesystem fact for the
    preflight report.

    Measured here: ``/tmp`` (tmpfs on this site's 4.18 kernel, which predates
    tmpfs user-xattr support) and ``/p/lustre5`` both answer *no* — yet a pull to
    ``/tmp`` succeeds with multi-GB SWE-bench images while a pull to lustre fails
    on a 3 MB alpine. The probe is blind to the thing that differs: extraction
    runs inside podman's user namespace and sets ``trusted.overlay.*``, which the
    overlay driver can do on tmpfs and cannot do on lustre.

    Use :func:`can_store_images` when the answer has to be right.
    """
    import tempfile

    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=str(path)) as handle:
            os.setxattr(handle.name, "user.phronix_probe", b"1")
        return True
    except OSError:
        return False


def can_store_images(path: Path, binary: str = "podman", timeout: int = 300) -> bool:
    """Whether a container image can actually be extracted under *path*.

    The only probe that has ever been right about this is doing it: pull a tiny
    real image into a throwaway store and see. Every cheaper proxy tried here —
    filesystem type, ``user.*`` xattr support, mount options — gave the correct
    answer for the wrong reason on one filesystem and the wrong answer outright
    on another, which is worse than no check at all because it looks authoritative.

    Costs a few megabytes and a few seconds, and is only called from preflight.
    """
    import shutil
    import subprocess
    import tempfile

    resolved = shutil.which(binary)
    if resolved is None:
        return False

    probe = Path(tempfile.mkdtemp(prefix="phronix-imgprobe-", dir=str(path)))
    try:
        result = subprocess.run(
            [resolved, "--root", str(probe / "storage"), "--runroot", str(probe / "run"),
             "--storage-opt", "overlay.ignore_chown_errors=true",
             "pull", "docker.io/library/alpine:latest"],
            capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
    finally:
        import shutil as _shutil

        _shutil.rmtree(probe, ignore_errors=True)


# Kept as an alias so existing callers keep working; images never go on the PFS.
def container_storage(root: Optional[Path] = None) -> dict:
    return image_store()


def run_dir(name: str, root: Optional[Path] = None) -> Path:
    return (Path(root) if root else data_root()) / "runs" / name


def dataset_cache(root: Optional[Path] = None) -> Path:
    path = (Path(root) if root else data_root()) / "dataset"
    path.mkdir(parents=True, exist_ok=True)
    return path


def describe(root: Optional[Path] = None) -> dict:
    """Where everything will go, for the preflight report."""
    try:
        base = data_root(str(root) if root else None, create=False)
    except NoDataRoot as exc:
        return {"error": str(exc)}
    import shutil

    try:
        usage = shutil.disk_usage(base if base.exists() else base.parent)
        free_gb = usage.free / 1e9
    except OSError:
        free_gb = -1.0
    try:
        images = image_store()["root"]
        image_free = shutil.disk_usage(images).free / 1e9
        image_error = ""
    except Exception as exc:
        images, image_free, image_error = "", -1.0, str(exc)

    return {
        "data_root": str(base),
        "runs": str(base / "runs"),
        "dataset": str(base / "dataset"),
        "image_store": images,
        "image_store_free_gb": round(image_free, 1),
        "image_store_error": image_error,
        "free_gb": round(free_gb, 1),
        "enough_space": free_gb < 0 or free_gb > 80,
        # ~3 GB per SWE-bench image; 30 instances needs roughly 90 GB.
        "enough_image_space": image_free < 0 or image_free > 100,
    }

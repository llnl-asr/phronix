"""Verify every integration point before spending money on a real run.

A full four-arm run is hours of wall-clock and a meaningful API bill. Every
external dependency it touches — opencode's non-interactive flags, podman's
ability to pull a SWE-bench image, mini-swe-agent's CLI, the LivAI endpoint — is
a place where a wrong assumption costs the whole run and is discovered at task 1
of arm 3.

So each is checked here, cheaply and in isolation, and each check reports what to
do about a failure rather than just that it failed. Checks are independent: one
failure does not stop the rest, because knowing all four things that are broken
is worth more than knowing the first.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .arms import (DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROVIDER,
                   _needs_key)


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    fix: str = ""
    skipped: bool = False


def _run(command: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    from .arms import tool_path_env

    # stdin closed: opencode blocks forever on an inherited stdin, which turns
    # every check that shells out to it into a timeout with no explanation.
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL,
                          env=tool_path_env(dict(os.environ)))


def check_node() -> Check:
    """node/npx, which `opencode` shells out to and this machine does not ship.

    Checked separately from opencode because the failure mode is identical from
    the outside — the wrapper exits 0 having printed `npx: command not found` to
    stderr — and the fix is entirely different.
    """
    from .arms import tool_path_env

    env = tool_path_env(dict(os.environ))
    found = shutil.which("npx", path=env["PATH"])
    if not found:
        return Check("node/npx", False, detail="npx not on PATH",
                     fix="pip install 'nodejs-bin[cmd]' into the venv you run the "
                         "benchmark from; `opencode` is a wrapper around npx")
    try:
        version = _run(["node", "--version"], timeout=30).stdout.strip()
    except Exception:
        version = "?"
    return Check("node/npx", True, detail=f"{found} (node {version})")


def check_api_key() -> Check:
    key = os.environ.get("OPENAI_API_KEY", "")
    return Check(
        "api key", bool(key),
        detail=("set" if key else "OPENAI_API_KEY is empty"),
        fix="export OPENAI_API_KEY=... (see dftracer-agents/.env.example)")


def check_endpoint(base_url: str = DEFAULT_BASE_URL,
                   model: str = DEFAULT_MODEL) -> Check:
    """Reach the endpoint and confirm the model it will be asked for is served.

    Checked before the run rather than assumed: a model name the endpoint does
    not serve fails identically to a broken agent, and only at the first API
    call of the first task.

    The model is a parameter because it used to be `DEFAULT_MODEL` regardless of
    what the run had actually been given — so a run pointed at another endpoint
    with another model checked for a model neither of them involved, and passed
    or failed for reasons unrelated to the run about to start.
    """
    key = os.environ.get("OPENAI_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    if not key and _needs_key(base_url):
        return Check("endpoint", False, skipped=True,
                     detail="skipped — no API key", fix="set OPENAI_API_KEY first")
    try:
        import urllib.request

        request = urllib.request.Request(
            f"{base_url.rstrip('/')}/models", headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
        served = {m.get("id") for m in payload.get("data", [])}
        present = model in served
        return Check(
            "endpoint", present,
            detail=(f"{base_url} serves {len(served)} models; "
                    f"{model} {'present' if present else 'NOT present'}"),
            fix=(f"pick a served model with --model; nearest matches: "
                 f"{sorted(m for m in served if 'sonnet' in str(m).lower())}"
                 if not present else ""))
    except Exception as exc:
        return Check("endpoint", False, detail=f"{type(exc).__name__}: {exc}",
                     fix="check network access to the gateway and the API key")


def check_opencode(binary: str = "opencode") -> Check:
    path = shutil.which(binary)
    if not path:
        return Check("opencode", False, detail="not on PATH",
                     fix="install opencode, or pass --arms without the opencode arms")
    try:
        result = _run([binary, "--version"], timeout=30)
        version = (result.stdout or result.stderr).strip().splitlines()[:1]
        return Check("opencode", result.returncode == 0,
                     detail=f"{path} {version[0] if version else ''}".strip())
    except Exception as exc:
        return Check("opencode", False, detail=str(exc))


def check_opencode_run(binary: str = "opencode",
                       model: str = f"{DEFAULT_PROVIDER}/{DEFAULT_MODEL}") -> Check:
    """The one that matters: does non-interactive `opencode run` actually work?

    Every opencode arm depends on this exact invocation. It is the most likely
    thing to be wrong — flags change between versions — and the cheapest possible
    task is used so the check costs a few hundred tokens rather than a task.
    """
    if not shutil.which(binary):
        return Check("opencode run", False, skipped=True, detail="skipped — no opencode")
    if not os.environ.get("OPENAI_API_KEY"):
        return Check("opencode run", False, skipped=True, detail="skipped — no API key")
    try:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "hello.txt").write_text("hello\n")
            result = _run([binary, "run", "--dir", tmp, "--auto",
                           "--model", model, "Reply with exactly the word: ok"],
                          timeout=180)
        combined = (result.stdout + result.stderr).lower()
        ok = result.returncode == 0 and "ok" in combined
        return Check("opencode run", ok,
                     detail=(f"exit={result.returncode}, "
                             f"{len(result.stdout)} bytes of output"),
                     fix=("`opencode run` did not behave as expected — check the flag "
                          "syntax for your version and update OpenCodeArm.run_attempt. "
                          f"Output tail: {(result.stderr or result.stdout)[-200:]}")
                     if not ok else "")
    except Exception as exc:
        return Check("opencode run", False, detail=f"{type(exc).__name__}: {exc}")


def check_runtime(preferred: str = "podman") -> Check:
    from .isolation import IsolationError, Runtime

    try:
        from .paths import container_storage

        runtime = Runtime.detect(preferred, storage=container_storage())
    except IsolationError as exc:
        return Check("container runtime", False, detail=str(exc), fix="install podman")
    except Exception as exc:
        return Check("container runtime", False, detail=str(exc),
                     fix="could not prepare the PFS image store")
    if not runtime.available():
        return Check("container runtime", False,
                     detail=f"{runtime.name} found but `{runtime.name} info` failed",
                     fix="on a login node, rootless podman usually needs "
                         "`podman system migrate` once, and subuid/subgid configured")
    store = (runtime.storage or {}).get("root", "default")
    return Check("container runtime", True,
                 detail=f"{runtime.name} at {runtime.binary}, images -> {store}")


def check_image(instance_id: str = "django__django-13551",
                preferred: str = "podman", pull: bool = False) -> Check:
    """Confirm a SWE-bench image name resolves.

    Only inspects by default: pulling one image is a multi-GB download, and a
    preflight that silently costs bandwidth is a preflight people stop running.
    """
    from .isolation import IsolationError, Runtime, image_for

    try:
        from .paths import container_storage

        runtime = Runtime.detect(preferred, storage=container_storage())
    except Exception:
        return Check("swebench image", False, skipped=True, detail="skipped — no runtime")

    image = image_for(instance_id)
    if not pull:
        local = runtime.run(["image", "exists", image], timeout=30)
        return Check("swebench image", True, skipped=True,
                     detail=(f"{image} "
                             f"{'cached locally' if local.returncode == 0 else 'not cached'} "
                             "— pass --pull to verify it downloads"))
    result = runtime.run(["pull", image], timeout=3600)
    return Check("swebench image", result.returncode == 0, detail=image,
                 fix=(f"could not pull {image}: {result.stderr[-200:]}. Check the "
                      "registry is reachable, or set --image-template.")
                 if result.returncode != 0 else "")


def check_mini() -> Check:
    try:
        import minisweagent  # noqa: F401

        return Check("mini-swe-agent", True, detail="importable")
    except ImportError:
        return Check(
            "mini-swe-agent", False, detail="not installed",
            fix="PIP_EXTRA_INDEX_URL= pip install mini-swe-agent  "
                "(the empty extra-index suppresses this machine's unreachable "
                "NVIDIA index; only the `mini` arm needs it)")


def check_dataset(split: str = "lite", cache: Optional[Path] = None) -> Check:
    from .tasks import DatasetUnavailable, load_instances

    try:
        instances = load_instances(split, cache)
        return Check("dataset", True, detail=f"{len(instances)} instances in {split!r}")
    except DatasetUnavailable as exc:
        return Check("dataset", False, detail=str(exc),
                     fix="PIP_EXTRA_INDEX_URL= pip install datasets, then "
                         "`tasks --dataset-cache <dir>` once to cache it locally")


def check_phronix_store() -> Check:
    """The phronix arms need a seedable store and a working MCP surface."""
    try:
        from phronix.layers import bundled_root
        from phronix.permissions import discover_mcp_tool_names

        skills = list((bundled_root() / "skills").glob("*/SKILL.md"))
        tools = discover_mcp_tool_names()
        ok = bool(skills) and bool(tools)
        return Check("phronix store", ok,
                     detail=f"{len(skills)} bundled skills, {len(tools)} MCP tools",
                     fix="the bundled skeleton looks empty — reinstall phronix"
                     if not ok else "")
    except Exception as exc:
        return Check("phronix store", False, detail=f"{type(exc).__name__}: {exc}")


CHECKS: Dict[str, Callable[..., Check]] = {
    "api key": check_api_key,
    "endpoint": check_endpoint,
    "opencode": check_opencode,
    "opencode run": check_opencode_run,
    "container runtime": check_runtime,
    "swebench image": check_image,
    "mini-swe-agent": check_mini,
    "dataset": check_dataset,
    "phronix store": check_phronix_store,
}


def check_data_root(explicit: Optional[str] = None) -> Check:
    """Where bulk data will go, and whether there is room for it.

    Checked first because getting this wrong fills a shared quota, and the
    symptom shows up as somebody else's job dying rather than as a benchmark
    failure.
    """
    from .paths import describe

    info = describe(explicit)
    if "error" in info:
        return Check("data root", False, detail=info["error"],
                     fix="set PHRONIX_BENCH_DATA to a PFS path")
    return Check("data root", bool(info["enough_space"]),
                 detail=f"{info['data_root']} ({info['free_gb']:,.0f} GB free)",
                 fix="under ~80 GB free; SWE-bench images alone need tens of GB"
                 if not info["enough_space"] else "")


def check_image_store() -> Check:
    """Where images go, and whether that filesystem can actually hold them.

    Separate from the data-root check because they deliberately live on different
    filesystems here: no filesystem on this node supports user xattrs, which image
    extraction requires, so images go on node-local disk while all data stays on
    the PFS. Getting this wrong produces a pull that fails five layers in, which
    reads as a network problem rather than a filesystem one.
    """
    from .paths import can_store_images, describe

    info = describe()
    if info.get("image_store_error"):
        return Check("image store", False, detail=info["image_store_error"],
                     fix="set PHRONIX_BENCH_IMAGES to a writable local path")
    store = Path(info["image_store"])

    # An actual pull, not a filesystem proxy: see paths.can_store_images for why
    # every cheaper check was misleading on one filesystem or the other.
    extractable = can_store_images(store)
    space = bool(info.get("enough_image_space"))
    ok = extractable and space
    detail = (f"{store} ({info['image_store_free_gb']:,.0f} GB free, "
              f"extraction={'ok' if extractable else 'FAILS'})")
    if not extractable:
        fix = ("image extraction fails here — a test pull of alpine did not "
               "complete. The PFS cannot hold images on this site; point "
               "PHRONIX_BENCH_IMAGES at node-local scratch.")
    elif not space:
        fix = "under ~100 GB free; SWE-bench images are ~3 GB each"
    else:
        fix = ""
    return Check("image store", ok, detail=detail, fix=fix)


def run_all(pull: bool = False, live: bool = True,
            dataset_cache: Optional[Path] = None,
            data_root: Optional[str] = None,
            base_url: str = DEFAULT_BASE_URL,
            model: str = DEFAULT_MODEL) -> List[Check]:
    """Run every check. *live* enables the ones that cost tokens or bandwidth.

    The endpoint and model are passed through rather than defaulted, so the
    check is about the run that is about to start rather than about whatever the
    package ships as its default.
    """
    checks = [
        check_data_root(data_root),
        check_image_store(),
        check_api_key(),
        check_node(),
        check_opencode(),
        check_runtime(),
        check_mini(),
        check_phronix_store(),
        check_dataset(cache=dataset_cache),
        check_image(pull=pull),
    ]
    if live:
        checks.insert(1, check_endpoint(base_url, model))
        checks.insert(3, check_opencode_run())
    return checks


def render(checks: List[Check]) -> str:
    lines = ["# Benchmark preflight", ""]
    for check in checks:
        mark = "skip" if check.skipped else ("ok  " if check.ok else "FAIL")
        lines.append(f"  [{mark}] {check.name:20s} {check.detail}")
        if check.fix and not check.ok and not check.skipped:
            lines.append(f"         -> {check.fix}")

    blocking = [c for c in checks if not c.ok and not c.skipped]
    lines += ["", (f"{len(blocking)} blocking issue(s); the arms that depend on them "
                   "will fail." if blocking else
                   "All checks passed — a run should get through its integration points.")]
    return "\n".join(lines) + "\n"

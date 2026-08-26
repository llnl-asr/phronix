"""Per-attempt container isolation, and per-run skill-store isolation.

Two independent things have to be isolated, for different reasons:

**The task environment** — one container per *attempt*, from the official
SWE-bench image for that instance. Per attempt rather than per task: a retry that
inherits the previous attempt's filesystem is not an independent try, and
"attempts until pass" would then be measuring recovery from a half-applied patch
rather than a fresh solve.

**The skill store** — one store per *run*, seeded from the bundled framework
skeleton only. This is the opposite requirement: the store deliberately persists
across tasks within a run, because that carry-over is the effect being measured.
What must not leak is anything from a *previous* run.

Rootless podman is the default. On a shared login node the Docker daemon is
commonly restricted or absent, and a benchmark whose isolation depends on a
daemon you cannot start is a benchmark that quietly falls back to something
weaker.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: SWE-bench publishes one image per instance under this namespace.
DEFAULT_IMAGE_TEMPLATE = "docker.io/swebench/sweb.eval.x86_64.{instance}:latest"

#: Instance ids contain `__`, which is not legal in a docker tag; SWE-bench's own
#: convention replaces it with `_1776_`.
def image_for(instance_id: str, template: str = DEFAULT_IMAGE_TEMPLATE) -> str:
    return template.format(instance=instance_id.replace("__", "_1776_").lower())


class IsolationError(RuntimeError):
    """The container runtime could not give us a clean environment."""


def node_of_flux_job(job: str, timeout: int = 60) -> str:
    """The first node allocated to flux *job*, or "" if it cannot be determined.

    Returns "" rather than raising: an unresolvable job should fall back to
    another launcher, not abort a run that could still proceed.
    """
    try:
        result = subprocess.run(
            ["flux", "jobs", "-no", "{nodelist}", job],
            capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return ""
    nodes = result.stdout.strip()
    if result.returncode != 0 or not nodes:
        return ""
    # A nodelist may be a range like "tuolumne[1030,1642]" or "tuolumne1030".
    # Only single-node allocations are supported — containers created by one
    # call must be found by the next — so take the first and let the caller's
    # single-node requirement stand.
    match = re.match(r"^([A-Za-z-]+)\[(\d+)", nodes)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return nodes.split(",")[0].strip()


@dataclass
class Runtime:
    """A container runtime, resolved once and reported explicitly.

    Recorded in the run manifest because "which runtime" changes what the results
    mean — a result produced under a different isolation mechanism is not
    comparable to one produced under this, and a benchmark that silently switches
    is one whose numbers cannot be trusted across runs.

    ``storage`` points the image store at the parallel filesystem. SWE-bench
    images are multi-GB and there are one per instance; podman's default store is
    under ``$HOME``, which is quota-limited, NFS-backed and shared. Passed per
    invocation rather than written into the user's global container config, so the
    benchmark cannot disturb their own setup.
    """

    name: str
    binary: str
    storage: Optional[Dict[str, str]] = None
    #: Command prefix that ships each podman invocation elsewhere, e.g.
    #: ``["ssh", "-n", "node42"]``. Empty means run podman right here.
    launcher: Tuple[str, ...] = ()
    #: Whether the launcher hands its tail to a *remote shell* rather than
    #: exec'ing it directly. ssh does; ``flux run`` does not. When it does, every
    #: argument must be quoted or the shell re-splits it — a test id containing a
    #: space, or ``bash -lc "cd /testbed && pytest"``, would otherwise arrive as
    #: several mangled arguments.
    remote_shell: bool = False

    @classmethod
    def detect(cls, preferred: str = "podman",
               storage: Optional[Dict[str, str]] = None,
               flux_job: str = "", node: str = "") -> "Runtime":
        """Resolve the runtime, and where its commands run.

        Given a flux job and no explicit node, the job's node is looked up and
        reached over **ssh** rather than through ``flux run``. Same allocation,
        same node, none of flux's process-group semantics: ssh returns in under a
        second for a detached container where ``flux run`` blocks indefinitely.
        ``flux run`` remains the fallback for sites where ssh to compute nodes is
        closed.
        """
        order = [preferred] + [r for r in ("podman", "docker") if r != preferred]
        for name in order:
            binary = shutil.which(name)
            if binary:
                # Only podman takes --root/--runroot as global flags; docker's
                # data-root is daemon configuration and cannot be set per call.
                runtime = cls(name=name, binary=binary,
                              storage=storage if name == "podman" else None)
                if node:
                    return runtime.with_remote(node)
                if flux_job:
                    resolved = node_of_flux_job(flux_job)
                    return (runtime.with_remote(resolved) if resolved
                            else runtime.with_flux(flux_job))
                return runtime
        raise IsolationError(
            f"no container runtime found (looked for {', '.join(order)}). "
            "Install podman, or pass --isolation worktree to trade repeatability "
            "for speed — but say so when reporting the numbers.")

    #: Storage options every podman invocation needs on this class of machine.
    #:
    #: ``ignore_chown_errors`` is not optional here. Rootless podman maps the
    #: user into a small subuid range (this account has no /etc/subuid entry at
    #: all), and several SWE-bench images contain files owned by UIDs far outside
    #: it — matplotlib ships build artifacts owned by 197609. Without this the
    #: pull dies with "potentially insufficient UIDs or GIDs available in user
    #: namespace", which reads like a registry problem and is not one.
    #:
    #: The cost is that those files land owned by the container user rather than
    #: their original owner. For a test fixture that is irrelevant; the tests read
    #: them, and nothing in SWE-bench depends on the numeric owner.
    STORAGE_OPTS = ("overlay.ignore_chown_errors=true",)

    def _global_flags(self) -> List[str]:
        if not self.storage:
            return []
        flags = ["--root", self.storage["root"], "--runroot", self.storage["runroot"]]
        for option in self.STORAGE_OPTS:
            flags += ["--storage-opt", option]
        return flags

    def with_remote(self, host: str) -> "Runtime":
        """A copy that runs every podman command over ssh on *host*.

        Preferred over :meth:`with_flux` wherever ssh to the allocated node is
        permitted. ``flux run`` never returns for ``podman run -d`` — flux waits
        on every process in the task cgroup, and the container's supervisor lives
        there — which forced a fire-and-poll dance around container startup. Over
        ssh the same command returns in under a second, and the per-call overhead
        is half of flux's.

        ``-n`` redirects stdin from /dev/null: without it ssh competes with the
        parent for the terminal and can consume input meant for something else.
        """
        return replace(self, launcher=("ssh", "-n", "-o", "BatchMode=yes",
                                       "-o", "StrictHostKeyChecking=no", host),
                       remote_shell=True)

    def with_flux(self, job: str) -> "Runtime":
        """A copy that runs every podman command inside flux allocation *job*.

        This exists because of a hard split on this machine: the SWE-bench
        containers should run on allocated compute nodes, but ``opencode``
        **segfaults** on them (rc=245, core dumped, reproducible on a one-line
        prompt), while running fine on the login node. Neither half can move to
        the other's node, so the work is split across both: the agent stays where
        it runs, and only the container work is shipped into the allocation.

        This is safe because the two halves communicate through the parallel
        filesystem, which both nodes see. The checkout the agent edits lives in
        the run directory on lustre; only ``podman`` itself needs to be where the
        container is.

        Two properties of the allocation make it work. Containers outlive a
        single ``flux run`` — podman is daemonless, so a container created by one
        invocation is found by the next — and a single-node allocation puts every
        invocation on the same node, which is what makes that true. A multi-node
        allocation would scatter the calls and break it; ``-N1 -n1`` keeps each
        call to one task, but the *allocation* must be one node.
        """
        return replace(self, launcher=("flux", "proxy", job, "flux", "run",
                                       "-N1", "-n1"))

    def command_for(self, args: List[str]) -> List[str]:
        """The argv to execute for podman *args*, launcher included."""
        podman = [self.binary, *self._global_flags(), *args]
        if not self.launcher:
            return podman
        if self.remote_shell:
            # One quoted string: ssh joins its tail with spaces and feeds it to a
            # login shell, so anything not quoted here is re-split there.
            return [*self.launcher, " ".join(shlex.quote(part) for part in podman)]
        return [*self.launcher, *podman]

    def run(self, args: List[str], timeout: int = 300,
            check: bool = False) -> subprocess.CompletedProcess:
        """Run a podman command with a timeout that actually bounds it.

        ``subprocess.run(timeout=...)`` does not. On timeout it kills the direct
        child and then calls ``communicate()`` again with NO timeout — so if
        anything still holds the pipe, it blocks forever. Over ssh that is the
        normal case: ssh dies, the remote command keeps the connection's pipe,
        and the call never returns.

        That happened to a ``podman rm`` during container cleanup. The arm's
        thread parked in ``__exit__`` and stopped making progress; the other arm
        carried on, so the run looked alive from the outside while half of it was
        wedged. The 120-second timeout on the call was already there and did
        nothing.

        Here the child gets its own process group, and on timeout the whole
        group is killed and the second wait is bounded too. A command that will
        not die still returns — with a non-zero code and a message saying so,
        which the caller can act on.
        """
        import os
        import signal

        command = self.command_for(args)
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True,
                                   stdin=subprocess.DEVNULL,
                                   start_new_session=True)
        try:
            out, err = process.communicate(timeout=timeout)
            code = process.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                process.kill()
            try:
                out, err = process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                # The pipe is held by something we cannot reach. Abandon it
                # rather than block: a leaked reader costs a file descriptor,
                # a blocked arm costs the run.
                out, err = "", f"abandoned after {timeout}s; pipe still held"
            code = -1
            err = (err or "") + f"\n[timed out after {timeout}s]"

        result = subprocess.CompletedProcess(command, code, out or "", err or "")
        if check and code != 0:
            raise subprocess.CalledProcessError(code, command, out, err)
        return result

    def available(self) -> bool:
        try:
            return self.run(["info"], timeout=30).returncode == 0
        except Exception:
            return False


@dataclass
class Container:
    """A live container for one attempt. Always removed, including on failure."""

    runtime: Runtime
    name: str
    image: str
    workdir: str = "/testbed"

    #: Longest command sent as an argv element. Above this it goes through a
    #: file instead.
    #
    # `bash -lc <command>` puts the whole script in one argument, and over ssh
    # that argument shares the exec limit with the ssh command line itself.
    # Measured on `psf__requests-863`, whose PASS_TO_PASS list names hundreds of
    # tests: `OSError: [Errno 7] Argument list too long: 'ssh'`, and the task
    # failed with no patch for a reason that had nothing to do with the agent.
    #
    # 96 KB is well under a typical 2 MB ARG_MAX while leaving room for the ssh
    # invocation, the environment and podman's own arguments — the limit applies
    # to their sum, not to this string alone.
    MAX_INLINE_COMMAND = 96 * 1024

    def exec(self, command: str, timeout: int = 1800,
             env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        args = ["exec", "-w", self.workdir]
        for key, value in (env or {}).items():
            args += ["-e", f"{key}={value}"]

        if len(command) > self.MAX_INLINE_COMMAND:
            # Copy the script in and run it by name. `copy_in` streams the file
            # rather than passing its contents, so nothing large reaches argv.
            import tempfile

            script = f"/tmp/.phronix-exec-{abs(hash(command)) & 0xffffffff:08x}.sh"
            handle = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                                 encoding="utf-8")
            try:
                handle.write(command)
                handle.close()
                self.copy_in(Path(handle.name), script)
            finally:
                try:
                    os.unlink(handle.name)
                except OSError:
                    pass
            args += [self.name, "bash", "-lc",
                     f"bash '{script}'; rc=$?; rm -f '{script}'; exit $rc"]
        else:
            args += [self.name, "bash", "-lc", command]
        return self.runtime.run(args, timeout=timeout)

    def copy_in(self, source: Path, dest: str) -> None:
        self.runtime.run(["cp", str(source), f"{self.name}:{dest}"], check=True)

    def copy_out(self, source: str, dest: Path) -> bool:
        dest.parent.mkdir(parents=True, exist_ok=True)
        return self.runtime.run(["cp", f"{self.name}:{source}", str(dest)]).returncode == 0

    def remove(self) -> None:
        # Force, and swallow errors: a container we failed to remove must not turn
        # into an exception that loses the attempt's results.
        try:
            self.runtime.run(["rm", "-f", self.name], timeout=120)
        except Exception:
            pass


class ContainerSession:
    """Context manager giving one clean container for one attempt."""

    def __init__(self, runtime: Runtime, instance_id: str, attempt: int,
                 image_template: str = DEFAULT_IMAGE_TEMPLATE,
                 pull: bool = True, mounts: Optional[Dict[Path, str]] = None,
                 label: str = "") -> None:
        self.runtime = runtime
        self.instance_id = instance_id
        self.image = image_for(instance_id, image_template)
        # Attempt index, arm label and a random suffix all appear in the name.
        #
        # The suffix is not decoration. The name was previously made unique with
        # a one-second-resolution timestamp, which collided the moment two arms
        # ran concurrently: both start the same instance in the same second, and
        # the second one dies with "container name is already in use" — an error
        # that reads like leftover state rather than a race. The label keeps the
        # name diagnosable when several containers are up at once.
        unique = uuid.uuid4().hex[:8]
        stem = instance_id.replace("__", "-")
        parts = ["phronix-bench", stem, str(attempt)]
        if label:
            parts.insert(1, re.sub(r"[^a-zA-Z0-9-]+", "-", label))
        self.name = "-".join(parts) + f"-{unique}"
        self.pull = pull
        self.mounts = mounts or {}
        self.container: Optional[Container] = None

    def __enter__(self) -> Container:
        if self.pull:
            # Best-effort: a cached image is fine and the run should not fail
            # because the registry is briefly unreachable.
            self.runtime.run(["pull", self.image], timeout=1800)

        args = ["run", "-d", "--rm=false", "--name", self.name]
        for host, guest in self.mounts.items():
            # :ro on the frozen arm's store is what makes "frozen" real rather
            # than a promise the agent could break.
            args += ["-v", f"{host}:{guest}"]
        args += [self.image, "sleep", "infinity"]

        if self.runtime.launcher and not self.runtime.remote_shell:
            # Only blocking launchers need the fire-and-poll dance; ssh
            # returns immediately for a detached container.
            self._start_detached(args)
        else:
            result = self.runtime.run(args, timeout=600)
            if result.returncode != 0:
                raise IsolationError(
                    f"could not start {self.image}: {result.stderr.strip()[-400:]}")
        self.container = Container(self.runtime, self.name, self.image)
        return self.container

    #: How long to wait for a container started through a batch launcher to
    #: appear. Generous: the image is local, but the launcher itself queues.
    START_DEADLINE_S = 420

    def _start_detached(self, args: List[str]) -> None:
        """Start the container without waiting for the launcher call to return.

        ``podman run -d`` never returns under ``flux run``. The container starts
        within seconds and is perfectly usable — verified by exec'ing into it from
        a separate invocation — but flux waits for every process in the task's
        cgroup, and the container's supervisor lives there, so the launcher call
        blocks for as long as the container lives. ``setsid`` does not escape it.

        So the start is fired and left running, and readiness is established by
        polling for the container instead of by the call returning. The launcher
        process lingers until the container is removed, at which point it exits on
        its own — :meth:`__exit__` removing the container is what reaps it.
        """
        process = subprocess.Popen(
            [*self.runtime.launcher, self.runtime.binary,
             *self.runtime._global_flags(), *args],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)

        deadline = time.time() + self.START_DEADLINE_S
        while time.time() < deadline:
            if self._is_running():
                return
            # If the launcher died, the container is never coming; surface why
            # rather than waiting out the whole deadline.
            if process.poll() is not None and not self._is_running():
                _, stderr = process.communicate(timeout=30)
                raise IsolationError(
                    f"could not start {self.image} via "
                    f"{' '.join(self.runtime.launcher)}: {stderr.strip()[-400:]}")
            time.sleep(3)

        process.kill()
        raise IsolationError(
            f"{self.image} did not come up within {self.START_DEADLINE_S}s via "
            f"{' '.join(self.runtime.launcher)}")

    def _is_running(self) -> bool:
        result = self.runtime.run(
            ["ps", "--filter", f"name={self.name}", "--format", "{{.Names}}"],
            timeout=120)
        return result.returncode == 0 and self.name in result.stdout

    def __exit__(self, *_exc: Any) -> None:
        if self.container:
            self.container.remove()


# ---------------------------------------------------------------------------
# Skill-store isolation
# ---------------------------------------------------------------------------

def fresh_store(destination: Path, seed_from_bundled: bool = True) -> Path:
    """Create a run-scoped phronix layer containing only the framework skeleton.

    ``--fresh`` means exactly this: the store starts as the bundled skills and
    agents that ship with phronix, and nothing else. No skill written by a
    previous benchmark run, and nothing from the developer's own project or user
    layers — both of which would otherwise be merged in by the normal layer
    resolution and would silently pre-train the arm.

    Returns the store root, to be passed as ``PHRONIX_PROJECT_ROOT``'s ``.phronix``.
    """
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    for kind in ("skills", "agents", "memory", "capabilities", "verifiers"):
        (destination / kind).mkdir(parents=True, exist_ok=True)

    if seed_from_bundled:
        from phronix.layers import bundled_root

        source = bundled_root()
        for kind in ("skills", "agents", "verifiers"):
            origin = source / kind
            if not origin.is_dir():
                continue
            if kind != "skills":
                shutil.copytree(origin, destination / kind, dirs_exist_ok=True)
                continue
            # The bundle ships the PIPELINE's skills, and only those.
            #
            # Two task skills — one naming a sympy filter bug, one a pylint
            # ignore-paths fix — had been committed into the skeleton, so every
            # "from scratch" run started holding a write-up of two of the tasks
            # it was about to be measured on. Nothing in the results would have
            # shown it.
            #
            # Filtered here rather than trusted upstream: what is in the bundle
            # is a question of what somebody committed, and this is the one
            # place that decides what a fresh run may inherit. A skill that is
            # part of the method is named for the framework; anything else
            # belongs in the project layer, which `--fresh` does not read.
            (destination / kind).mkdir(parents=True, exist_ok=True)
            for entry in sorted(origin.iterdir()):
                if entry.is_dir() and not entry.name.startswith("phronix-"):
                    continue
                if entry.is_dir():
                    shutil.copytree(entry, destination / kind / entry.name,
                                    dirs_exist_ok=True)
                elif entry.is_file():
                    shutil.copy2(entry, destination / kind / entry.name)
    (destination / "README.md").write_text(
        "Benchmark run store — seeded from the bundled phronix skeleton only.\n"
        "Skills written here were learned during this run.\n")
    return destination


# What a run can contribute back to the project, and what it cannot.
#
# ``agents`` is absent deliberately: agent definitions are rendered from the
# YAML templates by `phronix sync`, so promoting them would fight the generator
# and produce a diff on every model-map change.
CARRY_DIRS = ("skills", "memory", "capabilities", "verifiers", "research")


def _differs_from_bundled(path: Path, store_root: Path) -> bool:
    """Is this file something the run produced, rather than framework skeleton?

    ``fresh_store`` copies the bundled skills in, so a naive promotion would
    write the whole framework into the project layer, where it would shadow the
    bundled copy and then rot the moment the framework changed. Only content
    that is new, or that the run actually modified, is the run's to contribute.
    """
    from phronix.layers import bundled_root

    relative = path.relative_to(store_root)
    original = bundled_root() / relative
    if not original.is_file():
        return True
    try:
        return original.read_bytes() != path.read_bytes()
    except OSError:
        return True


#: What a run always contributes back to the SOURCE tree, whatever else it does.
#:
#: Answers and the research behind them. The project layer that `carry_root`
#: normally targets is `/.phronix`, which is gitignored — so everything a run
#: learned lived exactly as long as the checkout it was learned in, and a
#: clone started from nothing.
#:
#: `--fresh` still means what it says: `capabilities.visible_files` hides
#: bundled TASK ANSWERS from a from-scratch run while keeping the framework's
#: own tools. Saving and reading are different questions, and conflating them
#: is what made "always keep it" and "start clean" look incompatible.
SOURCE_DIRS = ("capabilities", "research")


def promote_to_source(store_root: Path) -> Dict[str, Any]:
    """Copy this run's capabilities and research into the packaged layer.

    Always, and regardless of `--fresh` or `--no-carry`: research is the
    expensive half of a run, and the point of keeping it is not paying for it
    twice. What a fresh run is entitled to is a clean READ, which it still
    gets.
    """
    from phronix.layers import bundled_root

    store_root = Path(store_root)
    try:
        destination = Path(bundled_root())
        destination.mkdir(parents=True, exist_ok=True)
    except Exception as exc:                     # a read-only install
        return {"promoted": [], "error": str(exc)[:120]}

    carried: List[str] = []
    for kind in SOURCE_DIRS:
        source = store_root / kind
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(store_root)
            target = destination / relative
            # Never overwrite what the framework ships. A run adds to the
            # source tree; it does not edit it.
            if target.exists() and kind == "capabilities" and "tasks" not in relative.parts:
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                carried.append(str(relative))
            except OSError:
                continue
    return {"promoted": carried, "destination": str(destination)}


def promote_store(store_root: Path, carry_root: Path) -> Dict[str, Any]:
    """Write what a run learned back into the durable project layer.

    Research is expensive — a survey, a plan, parallel investigation of several
    aspects, then evaluation — and until now every bit of it was discarded with
    the run directory. The next run started from the bundled skeleton and paid
    the same cost to rediscover the same things.

    So the store is merged back into the project layer, where phronix reads it
    like any other project content, and :func:`seed_store` puts it in front of
    the next run. Merge, never mirror: files are added and updated, never
    deleted, because two runs finishing out of order must not erase each other.
    """
    store_root, carry_root = Path(store_root), Path(carry_root)
    promoted: List[str] = []
    if not store_root.is_dir():
        return {"promoted": promoted, "carry_root": str(carry_root)}

    carry_root.mkdir(parents=True, exist_ok=True)
    readme = carry_root / "README.md"
    if not readme.is_file():
        try:
            readme.write_text(
                "# What earlier runs learned\n\n"
                "Everything in this directory was produced by a run, not shipped "
                "with the framework: skills written or amended while solving "
                "tasks, research records, memory, capabilities and verifiers.\n\n"
                "It is committed on purpose. Research is the expensive part, and "
                "the point of keeping it is not paying for it twice.\n\n"
                "A run seeds itself from here by default. `--fresh` ignores all "
                "of it and starts from the bundled framework alone, which is how "
                "an approach gets evaluated cleanly — a fresh run still syncs "
                "what IT finds back into here when it ends.\n\n"
                "`research/sessions/` is the exception: per-run working state, "
                "git-ignored, folded into `research/` as each task finishes.\n")
        except OSError:
            pass

    for kind in CARRY_DIRS:
        source = store_root / kind
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file() or not _differs_from_bundled(path, store_root):
                continue
            # Per-session research is working state, not a result. It is folded
            # into the common folder by research.sync_session when the session
            # ends; promoting the session folders as well would check in the
            # intermediate state of every run that ever started.
            if "research/sessions/" in path.as_posix():
                continue
            target = carry_root / path.relative_to(store_root)
            try:
                if target.is_file() and target.read_bytes() == path.read_bytes():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                promoted.append(str(path.relative_to(store_root)))
            except OSError:
                continue
    return {"promoted": promoted, "carry_root": str(carry_root)}


#: Capabilities whose names start with this are METHOD, not answer.
#:
#: A tool like ``probe_run_area_tests`` knows how to run a repository's tests
#: for one area and read what failed. It carries nothing about any particular
#: task, so seeding it into a ``--fresh`` run does not pre-train that run — it
#: hands it the same shell scripting every previous run had to derive from
#: nothing, which is infrastructure rather than knowledge.
#:
#: A prefix rather than a metadata field because it is visible at every point it
#: matters: in the tool list the agent sees, in the file name on disk, and in
#: the seeding decision here. A capability that quietly encoded a task's answer
#: under this prefix would be visible in review for the same reason.
METHOD_CAPABILITY_PREFIX = "probe_"


def seed_store(store_root: Path, carry_root: Path,
               kinds: Optional[Sequence[str]] = None,
               method_tools_only: bool = False) -> Dict[str, Any]:
    """Lay the durable project layer over a freshly created run store.

    Applied after :func:`fresh_store`, so carried content wins over the bundled
    skeleton — which is the point: a skill the last run improved should be the
    one this run reads.

    This makes the arm no longer from-scratch. The caller records it in the
    manifest, because a learning arm seeded with prior learning is not
    comparable to a published SWE-bench number and nothing in the results
    themselves would reveal the difference.
    """
    store_root, carry_root = Path(store_root), Path(carry_root)
    seeded: List[str] = []
    if not carry_root.is_dir():
        return {"seeded": seeded, "carry_root": str(carry_root)}

    for kind in (kinds or CARRY_DIRS):
        source = carry_root / kind
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            if (method_tools_only
                    and not path.name.startswith(METHOD_CAPABILITY_PREFIX)):
                continue
            target = store_root / path.relative_to(carry_root)
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                seeded.append(str(path.relative_to(carry_root)))
            except OSError:
                continue
    return {"seeded": seeded, "carry_root": str(carry_root)}


def isolated_env(store_root: Path, cache_root: Path,
                 extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Environment that pins phronix to this run's store and cache.

    Every layer is redirected. ``PHRONIX_HOME`` in particular: without it the
    user layer at ``~/.phronix`` is merged in, and a developer's own accumulated
    skills would leak into what is supposed to be a from-scratch run — the exact
    contamination ``--fresh`` exists to prevent, and invisible when it happens.
    """
    env = dict(os.environ)
    env.update({
        "PHRONIX_PROJECT_ROOT": str(Path(store_root).parent),
        "PHRONIX_HOME": str(Path(cache_root) / "user-layer-empty"),
        "PHRONIX_CACHE": str(cache_root),
        "PHRONIX_CONTEXT_STATE_DIR": str(Path(cache_root) / "context-state"),
        # The framework's OWN layer is off limits for the whole run.
        #
        # Redirecting the project and user layers is not enough. phronix is
        # installed editable from a clone here, which leaves the bundled layer
        # writable inside a git worktree — so anything that resolves a write to
        # it edits the repository, and the repository is what every later run
        # seeds from. Measured: a `--fresh --no-carry` run on a django task
        # wrote a sympy skill into `src/phronix/.phronix/skills/`, and the six
        # near-duplicate `column-domain` skills that reached later runs came
        # the same way. A from-scratch run was inheriting the edits of the runs
        # before it while reporting that it started clean.
        "PHRONIX_BUNDLED_READONLY": "1",
    })
    Path(env["PHRONIX_HOME"]).mkdir(parents=True, exist_ok=True)
    env.update(extra or {})
    return env


def snapshot_store(store_root: Path, destination: Path) -> Dict[str, Any]:
    """Copy the store after a task, so the run can be audited or replayed.

    Cheap (a few hundred KB) and the only way to answer "which skill existed when
    task 17 ran" after the fact. Without it, a reuse-rate figure is unverifiable.
    """
    store_root, destination = Path(store_root), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(store_root, destination)
    skills = sorted(p.name for p in (store_root / "skills").glob("*") if p.is_dir())
    return {"snapshot": str(destination), "skills": skills, "skill_count": len(skills)}


def store_inventory(store_root: Path) -> Dict[str, List[str]]:
    """What the store currently holds, by kind. Used to diff before/after a task."""
    store_root = Path(store_root)
    out: Dict[str, List[str]] = {}
    for kind in ("skills", "agents", "capabilities", "verifiers"):
        base = store_root / kind
        if not base.is_dir():
            out[kind] = []
        elif kind == "skills":
            out[kind] = sorted(p.name for p in base.iterdir() if p.is_dir())
        else:
            out[kind] = sorted(p.stem for p in base.glob("*") if p.is_file())
    memory = store_root / "memory"
    out["memory"] = (sorted(p.stem for p in memory.glob("*.md") if p.name != "MEMORY.md")
                     if memory.is_dir() else [])
    return out

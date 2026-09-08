"""``phronix-bench`` — pin tasks, run arms, report.

Three subcommands, matching the three things you actually do:

``tasks``   pin a reproducible instance list (needs the dataset, once)
``run``     execute arms × tasks × tries, writing results as it goes
``report``  render tables and the comparison verdict from a finished run

``run`` is resumable in the coarse sense that results are appended per task, so a
run killed at task 22 keeps 21 tasks of data. It is not resumable *into* the same
directory: re-running an arm starts its results file clean, because appending to
a partial file would double-count and there is no safe way to tell the two apart
after the fact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .arms import ARM_ORDER, DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROVIDER


def cmd_tasks(args: argparse.Namespace) -> int:
    from .paths import dataset_cache
    from .tasks import DatasetUnavailable, cache_instances, load_instances, select, write_task_file

    cache = Path(args.dataset_cache) if args.dataset_cache else dataset_cache()
    try:
        instances = load_instances(args.split, cache)
    except DatasetUnavailable as exc:
        print(f"phronix-bench tasks: {exc}", file=sys.stderr)
        return 1

    path = cache_instances(instances, cache, args.split)
    print(f"cached {len(instances)} instances -> {path}")

    ids = select(instances, limit=args.limit, seed=args.seed,
                 stratify=not args.no_stratify)
    out = write_task_file(Path(args.out), ids, args.split, args.seed, instances)
    repos = sorted({instances[i].get("repo", "?") for i in ids})
    print(f"pinned {len(ids)} tasks across {len(repos)} repositories -> {out}")
    return 0


def cmd_prefetch(args: argparse.Namespace) -> int:
    """Fetch everything a run needs from the network, so runs need none.

    Three caches, in two places, because one of them cannot go where the others do:

    * **The dataset** and the HuggingFace download cache go on the PFS, next to
      the runs they describe. Small, and part of the experiment's provenance.
    * **Image archives** (``podman save`` tarballs) also go on the PFS. These are
      the durable copy: the live store is node-local and evaporates on reboot,
      and re-downloading 90 GB from a public registry is the slowest possible way
      to recover from that.
    * **The live image store** must be node-local. Podman cannot extract an image
      onto lustre here at all — a 3 MB alpine fails on ``lsetxattr /bin`` — so
      this one is a hard constraint rather than a preference.

    Pulling up front rather than lazily is worth a subcommand because a pull is
    ~3 GB against a public registry: doing it inside a timed attempt charges
    registry latency to the agent's wall-clock, and a transient registry failure
    kills a task that had nothing wrong with it.
    """
    from .isolation import Runtime, image_for
    from .paths import dataset_cache, data_root, image_store
    from .tasks import DatasetUnavailable, cache_instances, load_instances, read_task_file

    root = data_root(args.data_root)
    cache = Path(args.dataset_cache) if args.dataset_cache else dataset_cache(root)

    # Keep HuggingFace's own cache off $HOME. datasets/ downloads the raw parquet
    # into HF_HOME before we ever see a row, and its default is ~/.cache — which
    # on this site is a quota-limited NFS mount shared with every other session.
    hf_home = root / "hf-cache"
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HF_DATASETS_CACHE", str(hf_home / "datasets"))
    print(f"hf cache:  {hf_home}")

    print(f"dataset:   {cache}")
    try:
        instances = load_instances(args.split, cache)
    except DatasetUnavailable as exc:
        print(f"phronix-bench prefetch: {exc}", file=sys.stderr, flush=True)
        return 1
    path = cache_instances(instances, cache, args.split)
    print(f"  cached {len(instances)} instances -> {path}")

    if args.tasks:
        ids = read_task_file(Path(args.tasks))
    else:
        ids = sorted(instances)
    missing = [i for i in ids if i not in instances]
    if missing:
        print(f"  {len(missing)} pinned ids are not in split {args.split!r}: "
              f"{', '.join(missing[:3])}", file=sys.stderr, flush=True)
        return 1

    if args.no_images:
        print(f"images:    skipped (--no-images); {len(ids)} would be pulled")
        return 0

    store = image_store()
    archives = None if args.no_archive else Path(args.archive_dir or (root / "images"))
    if archives:
        archives.mkdir(parents=True, exist_ok=True)
        print(f"archives:  {archives} (durable, survives reboot)")
    print(f"images:    {store['root']} (live store, ~3 GB each)")

    runtime = Runtime.detect(storage=store)
    failed: List[str] = []
    counts = {"present": 0, "loaded": 0, "pulled": 0}

    for number, instance_id in enumerate(ids, 1):
        image = image_for(instance_id)
        archive = archives / f"{instance_id}.tar" if archives else None
        started = time.time()

        if runtime.run(["image", "exists", image], timeout=120).returncode == 0:
            counts["present"] += 1
            print(f"  [{number:>3}/{len(ids)}] {instance_id:<42} present", flush=True)
            # Still archive it if the durable copy is missing, so a later reboot
            # does not send us back to the registry for an image we already have.
            if archive is not None and not archive.is_file():
                runtime.run(["save", "-o", str(archive), image], timeout=args.timeout)
            continue

        if archive is not None and archive.is_file():
            result = runtime.run(["load", "-i", str(archive)], timeout=args.timeout)
            if result.returncode == 0:
                counts["loaded"] += 1
                print(f"  [{number:>3}/{len(ids)}] {instance_id:<42} loaded "
                      f"{time.time() - started:6.0f}s  (no network)", flush=True)
                continue
            print(f"  [{number:>3}/{len(ids)}] {instance_id:<42} archive unreadable, "
                  f"falling back to registry", file=sys.stderr, flush=True)

        result = runtime.run(["pull", image], timeout=args.timeout)
        elapsed = time.time() - started
        if result.returncode != 0:
            failed.append(instance_id)
            print(f"  [{number:>3}/{len(ids)}] {instance_id:<42} FAIL {elapsed:6.0f}s "
                  f"{result.stderr.strip()[-200:]}", file=sys.stderr, flush=True)
            continue
        counts["pulled"] += 1
        if archive is not None:
            saved = runtime.run(["save", "-o", str(archive), image], timeout=args.timeout)
            if saved.returncode != 0:
                # Not fatal: the image is in the live store and the run can
                # proceed. Only the durable copy is missing.
                print(f"      archive failed: {saved.stderr.strip()[-160:]}",
                      file=sys.stderr, flush=True)
        print(f"  [{number:>3}/{len(ids)}] {instance_id:<42} pulled {elapsed:6.0f}s", flush=True)

    print(f"\n{len(ids) - len(failed)}/{len(ids)} images available "
          f"({counts['present']} already there, {counts['loaded']} from archive, "
          f"{counts['pulled']} from registry)")
    if failed:
        print(f"failed: {', '.join(failed)}", file=sys.stderr, flush=True)
        print("re-run prefetch to retry only these; available images are skipped.",
              file=sys.stderr, flush=True)
    return 1 if failed else 0


def _claim_runner_lock(root: Path, force: bool = False) -> Optional[Path]:
    """Refuse to start when another runner is already going against this root.

    Two runners were started within a minute of each other more than once here,
    and the damage is not theoretical: they share one podman image store and one
    node, they double the API spend, and their traces interleave into what reads
    like a single run restarting itself. Worse, killing one leaves the other's
    agents orphaned and still billing.

    The lock records a pid. A stale lock — the process is gone — is taken over
    silently, because a crashed run must not block the next one.
    """
    lock = Path(root) / ".runner.lock"
    try:
        existing = int(lock.read_text().split()[0])
    except (OSError, ValueError, IndexError):
        existing = 0

    if existing and existing != os.getpid():
        try:
            os.kill(existing, 0)          # signal 0: liveness test, no effect
            alive = True
        except (OSError, ProcessLookupError):
            alive = False
        if alive and not force:
            print(f"another benchmark runner is already running (pid {existing}). "
                  f"Stop it first, or pass --force if you are certain it is dead.\n"
                  f"lock: {lock}", file=sys.stderr)
            return None

    try:
        lock.write_text(f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    except OSError:
        pass
    return lock


def default_carry_root() -> str:
    """Where research accumulates between runs: the phronix project's own layer.

    The project layer rather than a scratch directory on the PFS, because that
    is what "learned this" should mean — a finding that survives the run becomes
    part of the project, reviewable in a diff and committable, instead of state
    hidden in a benchmark output tree that nobody reads.

    Falls back to the PFS when the checkout is not writable, which it is not when
    the harness runs from an installed package.
    """
    from phronix.layers import project_root

    try:
        found = project_root()
        if found is None:
            raise RuntimeError("no project root")
        root = Path(found) / ".phronix"
        root.mkdir(parents=True, exist_ok=True)
        probe = root / ".writable"
        probe.write_text("")
        probe.unlink()
        return str(root)
    except Exception:
        from .paths import data_root

        fallback = data_root() / "carry" / ".phronix"
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)


def cmd_run(args: argparse.Namespace) -> int:
    from .runner import RunConfig, Runner
    from .tasks import DatasetUnavailable, load_instances, read_task_file

    # Set before anything imports arms: the resolver reads this once and
    # caches, because `auto` is an HTTP probe of the fleet and every stage of
    # every task would otherwise repeat it.
    os.environ["PHRONIX_BUDGET_SCALE"] = str(args.budget_scale)

    try:
        task_ids = read_task_file(Path(args.tasks))
    except FileNotFoundError as exc:
        print(f"phronix-bench run: {exc}\nGenerate one with `phronix-bench tasks`.",
              file=sys.stderr)
        return 1

    if args.limit:
        task_ids = task_ids[:args.limit]

    from .paths import NoDataRoot, data_root, dataset_cache, run_dir

    try:
        root = data_root(args.data_root or None)
    except NoDataRoot as exc:
        print(f"phronix-bench run: {exc}", file=sys.stderr)
        return 1

    cache = Path(args.dataset_cache) if args.dataset_cache else dataset_cache(root)
    out = (Path(args.out) if args.out
           else run_dir(time.strftime("%Y%m%d-%H%M%S"), root))
    try:
        instances = load_instances(args.split, cache)
    except DatasetUnavailable as exc:
        print(f"phronix-bench run: {exc}", file=sys.stderr)
        return 1

    missing = [i for i in task_ids if i not in instances]
    if missing:
        # Loudly, and before spending anything: a silently shortened task list
        # makes two runs incomparable in a way nothing downstream would reveal.
        print(f"phronix-bench run: {len(missing)} pinned task(s) are not in the "
              f"{args.split!r} split, starting with {missing[0]}. The task list and "
              "the dataset disagree; fix one before running.", file=sys.stderr)
        return 1

    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    unknown = [a for a in arms if a not in ARM_ORDER]
    if unknown:
        print(f"phronix-bench run: unknown arm(s) {unknown}; known: {', '.join(ARM_ORDER)}",
              file=sys.stderr)
        return 1

    # No cluster asked for means a HOSTED endpoint, and hosted must not
    # measure whatever fleet happens to be deployed on this machine.
    #
    # `has_local_fleet` falls back to the default cluster config, which is
    # right for a local run started without `--cluster` and wrong here: a
    # hosted Haiku run read a concurrent gpt-oss job's cluster, measured
    # 126 tok/s against a calibration of 1000, and multiplied every research
    # budget by 7.9 for a model that turns a stage around in seconds.
    if not getattr(args, "cluster", None):
        os.environ.setdefault("PHRONIX_HOSTED_MODEL", "1")
        # ...and PACED only for the subscription.
        #
        # The Claude account has a five-hour window that, once rejected, fails
        # every agent for the rest of it, so its draw has to be spaced. A site
        # gateway is hosted too and has none of that — it has its own key and
        # its own capacity — so pacing it to 8 agents and a 2s stagger buys
        # nothing and costs the run. `--provider` naming anything other than
        # Anthropic is what says "not the subscription".
        provider = str(getattr(args, "provider", "") or "").lower()
        if provider in ("", "anthropic", "claude"):
            os.environ.setdefault("PHRONIX_PACED_LLM", "1")
        elif not getattr(args, "api_key", ""):
            # A gateway needs a credential, and it must not travel in argv.
            #
            # `run-benchmark.sh` passes `--base-url` but no key, so a gateway
            # run reached the endpoint unauthenticated. Putting the key on the
            # command line instead would print it in `ps`, in the batch log,
            # and in the manifest's own record of how the run was invoked.
            # The environment is where it already lives — `.env` is sourced
            # before the runner starts.
            args.api_key = (os.environ.get("PHRONIX_API_KEY")
                            or os.environ.get("OPENAI_API_KEY") or "")

    if getattr(args, "cluster", None):
        # The cluster's config is the source of truth for where the model is
        # and what it is called. Resolved here, before the RunConfig is built,
        # so every arm and the manifest all record the same endpoint.
        from . import cluster as cluster_mod

        spec = cluster_mod.load(Path(args.cluster) if args.cluster is not True
                                else None)
        wired = cluster_mod.configure_opencode(spec, direct=args.cluster_direct)
        args.base_url = wired["base_url"]
        args.model = spec.model
        args.api_key = spec.api_key
        args.provider = cluster_mod.PROVIDER_NAME
        args.models = ",".join(spec.models)
        args.pinned_models = ",".join(spec.pinned_models())
        print(f"cluster: {spec.describe()}", file=sys.stderr)
        print(f"         opencode provider '{wired['provider']}' -> "
              f"{wired['file']}", file=sys.stderr)

    # Say what the budgets ended up being, and why.
    #
    # A stage cut off at its ceiling looks like a slow stage from the outside,
    # so the scale has to be visible BEFORE the run rather than reconstructed
    # from the manifest afterwards.
    from .arms import budget_scale, measured_decode_rate

    resolved = budget_scale()
    if str(args.budget_scale).strip().lower() == "auto":
        rate = measured_decode_rate()
        if rate:
            print(f"budgets: x{resolved:.1f} — fleet decodes {rate:.0f} tok/s "
                  f"against a calibration of 1000", file=sys.stderr)
        else:
            print("budgets: x1.0 — no fleet to measure, using the calibration "
                  "the budgets were set at", file=sys.stderr)
    elif resolved != 1.0:
        print(f"budgets: x{resolved:.1f} (set explicitly)", file=sys.stderr)

    if "opencode-phronix" in arms and "opencode-phronix-frozen" not in arms:
        print("note: running the learning arm without `opencode-phronix-frozen`. Any "
              "slope it shows cannot be separated from task-ordering effects, and the "
              "report will say so rather than quote a learning rate.", file=sys.stderr)

    config = RunConfig(
        tasks=task_ids, arms=arms, model=args.model, provider=args.provider,
        base_url=args.base_url, api_key=getattr(args, "api_key", "") or "",
        max_tries=args.max_tries, timeout_s=args.timeout,
        isolation=args.isolation, fresh=not args.no_fresh, pull=not args.no_pull,
        resume_from=getattr(args, "resume", "") or "",
        carry_root=("" if args.no_carry else (args.carry_root or default_carry_root())),
        # Written to always, read from only when carrying. `--fresh` and
        # `--no-carry` both empty `carry_root`, and gating promotion on it
        # meant a from-scratch run contributed nothing to the runs after it.
        promote_root=(args.promote_root or args.carry_root
                      or default_carry_root()),
        max_spend_usd=float(getattr(args, "max_spend", 0.0) or 0.0),
        # Research is the fallback, not the opening move, unless asked.
        pipeline=args.pipeline,
        research_on_retry=args.research_on_retry or not args.research_first,
        research_first=args.research_first,
        research_reuse=not args.fresh,
        research_session=(args.session or Path(out).name),
        out=out, image_template=args.image_template, data_root=str(root),
        flux_job=args.flux_job, node=args.node,
        parallel_arms=args.parallel_arms,
        parallel_tasks=args.parallel_tasks,
        # `or 0` not `or 1`: 0 means every candidate, and coercing it to 1
        # would quietly restore the single-attempt behaviour it asks to leave.
        attempt_candidates=int(getattr(args, "attempt_candidates", 0) or 0),
        models=getattr(args, "models", "") or "",
        pinned_models=getattr(args, "pinned_models", "") or "",
        nodes=getattr(args, "nodes", "") or "",
        tasks_per_node=int(getattr(args, "tasks_per_node", 0) or 0),
        until_pass=args.until_pass, stall_limit=args.stall_limit,
        include_hints=args.with_hints,
        reveal_target_tests=args.reveal_target_tests,
    )
    print(f"data root: {root}")
    print(f"run dir:   {out}")
    if args.node or args.flux_job:
        where = args.node or f"the node of flux job {args.flux_job}"
        print(f"containers: {where} over ssh (agent stays here)")
    if args.parallel_arms and len(arms) > 1:
        print(f"arms:       {len(arms)} running concurrently")
    if args.until_pass:
        print(f"retries:    until pass (ceiling {args.max_tries}, "
              f"stall limit {args.stall_limit})")
    if args.with_hints or args.reveal_target_tests:
        extras = [n for n, on in (("maintainer hints", args.with_hints),
                                  ("target test names", args.reveal_target_tests))
                  if on]
        print(f"NOTE:       agents are given {' and '.join(extras)} — these "
              "results are NOT comparable to standard SWE-bench numbers")
    lock = _claim_runner_lock(root, force=args.force)
    if lock is None:
        return 1
    runner = Runner(config, instances)
    try:
        runner.run()
    finally:
        try:
            if lock.is_file() and lock.read_text().split()[0] == str(os.getpid()):
                lock.unlink()
        except (OSError, IndexError):
            pass

    from . import report as report_module

    written = report_module.write(out)
    print(f"\nreport: {written['markdown']}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    from . import report as report_module

    run_dir = Path(args.run)
    if not run_dir.is_dir():
        print(f"phronix-bench report: no such run directory: {run_dir}", file=sys.stderr)
        return 1
    built = report_module.build(run_dir, window=args.window)
    if args.json:
        print(json.dumps(built, indent=2))
    else:
        print(report_module.render(built))
    report_module.write(run_dir, window=args.window)
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    from . import preflight

    checks = preflight.run_all(pull=args.pull, live=not args.offline,
                               dataset_cache=Path(args.dataset_cache)
                               if args.dataset_cache else None,
                               data_root=args.data_root or None,
                               base_url=getattr(args, "base_url", None)
                               or DEFAULT_BASE_URL,
                               model=getattr(args, "model", None) or DEFAULT_MODEL)
    print(preflight.render(checks))
    return 1 if any(not c.ok and not c.skipped for c in checks) else 0


def cmd_baseline(args: argparse.Namespace) -> int:
    """Run every task's tests with NO patch, and report what the environment does.

    The question this answers is not "is the task hard" but "can this instance
    be judged at all". sympy-24066 spent three attempts and $1.94 against a
    container whose testbed env had no pytest in it: every test scored
    not-passed, the verdict was indistinguishable from a catastrophically wrong
    patch, and the baseline cached 30 tests as already broken. None of that cost
    would have been spent had anyone run the suite once, unpatched, first.

    Cheap in tokens — no agent at all — but not in time: each instance is a
    multi-GB image pull. So results are appended to a JSONL as they land and
    already-recorded instances are skipped, which makes a sweep over the whole
    split resumable across allocations.
    """
    import concurrent.futures
    import threading

    from .isolation import ContainerSession, DEFAULT_IMAGE_TEMPLATE, Runtime
    from .paths import NoDataRoot, container_storage, data_root, dataset_cache
    from .runner import baseline_failures
    from .tasks import DatasetUnavailable, load_instances, read_task_file

    try:
        root = data_root(args.data_root or None)
        instances = load_instances(args.split, Path(args.dataset_cache)
                                   if args.dataset_cache else dataset_cache(root))
        task_ids = (read_task_file(Path(args.tasks)) if args.tasks
                    else sorted(instances))
    except (FileNotFoundError, NoDataRoot, DatasetUnavailable) as exc:
        print(f"phronix-bench baseline: {exc}", file=sys.stderr)
        return 1

    report = Path(args.report) if args.report else Path(root) / "baseline-report.jsonl"
    done: Dict[str, Dict[str, Any]] = {}
    if report.is_file() and not args.restart:
        for line in report.read_text(errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            done[row.get("instance_id", "")] = row

    todo = [i for i in task_ids if i not in done]
    runtime = Runtime.detect("podman", storage=container_storage(root),
                             flux_job=args.flux_job, node=args.node)
    cache = None if args.no_cache else Path(root) / "baselines"

    print(f"baseline check — {len(task_ids)} instance(s), no patch, no agent")
    print(f"node: {args.node or args.flux_job or 'local'}   jobs: {args.jobs}   "
          f"already recorded: {len(done)}   to run: {len(todo)}")
    print(f"report: {report}\n", flush=True)

    lock = threading.Lock()

    def measure(instance_id: str) -> Dict[str, Any]:
        instance = instances.get(instance_id)
        if instance is None:
            return {"instance_id": instance_id, "state": "not-in-split"}
        try:
            with ContainerSession(runtime, instance_id, 0,
                                  image_template=args.image_template
                                  or DEFAULT_IMAGE_TEMPLATE,
                                  pull=not args.no_pull, label="baseline") as box:
                result = baseline_failures(box, instance, cache_dir=cache,
                                           timeout_s=args.timeout)
        except Exception as exc:  # noqa: BLE001 - one bad instance must not stop it
            return {"instance_id": instance_id, "state": "error",
                    "detail": f"{type(exc).__name__}: {exc}"[:300]}

        if result.get("runner_failed"):
            return {"instance_id": instance_id, "state": "runner-failed",
                    "detail": str(result.get("error"))[:300]}
        already = result.get("pre_existing_failures") or []
        passing = result.get("target_already_passing") or []
        return {"instance_id": instance_id,
                # A target that passes BEFORE the fix means the instance cannot
                # measure anything: every arm resolves it by doing nothing.
                "state": ("target-already-passing" if passing
                          else "dirty" if already else "clean"),
                "pre_existing": already[:12], "pre_existing_n": len(already),
                "target_already_passing": passing[:4]}

    def record(row: Dict[str, Any], index: int) -> None:
        with lock:
            with report.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            state = row["state"]
            note = ""
            if state == "dirty":
                note = (f"{row['pre_existing_n']} already failing: "
                        f"{', '.join(row['pre_existing'][:2])}")
            elif state in ("runner-failed", "error", "not-in-split"):
                note = str(row.get("detail", ""))[:90]
            elif state == "target-already-passing":
                note = f"TARGET ALREADY PASSES: {row['target_already_passing']}"
            print(f"  [{index:>3}/{len(todo)}] {row['instance_id']:<34} "
                  f"{state:<22} {note}", flush=True)

    report.parent.mkdir(parents=True, exist_ok=True)
    if todo:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
            futures = {pool.submit(measure, i): i for i in todo}
            for index, future in enumerate(
                    concurrent.futures.as_completed(futures), 1):
                record(future.result(), index)

    rows = list(done.values()) + [json.loads(l) for l in
                                  report.read_text(errors="replace").splitlines()
                                  if l.strip()]
    seen: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        seen[row.get("instance_id", "")] = row
    final = [seen[i] for i in task_ids if i in seen]

    tally: Dict[str, int] = {}
    for row in final:
        tally[row["state"]] = tally.get(row["state"], 0) + 1
    print("\n" + "  ".join(f"{state}: {count}"
                            for state, count in sorted(tally.items())))

    unusable = [r["instance_id"] for r in final
                if r["state"] in ("runner-failed", "error", "not-in-split",
                                  "target-already-passing")]
    if unusable:
        print(f"\nunusable ({len(unusable)}) — do not spend a run on these:")
        for name in unusable[:40]:
            print(f"  {name}")
        if len(unusable) > 40:
            print(f"  ... and {len(unusable) - 40} more (see {report})")
    return 1 if unusable else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phronix-bench",
        description="Measure whether phronix's self-learning actually improves "
                    "performance, against mini-swe-agent and bare opencode.")
    parser.add_argument("--verbose", action="store_true",
                        help="Report which variables were loaded from .env (names only).")
    sub = parser.add_subparsers(dest="command", required=True)

    tasks = sub.add_parser("tasks", help="Pin a reproducible instance list.")
    tasks.add_argument("--split", default="lite", choices=("lite", "verified", "full"))
    tasks.add_argument("--limit", type=int, default=30)
    tasks.add_argument("--seed", type=int, default=0)
    tasks.add_argument("--no-stratify", action="store_true",
                       help="Sample without balancing across repositories. Makes "
                            "cross-repo skill reuse effectively unobservable.")
    tasks.add_argument("--dataset-cache", default="",
                       help="Directory for <split>.jsonl. Default: <PFS data root>/dataset.")
    tasks.add_argument("--out", default="tests/benchmark/tasks/lite-30.txt")
    tasks.set_defaults(func=cmd_tasks)

    prefetch = sub.add_parser(
        "prefetch",
        help="Download the dataset and container images so runs need no network.")
    prefetch.add_argument("--split", default="lite", choices=("lite", "verified", "full"))
    prefetch.add_argument("--tasks", default="tests/benchmark/tasks/lite-30.txt",
                          help="Pull images only for these instances. Empty pulls the "
                               "whole split, which for lite is ~300 images.")
    prefetch.add_argument("--dataset-cache", default="")
    prefetch.add_argument("--data-root", default="",
                          help="PFS root. Default: PHRONIX_BENCH_DATA, else the site PFS.")
    prefetch.add_argument("--no-images", action="store_true",
                          help="Fetch the dataset only; skip the multi-GB image pulls.")
    prefetch.add_argument("--archive-dir", default="",
                          help="Durable image archives on the PFS. Default: "
                               "<data root>/images. These survive reboot; the live "
                               "podman store does not.")
    prefetch.add_argument("--no-archive", action="store_true",
                          help="Do not keep PFS archives. Halves disk use, but a "
                               "reboot then costs a full re-download.")
    prefetch.add_argument("--timeout", type=int, default=3600,
                          help="Per-image pull timeout in seconds.")
    prefetch.set_defaults(func=cmd_prefetch)

    run = sub.add_parser("run", help="Execute arms × tasks × tries.")
    run.add_argument("--tasks", default="tests/benchmark/tasks/lite-30.txt")
    run.add_argument("--arms", default=",".join(ARM_ORDER))
    run.add_argument("--limit", type=int, default=0, help="Truncate the task list.")
    run.add_argument("--max-tries", type=int, default=3)
    run.add_argument("--max-spend", type=float, default=0.0, metavar="USD",
                     help="Stop starting new tasks once this much has been "
                          "charged. Checked at the door of every task, so the "
                          "overrun is bounded by one task. 0 disables the cap.")
    run.add_argument("--timeout", type=int, default=1800, help="Per-attempt seconds.")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--provider", default=DEFAULT_PROVIDER)
    run.add_argument("--base-url", default=DEFAULT_BASE_URL)
    run.add_argument("--attempt-candidates", type=int, default=0,
                     metavar="N",
                     help="Build, attempt and evaluate this many researched "
                          "plans separately, in parallel, keeping whichever "
                          "gets furthest on the target tests. 1 writes one "
                          "merged solution and makes one attempt. "
                          "0 (the default) does it for EVERY plan research "
                          "produced. "
                          "Whatever the number, the trials are then reconciled "
                          "into the store: what worked is merged, and what "
                          "failed is recorded as a lesson rather than lost.")
    run.add_argument("--models", default="",
                     help="Comma-separated models the endpoint serves. With "
                          "more than one, candidate-generating stages spread "
                          "across them. Usually comes from --cluster.")
    run.add_argument("--nodes", default="",
                     help="Comma-separated nodes to spread tasks across. Each "
                          "task's containers run on its assigned node over ssh.")
    run.add_argument("--tasks-per-node", type=int, default=0,
                     help="Concurrent tasks per node; the pool is this times "
                          "the node count. Overrides --parallel-tasks.")
    run.add_argument("--api-key", default="",
                     help="Credential for --base-url. Usually comes from "
                          "--cluster instead.")
    run.add_argument("--cluster", nargs="?", const=True, default=None,
                     metavar="CLUSTER_JSON",
                     help="Take the endpoint, model, key and provider from a "
                          "cluster.json. Overrides --base-url/--model/"
                          "--provider, and writes opencode's provider config.")
    run.add_argument("--cluster-direct", action="store_true",
                     help="Address a backend llama-server directly instead of "
                          "the gateway. opencode only — Claude Code needs the "
                          "gateway, which is what speaks the Anthropic format.")
    run.add_argument("--isolation", default="podman", choices=("podman", "docker"))
    run.add_argument("--image-template", default="",
                     help="Override the SWE-bench image name pattern.")
    run.add_argument("--node", default=os.environ.get("PHRONIX_BENCH_NODE", ""),
                     help="Run containers on this host over ssh. Faster and simpler "
                          "than --flux-job; use it when you know the node.")
    run.add_argument("--until-pass", action="store_true",
                     help="Retry each task until it passes. --max-tries becomes a "
                          "hard ceiling, and a task also stops once consecutive "
                          "attempts repeat a patch without learning anything new.")
    run.add_argument("--research-first", action="store_true",
                     help="Research before the first attempt. The default is to "
                          "try what the store already holds for this task, then a "
                          "plain attempt, and to research only after that fails — "
                          "so a task already solved once is not re-researched.")
    run.add_argument("--research-on-retry", action="store_true",
                     help="Withhold research from the first attempt, so it runs "
                          "only after that attempt has failed. Try 1 is then the "
                          "same first move the baseline makes, and what gets "
                          "measured is what research RECOVERS rather than what it "
                          "adds up front.")
    run.add_argument("--stall-limit", type=int, default=2,
                     help="With --until-pass: consecutive no-progress attempts "
                          "that end a task (default 2).")
    run.add_argument("--with-hints", action="store_true",
                     help="Attach the issue's maintainer discussion. Off by "
                          "default: published SWE-bench numbers exclude hints, so "
                          "a run with them is not comparable to them.")
    run.add_argument("--reveal-target-tests", action="store_true",
                     help="Name the grading tests to the agent. Off by default — "
                          "the name usually describes the required behaviour, so "
                          "this is a large hint and must be disclosed.")
    run.add_argument("--force", action="store_true",
                     help="Start even if another runner holds the lock. Only when "
                          "you know the other process is gone.")
    run.add_argument("--parallel-arms", action="store_true",
                     help="Run the arms concurrently. Tasks within an arm stay "
                          "strictly ordered, so learning carry-over is unaffected.")
    run.add_argument("--parallel-tasks", type=int, default=1,
                     help="Run this many of an arm's tasks at once. Faster for "
                          "iterating on the pipeline, and it INVALIDATES the "
                          "reuse and learning-rate figures: a task that "
                          "overlaps its predecessors cannot have benefited from "
                          "them. Recorded in the manifest.")
    run.add_argument("--flux-job", default=os.environ.get("PHRONIX_BENCH_FLUX_JOB", ""),
                     help="Run containers inside this flux allocation (single-node) "
                          "while the agent runs locally. Needed here because opencode "
                          "segfaults on the compute nodes but podman must run there.")
    run.add_argument("--budget-scale",
                     default=os.environ.get("PHRONIX_BUDGET_SCALE", "auto"),
                     help="Multiplier on every research stage budget, or 'auto' "
                          "(the default) to derive it from the fleet's measured "
                          "decode rate. The budgets are seconds but what a stage "
                          "needs is tokens, so they only mean anything paired "
                          "with a rate: they were calibrated at ~1000 tok/s, and "
                          "corona's MI50 fleet decodes ~34, so unscaled every "
                          "planning agent is killed mid-investigation and the "
                          "run is scored as though the research happened. 'auto' "
                          "reads /metrics from the replicas and is a no-op for a "
                          "hosted endpoint, where there is no fleet to measure "
                          "and the calibration already applies.")
    run.add_argument("--pipeline", default="sequential",
                     choices=("sequential", "parallel"),
                     help="Which research pipeline runs. 'sequential' (default) "
                          "is the tracked loop: check for a skill, attempt, "
                          "evaluate, fold the result into this task's record, "
                          "then either write the solution or hand the open "
                          "failure to research, which updates the skill the "
                          "next attempt loads. 'parallel' is the earlier "
                          "pipeline — plan emits ideas, each is refined, built "
                          "and tried on its own thread, pairs combine into "
                          "super-ideas. Both are kept so they can be compared "
                          "on the same tasks.")
    run.add_argument("--split", default="lite", choices=("lite", "verified", "full"))
    run.add_argument("--dataset-cache", default="")
    run.add_argument("--no-fresh", action="store_true",
                     help="Reuse an existing store instead of seeding from the bundled "
                          "skeleton. Breaks from-scratch comparability.")
    run.add_argument("--carry-root", default="",
                     help="Durable project layer that research is promoted into "
                          "after every task and seeded from at the start of the "
                          "next run. Default: the phronix project's own .phronix. "
                          "Findings therefore accumulate across runs instead of "
                          "dying with the run directory.")
    run.add_argument("--promote-root", default="",
                     help="Where this run WRITES what it learned, whatever its "
                          "mode. Unlike --carry-root this is not emptied by "
                          "--fresh or --no-carry: a from-scratch run still "
                          "contributes its research to the runs after it, and "
                          "the --fresh filter decides what may be READ. "
                          "Default: the same place --carry-root points at.")
    run.add_argument("--fresh", action="store_true",
                     help="Explore from scratch: ignore task-specific skills and "
                          "research from earlier runs, seeding only the bundled "
                          "framework. Use it to evaluate an approach cleanly — "
                          "reuse is the default because not paying twice for "
                          "research is the point of keeping it. What this run "
                          "finds is still synced back afterwards.")
    run.add_argument("--resume", default="", metavar="RUN-DIR|auto",
                     help="Continue a run that was cut short: its finished "
                          "tasks are carried into this one's results and not "
                          "re-run. `auto` finds the newest incomplete run of "
                          "the same task list and model. A node failure kills "
                          "the whole Flux job, so without this a resubmission "
                          "repeats everything the dead job had finished.")
    run.add_argument("--session", default="",
                     help="Name this run's research session. Records go to "
                          ".phronix/research/sessions/<name>/ and are folded into "
                          "the common folder when the run ends. Default: the run "
                          "directory's name.")
    run.add_argument("--no-carry", action="store_true",
                     help="Do not promote or seed research. Every run starts from "
                          "the bundled skeleton — required for a number that is "
                          "comparable to published SWE-bench results.")
    run.add_argument("--no-pull", action="store_true", help="Use cached images only.")
    run.add_argument("--out", default="",
                     help="Run directory. Default: <PFS data root>/runs/<timestamp>.")
    run.add_argument("--data-root", default="",
                     help="Bulk-data root. Default: a site PFS path. Never $HOME.")
    run.set_defaults(func=cmd_run)

    check = sub.add_parser(
        "check", help="Verify every integration point before spending on a real run.")
    check.add_argument("--pull", action="store_true",
                       help="Actually pull a SWE-bench image (multi-GB).")
    check.add_argument("--offline", action="store_true",
                       help="Skip the checks that cost tokens or network.")
    check.add_argument("--dataset-cache", default="")
    check.add_argument("--data-root", default="")
    check.set_defaults(func=cmd_check)

    baseline = sub.add_parser(
        "baseline",
        help="Run every task's tests unpatched, to find environment faults first.")
    baseline.add_argument("--tasks", default="",
                          help="Task file. Omitted means the WHOLE split.")
    baseline.add_argument("--jobs", type=int, default=4,
                          help="Instances measured concurrently.")
    baseline.add_argument("--report", default="",
                          help="JSONL of results; resumed from unless --restart.")
    baseline.add_argument("--restart", action="store_true",
                          help="Ignore an existing report and measure everything.")
    baseline.add_argument("--split", default="lite",
                          choices=("lite", "verified", "full"))
    baseline.add_argument("--node", default="")
    baseline.add_argument("--flux-job", default="")
    baseline.add_argument("--timeout", type=int, default=900)
    baseline.add_argument("--image-template", default="")
    baseline.add_argument("--dataset-cache", default="")
    baseline.add_argument("--data-root", default="")
    baseline.add_argument("--no-pull", action="store_true")
    baseline.add_argument("--no-cache", action="store_true",
                          help="Measure fresh rather than reading cached baselines.")
    baseline.set_defaults(func=cmd_baseline)

    report = sub.add_parser("report", help="Render tables from a finished run.")
    report.add_argument("run")
    report.add_argument("--window", type=int, default=10)
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=cmd_report)
    return parser


def _redirect_hf_cache() -> None:
    """Point HuggingFace's cache at the PFS before anything can import ``datasets``.

    ``HF_HOME`` defaults to ``~/.cache/huggingface``. The ``mini`` arm reaches the
    dataset through swebench rather than through our JSONL cache, so a run that
    never touches :func:`cmd_prefetch` would still quietly write gigabytes into a
    quota-limited NFS home. Set here rather than per-subcommand because the
    variable is read at import time by the datasets library, and an existing
    export always wins — a user who has deliberately set ``HF_HOME`` keeps it.
    """
    if os.environ.get("HF_HOME"):
        return
    try:
        from .paths import data_root

        home = data_root() / "hf-cache"
    except Exception:
        return  # No PFS root is a problem for `run` to report, not for import.
    home.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(home)
    os.environ.setdefault("HF_DATASETS_CACHE", str(home / "datasets"))


def main(argv: Optional[List[str]] = None) -> int:
    # Same as the stack launcher does. Without it the benchmark works from a
    # shell that happens to have OPENAI_API_KEY exported and fails
    # indistinguishably from one that does not.
    from . import env as env_module

    loaded = env_module.load()
    _redirect_hf_cache()
    args = build_parser().parse_args(argv)
    if loaded and getattr(args, "verbose", False):
        print(f"loaded from .env: {', '.join(sorted(loaded))}", file=sys.stderr)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted — results written so far are kept", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())

"""The ``phronix`` umbrella command.

Everything reachable through the individual ``phronix-*`` console scripts is
also reachable here as a subcommand, plus the two operations that only make
sense as a sequence:

``phronix init``
    Bootstrap a project end to end — create its layer, wire its instruction
    files and memory, install skills, render agents, sync permissions and hooks,
    and register the MCP server with every harness. One command from a fresh
    clone to a working setup.

``phronix status``
    What the store currently holds, where new learning will be written, and who
    inherits it. The first thing to run when something is not behaving as
    expected.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(payload if isinstance(payload, str) else json.dumps(payload, indent=2, default=str))


# ---------------------------------------------------------------------------
# init / status
# ---------------------------------------------------------------------------

#: How to count "what changed" in each deploy step's result. The steps predate
#: any common return shape and each reports differently; normalising here keeps
#: that history out of the deploy report, which has to be readable.
def _changes(label: str, result: Any) -> List[str]:
    if not isinstance(result, dict):
        return []
    if label == "workspace":
        return [f"{a['what']} ({a['status']})" for a in result.get("actions", [])
                if a["status"] in ("installed", "updated", "migrated")]
    if label in ("skills", "agents"):
        return [f"{i.get('harness', '')} {i['name']} ({i['action']})".strip()
                for i in result.get("installed", [])
                if i["action"] != "already_installed"]
    if label in ("permissions", "hooks"):
        return list(result.get("changed", []))
    if label == "mcp":
        out = []
        for key, value in result.items():
            if key in ("target", "transport", "changed", "summary"):
                continue
            if isinstance(value, dict):
                out += [f"{key} {f}" for f, s in value.items() if s == "updated"]
            elif value == "updated":
                out.append(key)
        return out
    return []


def cmd_deploy(args: argparse.Namespace) -> int:
    """Materialise everything from the package into the project root, idempotently.

    Runs the same steps every time and writes only what differs, so re-running is
    a no-op that says so. ``--check`` performs the comparison without writing and
    exits non-zero when anything is out of date — the shape a CI gate needs.
    """
    from phronix.agents import install_agents
    from phronix.bootstrap import ensure_workspace_setup
    from phronix.hooks import sync_hooks
    from phronix.layers import project_root
    from phronix.mcp_setup import configure_all
    from phronix.permissions import sync_permissions
    from phronix.skills import install_skills

    root = (Path(args.target).expanduser().resolve() if args.target
            else (project_root() or Path.cwd()))
    check = getattr(args, "check", False)

    if check:
        # Only the MCP step can preview without writing; the others compare
        # content as they go. Rather than build a parallel dry-run path for each
        # — which would be a second implementation to keep in step, and would
        # drift — deploy into a scratch copy and diff the outcome.
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory(prefix="phronix-check-") as tmp:
            scratch = Path(tmp) / "root"
            scratch.mkdir()
            for name in (".claude", ".opencode", ".codex", ".github", ".vscode",
                         ".phronix", "CLAUDE.md", "AGENTS.md", ".mcp.json", ".gitignore"):
                source = root / name
                if source.is_dir():
                    shutil.copytree(source, scratch / name, symlinks=True)
                elif source.exists():
                    shutil.copy2(source, scratch / name)
            # The Claude memory symlink points into ``~/.claude/projects/<slug>/``,
            # keyed on the project's absolute path — a scratch copy has a
            # different slug and so can never reproduce it. Including it would
            # make `--check` report an always-pending change on an
            # already-deployed project, which is exactly the false alarm that
            # gets a CI gate disabled.
            scratch_args = argparse.Namespace(**{**vars(args), "target": str(scratch),
                                                 "check": False, "json": True,
                                                 "no_link_memory": True})
            import io
            import contextlib

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                cmd_deploy(scratch_args)
            report = json.loads(buffer.getvalue())

        pending = {k: v for k, v in report["changes"].items() if v}
        if args.json:
            _print({"target": str(root), "up_to_date": not pending,
                    "pending": pending}, True)
        elif pending:
            print(f"Out of date: {root}")
            for label, items in pending.items():
                print(f"  {label}:")
                for item in items[:8]:
                    print(f"    - {item}")
                if len(items) > 8:
                    print(f"    - ... {len(items) - 8} more")
            print(f"\nRun `phronix deploy` to apply.")
        else:
            print(f"Up to date: {root}")
        return 1 if pending else 0

    steps = [
        ("workspace", lambda: ensure_workspace_setup(
            root, force=args.force, link_memory=not args.no_link_memory)),
        ("skills", lambda: install_skills(target_root=root)),
        ("agents", lambda: install_agents(target_root=root)),
        ("permissions", lambda: sync_permissions(root)),
        ("hooks", lambda: sync_hooks(root)),
        ("mcp", lambda: configure_all(root, transport=args.transport,
                                      host=args.host, port=args.port)),
    ]

    changes: Dict[str, List[str]] = {}
    conflicts: List[str] = []
    failures: List[str] = []
    for label, step in steps:
        try:
            result = step()
            changes[label] = _changes(label, result)
            if isinstance(result, dict):
                conflicts += [str(c) for c in result.get("conflicts", [])]
        except Exception as exc:
            changes[label] = []
            failures.append(f"{label}: {type(exc).__name__}: {exc}")

    total = sum(len(v) for v in changes.values())
    if args.json:
        _print({"target": str(root), "changed": total, "changes": changes,
                "conflicts": conflicts, "failed": failures}, True)
        return 1 if failures else 0

    for label, items in changes.items():
        marker = "+" if items else "="
        detail = f"{len(items)} change(s)" if items else "up to date"
        print(f"  {marker} {label:12s} {detail}")
        for item in items[:5]:
            print(f"      {item}")
        if len(items) > 5:
            print(f"      ... {len(items) - 5} more")

    for conflict in conflicts:
        print(f"  ! left alone (not ours): {conflict}")

    print(f"\n{'Deployed' if total else 'Already current'}: {root}")
    print(f"Knowledge layer: {root / '.phronix'}  "
          "(commit this — it is what your team inherits)")
    if failures:
        for failure in failures:
            print(f"  ! {failure}", file=sys.stderr)
        return 1
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from phronix import __version__
    from phronix.capabilities import listing as capability_listing
    from phronix.harness_models import summarize
    from phronix.layers import describe, resolve_write_layer

    try:
        write_layer = resolve_write_layer()
        target = {"name": write_layer.name, "root": str(write_layer.root),
                  "shared": write_layer.shared}
    except Exception as exc:
        target = {"error": str(exc)}

    try:
        from phronix.verification import coverage

        report = coverage()
        verification = {k: report[k] for k in
                        ("total_artifacts", "claim_verified", "percent",
                         "orphaned_verifiers", "broken_verifiers", "never_run")}
    except Exception as exc:
        verification = {"error": f"{type(exc).__name__}: {exc}"}

    payload = {
        "version": __version__,
        "layers": describe(),
        "write_layer": target,
        "verification": verification,
        "capabilities": capability_listing(),
        "harness_models": summarize(),
    }
    if args.json:
        _print(payload, True)
        return 0

    print(f"phronix {__version__}\n")
    print(f"{'layer':10s} {'skills':>7s} {'agents':>7s} {'memory':>7s} {'caps':>6s} "
          f"{'verif':>6s}  root")
    for entry in payload["layers"]:
        counts = entry["counts"]
        flags = []
        if not entry["exists"]:
            flags.append("absent")
        if entry["exists"] and not entry["writable"]:
            flags.append("read-only")
        suffix = f"  ({', '.join(flags)})" if flags else ""
        print(f"{entry['layer']:10s} {counts['skills']:7d} {counts['agents']:7d} "
              f"{counts['memory']:7d} {counts['capabilities']:6d} {counts['verifiers']:6d}  "
              f"{entry['root']}{suffix}")

    verification = payload["verification"]
    if "error" not in verification:
        print(f"\nverification: {verification['claim_verified']}/"
              f"{verification['total_artifacts']} artifacts have an authored corrector "
              f"({verification['percent']}%); all are structurally corrected")
        for label, key in (("orphaned", "orphaned_verifiers"),
                           ("broken", "broken_verifiers"),
                           ("never run", "never_run")):
            if verification.get(key):
                print(f"  {label}: {', '.join(verification[key])}")

    if "error" in target:
        print(f"\nwrite target: UNAVAILABLE — {target['error']}")
    else:
        audience = {
            "bundled": "everyone who installs phronix",
            "project": "everyone who clones this repository",
            "user": "you only, across your own projects",
        }[target["name"]]
        print(f"\nNew learning is written to the '{target['name']}' layer -> {audience}")
        print(f"  {target['root']}")

    print("\nmodels:")
    for line in payload["harness_models"]:
        print(f"  {line}")
    return 0


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

def cmd_sync(args: argparse.Namespace) -> int:
    from phronix.agents import sync_agents
    from phronix.hooks import sync_hooks
    from phronix.permissions import sync_permissions
    from phronix.skills import ensure_skills_setup

    root = Path(args.target).expanduser().resolve() if args.target else None
    available = {
        "skills": lambda: ensure_skills_setup(root),
        "agents": lambda: sync_agents(root),
        "permissions": lambda: sync_permissions(root),
        "hooks": lambda: sync_hooks(root),
    }
    wanted = list(available) if args.what == "all" else [args.what]
    results = {}
    for name in wanted:
        try:
            results[name] = available[name]()
        except Exception as exc:
            results[name] = {"error": f"{type(exc).__name__}: {exc}"}

    if args.json:
        _print(results, True)
        return 0
    for name, result in results.items():
        summary = result.get("summary") or result.get("status") or result.get("error")
        print(f"  {name:12s} {summary}")
    return 0


# ---------------------------------------------------------------------------
# thin passthroughs
# ---------------------------------------------------------------------------

def cmd_skills(args: argparse.Namespace) -> int:
    from phronix.skills import iter_skills, load, search, write_lesson

    if args.action == "list":
        skills = iter_skills()
        if args.json:
            _print([{k: s[k] for k in ("name", "description", "layer", "sections")}
                    for s in skills], True)
            return 0
        for skill in skills:
            print(f"{skill['layer']:8s} {skill['name']:32s} {skill['description'][:70]}")
        return 0
    if args.action == "search":
        _print(search(args.query or "", args.limit), True)
        return 0
    if args.action == "load":
        _print(load(args.query or "", section=args.section), True)
        return 0
    if args.action == "write":
        if not args.query or not args.lesson:
            print("usage: phronix skills write <skill> --lesson '<text>'", file=sys.stderr)
            return 2
        _print(write_lesson(args.query, args.lesson, section=args.section or "Lessons",
                            layer=args.layer), True)
        return 0
    return 2


def cmd_memory(args: argparse.Namespace) -> int:
    from phronix.memory import listing, read, write
    from phronix.memory_graph import recall

    if args.action == "list":
        entries = listing()
        if args.json:
            _print(entries, True)
            return 0
        for entry in entries:
            print(f"{entry.get('layer', '?'):8s} {entry.get('type', ''):10s} "
                  f"{entry['name']:36s} {entry.get('description', '')[:60]}")
        return 0
    if args.action == "recall":
        _print(recall(args.query or "", k=args.limit), True)
        return 0
    if args.action == "read":
        _print(read(args.query or "") or {"status": "not_found", "name": args.query}, True)
        return 0
    if args.action == "write":
        if not args.query or not args.body:
            print("usage: phronix memory write <name> --description D --body B", file=sys.stderr)
            return 2
        _print(write(args.query, args.description or "", args.body,
                     type=args.type, layer=args.layer), True)
        return 0
    return 2


def cmd_graph(args: argparse.Namespace) -> int:
    from phronix.knowledge_graph import ensure, get_node, query

    if args.action == "ensure":
        _print(ensure(args.scope, None, args.force), True)
        return 0
    if args.action == "node":
        _print(get_node(args.query or "", scope=args.scope), True)
        return 0
    result = query(question=args.query or "", mode=args.mode, symbol=args.symbol or "",
                   scope=args.scope)
    if args.json or result.get("status") != "ok":
        _print(result, True)
    else:
        print(result["output"])
    return 0


def cmd_privacy(args: argparse.Namespace) -> int:
    from phronix.privacy import (STRUCTURED_SUFFIXES, anonymize, current_users,
                                 find_identifiers, suspects)
    from phronix.layers import iter_all_content

    paths = [Path(p) for p in args.paths] if args.paths else list(iter_all_content())
    files: List[Path] = []
    for path in paths:
        files.extend(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else files.append(path)
    users = current_users()

    if args.action == "scan":
        from phronix.privacy import exemption_reason

        findings, exempt = [], []
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            hits = find_identifiers(text, extra_users=users)
            if not hits:
                continue
            reason = exemption_reason(text)
            if reason:
                exempt.append({"file": str(file), "reason": reason})
            else:
                findings.append({"file": str(file), "identifiers": sorted(set(hits))[:20]})
        if args.json:
            _print({"status": "clean" if not findings else "findings",
                    "checked": len(files), "findings": findings, "exempt": exempt}, True)
        else:
            for finding in findings:
                print(f"  LEAK   {finding['file']}: {', '.join(finding['identifiers'][:6])}")
            for entry in exempt:
                print(f"  exempt {entry['file']}: {entry['reason'][:80]}")
            print(f"\n{len(files) - len(findings) - len(exempt)}/{len(files)} clean, "
                  f"{len(exempt)} exempt, {len(findings)} with findings")
        return 1 if findings else 0

    if args.action == "suspects":
        found = []
        for file in files:
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for probe, token in suspects(text, extra_users=users):
                found.append({"file": str(file), "probe": probe, "text": token})
        _print(found, True)
        return 0

    changed = []
    for file in files:
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        clean = anonymize(text, extra_users=users,
                          preserve_structure=file.suffix in STRUCTURED_SUFFIXES)
        if clean != text:
            if not args.dry_run:
                file.write_text(clean)
            changed.append(str(file))
    _print({"status": "ok", "changed": changed, "dry_run": args.dry_run}, True)
    return 0


def cmd_capability(args: argparse.Namespace) -> int:
    from phronix.capabilities import listing, new

    if args.action == "list":
        entries = listing()
        if args.json:
            _print(entries, True)
            return 0
        for entry in entries:
            print(f"{entry['layer']:8s} {entry['name']:28s} {entry['description'][:60]}")
        return 0
    if not args.name:
        print("usage: phronix capability new <name> --description D [--source-file F]",
              file=sys.stderr)
        return 2
    source = Path(args.source_file).read_text() if args.source_file else None
    _print(new(args.name, args.description or "", source=source,
               layer=args.layer, overwrite=args.overwrite), True)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    from phronix.verification import coverage, discover, new, run

    if args.action == "list":
        verifiers = discover()
        if args.json:
            _print(verifiers, True)
            return 0
        for entry in verifiers:
            flag = "!" if entry.get("error") else " "
            print(f"{flag} {entry.get('layer', '?'):8s} {entry['name']:28s} "
                  f"{entry.get('kind', ''):11s} {entry.get('target', '')}")
        return 0

    if args.action == "coverage":
        report = coverage()
        if args.json:
            _print(report, True)
            return 0
        print(f"{report['covered']}/{report['total_artifacts']} artifacts verified "
              f"({report['percent']}%)\n")
        for entry in report["uncovered_detail"]:
            print(f"  UNVERIFIED  {entry['kind']:11s} {entry['name']}")
        for name in report["orphaned_verifiers"]:
            print(f"  ORPHANED    verifier    {name}  (target no longer exists)")
        for name in report["never_run"]:
            print(f"  NEVER RUN   verifier    {name}")
        # Uncovered learning is a gap to close, not an error to fail CI on;
        # an orphaned or never-run verifier is a broken check, which is worse.
        return 1 if (report["orphaned_verifiers"] or report["never_run"]) else 0

    if args.action == "new":
        if not (args.name and args.kind and args.target and args.claim):
            print("usage: phronix verify new <name> --kind K --target T --claim C",
                  file=sys.stderr)
            return 2
        source = Path(args.source_file).read_text() if args.source_file else None
        _print(new(args.name, args.kind, args.target, args.claim,
                   source=source, layer=args.layer, overwrite=args.overwrite), True)
        return 0

    result = run(name=args.name or "", kind=args.kind or "", target=args.target or "")
    if args.json:
        _print(result, True)
    else:
        for entry in result["results"]:
            print(f"  {entry['status'].upper():13s} {entry['name']:28s} "
                  f"{entry.get('target', '')}")
            if entry.get("evidence"):
                print(f"                {entry['evidence'][:160]}")
        print(f"\n{result['summary']}")
    # `inconclusive` is not a failure and must not fail a CI step; a broken
    # corrector (`error`) must, because it is unverifiable content that looks
    # verified.
    return 1 if result["status"] in ("fail", "error") else 0


def cmd_complexity(args: argparse.Namespace) -> int:
    from phronix.complexity import assess_agent, assess_task, reassess_all

    if args.action == "reassess":
        report = reassess_all()
        if args.json:
            _print(report, True)
            return 0
        print(f"{'agent':30s} {'declared':9s} {'scope':9s} {'intrinsic':10s} "
              f"{'needs':9s} score")
        for entry in report["all"]:
            flag = "  DRIFT" if entry["drift"] else ""
            print(f"{entry['agent']:30s} {entry['declared_level']:9s} "
                  f"{entry['level_from_scope']:9s} {entry['intrinsic']:10s} "
                  f"{entry['recommended_level']:9s} {entry['score']:.3f}{flag}")
        print(f"\n{report['next']}")
        # Drift is a finding to act on, not an error — non-zero so CI can gate.
        return 1 if report["drifted"] else 0

    result = (assess_agent(args.target) if args.action == "agent"
              else assess_task(args.target or ""))
    if args.json or result.get("status") != "ok":
        _print(result, True)
        return 0
    print(f"score            {result['score']:.3f}")
    print(f"recommended      {result['recommended_level']} (effort: "
          f"{result['recommended_effort']})")
    if "declared_level" in result:
        print(f"declared         {result['declared_level']}"
              + ("   DRIFT" if result["drift"] else ""))
    print("\ndrivers:")
    for driver in result["drivers"]:
        print(f"  {driver}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from phronix.mcp_server import main as serve

    argv = ["--transport", args.transport, "--host", args.host, "--port", str(args.port)]
    if args.no_setup:
        argv.append("--no-setup")
    return serve(argv)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phronix",
        description="A self-learning, self-healing agentic framework: capabilities "
                    "first, then intelligence, then agents.",
    )
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")

    # `--json` is accepted on either side of the subcommand. argparse normally
    # only allows a global flag BEFORE it, which reads as an arbitrary rule to
    # anyone typing `phronix deploy --json` — the obvious spelling. SUPPRESS is
    # what makes it work: without it the subparser's own default of False would
    # overwrite a `--json` given to the main parser.
    json_flag = argparse.ArgumentParser(add_help=False)
    json_flag.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                           help="Machine-readable output.")

    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, **kwargs) -> argparse.ArgumentParser:
        kwargs.setdefault("parents", []).append(json_flag)
        return sub.add_parser(name, **kwargs)

    # `init` and `deploy` are the same operation. `init` is what you reach for the
    # first time; `deploy` is what you reach for afterwards, and it is idempotent,
    # so they are deliberately one command with two names rather than two
    # implementations that could drift.
    for name, help_text in (
        ("deploy", "Materialise everything from the package into the project (idempotent)."),
        ("init", "Alias for `deploy` — bootstrap a project end to end."),
    ):
        deploy = add(name, help=help_text)
        deploy.add_argument("--target", default=None)
        deploy.add_argument("--force", action="store_true")
        deploy.add_argument("--check", action="store_true",
                            help="Report what would change and exit non-zero if "
                                 "anything is out of date. Writes nothing.")
        deploy.add_argument("--no-link-memory", action="store_true",
                            help="Leave Claude Code's memory out of version control.")
        deploy.add_argument("--transport", choices=("stdio", "http"), default="stdio")
        deploy.add_argument("--host", default="127.0.0.1")
        deploy.add_argument("--port", type=int, default=5100)
        deploy.set_defaults(func=cmd_deploy)

    status = add("status", help="Show layers, counts, and the write target.")
    status.set_defaults(func=cmd_status)

    sync = add("sync", help="Push the store out to the harnesses.")
    sync.add_argument("what", nargs="?", default="all",
                      choices=("all", "skills", "agents", "permissions", "hooks"))
    sync.add_argument("--target", default=None)
    sync.set_defaults(func=cmd_sync)

    skills = add("skills", help="Browse and grow the skill library.")
    skills.add_argument("action", choices=("list", "search", "load", "write"))
    skills.add_argument("query", nargs="?", default=None)
    skills.add_argument("--section", default=None)
    skills.add_argument("--lesson", default=None)
    skills.add_argument("--layer", default=None)
    skills.add_argument("--limit", type=int, default=5)
    skills.set_defaults(func=cmd_skills)

    memory = add("memory", help="Browse and grow the memory store.")
    memory.add_argument("action", choices=("list", "recall", "read", "write"))
    memory.add_argument("query", nargs="?", default=None)
    memory.add_argument("--description", default=None)
    memory.add_argument("--body", default=None)
    memory.add_argument("--type", default="project",
                        choices=("project", "feedback", "reference", "lesson"))
    memory.add_argument("--layer", default=None)
    memory.add_argument("--limit", type=int, default=5)
    memory.set_defaults(func=cmd_memory)

    graph = add("graph", help="Locate code and knowledge without reading it.")
    graph.add_argument("action", choices=("query", "ensure", "node"))
    graph.add_argument("query", nargs="?", default=None)
    graph.add_argument("--mode", default="query",
                       choices=("query", "docs", "explain", "affected"))
    graph.add_argument("--symbol", default=None)
    graph.add_argument("--scope", default="knowledge", choices=("knowledge", "project"))
    graph.add_argument("--force", action="store_true")
    graph.set_defaults(func=cmd_graph)

    privacy = add("privacy", help="Verify nothing shared identifies anyone.")
    privacy.add_argument("action", choices=("scan", "redact", "suspects"))
    privacy.add_argument("paths", nargs="*")
    privacy.add_argument("--dry-run", action="store_true")
    privacy.set_defaults(func=cmd_privacy)

    capability = add("capability", help="Deterministic tools built at runtime.")
    capability.add_argument("action", choices=("list", "new"))
    capability.add_argument("name", nargs="?", default=None)
    capability.add_argument("--description", default=None)
    capability.add_argument("--source-file", default=None)
    capability.add_argument("--layer", default=None)
    capability.add_argument("--overwrite", action="store_true")
    capability.set_defaults(func=cmd_capability)

    verify = add("verify", help="Prove that what was learned is still true.")
    verify.add_argument("action", choices=("run", "list", "coverage", "new"))
    verify.add_argument("name", nargs="?", default=None)
    verify.add_argument("--kind", default=None,
                        choices=("skill", "capability", "agent", "memory"))
    verify.add_argument("--target", default=None)
    verify.add_argument("--claim", default=None)
    verify.add_argument("--source-file", default=None)
    verify.add_argument("--layer", default=None)
    verify.add_argument("--overwrite", action="store_true")
    verify.set_defaults(func=cmd_verify)

    complexity = add("complexity", help="Measure task complexity and the model level it needs.")
    complexity.add_argument("action", choices=("reassess", "agent", "task"))
    complexity.add_argument("target", nargs="?", default=None)
    complexity.set_defaults(func=cmd_complexity)

    serve = add("serve", help="Run the MCP server.")
    serve.add_argument("--transport", choices=("stdio", "http"), default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=10000)
    serve.add_argument("--no-setup", action="store_true")
    serve.set_defaults(func=cmd_serve)

    # Delegated wholesale: these have their own rich argument sets, and
    # re-declaring them here would be two parsers to keep in step.
    for name, module, help_text in (
        ("configure-mcp", "phronix.mcp_setup", "Register the MCP server with each harness."),
        ("configure-harness", "phronix.harness_models", "Choose model providers per harness."),
        ("contribute", "phronix.contribute", "Promote local learning into the bundled layer."),
        ("bootstrap", "phronix.bootstrap", "Create the project layer and wire instructions."),
    ):
        delegated = add(name, help=help_text, add_help=False)
        delegated.add_argument("rest", nargs=argparse.REMAINDER)
        delegated.set_defaults(func=_delegate(module))

    return parser


def _delegate(module_name: str):
    def run(args: argparse.Namespace) -> int:
        module = __import__(module_name, fromlist=["main"])
        saved = sys.argv
        sys.argv = [module_name.rsplit(".", 1)[-1], *args.rest]
        try:
            module.main()
            return 0
        except SystemExit as exc:
            return int(exc.code or 0)
        finally:
            sys.argv = saved

    return run


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"phronix {args.command}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

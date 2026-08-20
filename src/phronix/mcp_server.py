#!/usr/bin/env python3
"""The phronix MCP server — stdio (default) or streamable HTTP.

    phronix-mcp-server                              # stdio, for a harness to spawn
    phronix-mcp-server --transport http --port 10000  # one shared server

Two things happen before the server serves anything, and both are deliberate.

**Self-heal on start.** Skills are re-linked, agent files re-rendered,
permissions and hooks re-synced. Every one of those steps compares actual
content rather than trusting a "we did this already" state file, because the
failure they exist to catch — a deleted directory, a stale symlink, a rendered
file left behind by an older version — is exactly the failure a state file
reports as fine. The cost is a handful of stat calls per start.

**Load learned capabilities.** MCP tools authored at runtime are imported from
the layered store and registered alongside the built-in ones, so a tool the
system built for itself last session is available this session with no install
step. One broken capability is reported and skipped, never fatal: a self-building
system whose own learning can brick it is worse than one that learns nothing.

The startup sequence deliberately does NOT reconfigure the user's harness MCP
settings. Rewriting someone's config every time a server boots is a side effect
they did not ask for; that belongs to ``phronix init`` / ``phronix-configure-mcp``.
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List

SERVER_NAME = "phronix"


def run_startup_setup(target_root: str = "", quiet: bool = False) -> Dict[str, Any]:
    """Re-link skills, re-render agents, re-sync permissions and hooks.

    Ordered by dependency: skills and agents first (they are what the other steps
    describe), then permissions (whose MCP allowlist is discovered from the tools
    that exist), then hooks. Every step is independently guarded — one failing
    step must not stop the others, since a server with stale hooks is far more
    useful than no server.

    Progress goes to stderr, never stdout: in stdio transport, stdout IS the MCP
    protocol channel and a stray print corrupts the session's first message.
    """
    from phronix.agents import ensure_agents_setup
    from phronix.hooks import ensure_hooks_setup
    from phronix.permissions import ensure_permissions_setup
    from phronix.skills import ensure_skills_setup

    root = target_root or None
    steps = (
        ("skills", ensure_skills_setup),
        ("agents", ensure_agents_setup),
        ("permissions", ensure_permissions_setup),
        ("hooks", ensure_hooks_setup),
    )
    results: Dict[str, Any] = {}
    for label, step in steps:
        try:
            outcome = step(target_root=root)
            results[label] = outcome.get("status", "ok")
        except Exception as exc:
            results[label] = f"error: {type(exc).__name__}: {exc}"
        if not quiet:
            print(f"[phronix] {label:12s} {results[label]}", file=sys.stderr)

    try:
        from phronix.memory import reindex_all

        results["memory_index"] = len(reindex_all())
    except Exception as exc:
        results["memory_index"] = f"error: {exc}"

    # Verification coverage is reported, never enforced, at startup. Refusing to
    # serve because a lesson lacks a verifier would make the framework's own
    # discipline the thing that blocks work — and would push people to disable it.
    # Surfacing the gap on every start is what keeps it from being forgotten.
    try:
        from phronix.verification import coverage

        report = coverage()
        results["verification"] = {
            "covered": report["covered"],
            "uncovered": report["uncovered"],
            "percent": report["percent"],
        }
        if not quiet:
            gap = report["uncovered"]
            print(f"[phronix] {'verification':12s} {report['covered']}/{report['total_artifacts']} "
                  f"artifacts verified ({report['percent']}%)"
                  + (f" — {gap} unverified, run verify_coverage()" if gap else ""),
                  file=sys.stderr)
            if report["orphaned_verifiers"]:
                print(f"[phronix] orphaned verifiers (target no longer exists): "
                      f"{', '.join(report['orphaned_verifiers'])}", file=sys.stderr)
    except Exception as exc:
        results["verification"] = f"error: {exc}"

    return results


def build_server(quiet: bool = False) -> Any:
    """Construct the FastMCP server with built-in tools, capabilities and middleware."""
    from fastmcp import FastMCP

    from phronix.capabilities import load_all
    from phronix.context_middleware import install
    from phronix.mcp_tools import register_all

    server = FastMCP(SERVER_NAME)

    builtin = register_all(server)
    for failure in builtin["failed"]:
        print(f"[phronix] service FAILED {failure['service']}: {failure['error']}",
              file=sys.stderr)

    learned = load_all(server)
    for failure in learned["failed"]:
        # Named loudly: a capability that silently stops loading looks to the next
        # session like a tool that never existed, and it will be rewritten.
        print(f"[phronix] capability FAILED {failure['name']} ({failure['file']}): "
              f"{failure['error']}", file=sys.stderr)

    if not quiet:
        print(f"[phronix] services={len(builtin['loaded'])} "
              f"capabilities={len(learned['loaded'])}"
              + (f" failed={len(learned['failed'])}" if learned["failed"] else ""),
              file=sys.stderr)

    return install(server)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="phronix-mcp-server",
        description="Serve the phronix skills, memory, graph, privacy and capability "
                    "tools over MCP.",
    )
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio",
                        help="stdio (default) is spawned per harness; http serves "
                             "one shared instance.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--target", default="",
                        help="Workspace root for the startup self-heal "
                             "(default: detected project root).")
    parser.add_argument("--no-setup", action="store_true",
                        help="Skip the startup self-heal (faster start; leaves stale "
                             "rendered agent files and skill links in place).")
    parser.add_argument("--quiet", action="store_true", help="Suppress startup progress.")
    args = parser.parse_args(argv)

    if not args.no_setup:
        run_startup_setup(args.target, quiet=args.quiet)

    try:
        server = build_server(quiet=args.quiet)
    except ImportError as exc:
        print(f"phronix-mcp-server: {exc}\nInstall the dependencies: pip install -U phronix",
              file=sys.stderr)
        return 1

    if args.transport == "http":
        if not args.quiet:
            print(f"[phronix] http://{args.host}:{args.port}/mcp", file=sys.stderr)
        server.run(transport="http", host=args.host, port=args.port)
    else:
        server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

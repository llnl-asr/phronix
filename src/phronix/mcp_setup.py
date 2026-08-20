"""Register the phronix MCP server with every harness's config.

Each harness spells the same idea — "here is an MCP server, use it" — in a
different file and a different dialect:

============  ================================  ==================================
harness       file                              key
============  ================================  ==================================
claude        ``.mcp.json``                     ``mcpServers.phronix``
              ``.claude/settings.json``         ``enabledMcpjsonServers``
opencode      ``.opencode/opencode.jsonc``      ``mcp.phronix``
copilot       ``.vscode/mcp.json``              ``servers.phronix``
codex         ``.codex/config.toml``            ``[mcp_servers.phronix]``
============  ================================  ==================================

Two transports, and the choice is not cosmetic:

**stdio** (default)
    Each harness spawns its own private server process. Simplest to configure,
    no ports, works everywhere — and the right default because a user who just
    ran ``pip install phronix`` should get a working setup with no daemon to
    remember to start.

**http**
    One shared server the harnesses connect to. Use this when several harnesses
    (or several concurrent sessions) should share one process — notably so they
    share one in-memory context-dedup state rather than each re-injecting the
    same standing rules.

Every write is a *merge*: these files belong to the user, and clobbering an
unrelated MCP server they had configured is not an acceptable side effect of
installing ours.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

MCP_SERVER_NAME = "phronix"

#: The console script a stdio config spawns. Resolved on PATH at launch time
#: rather than pinned to an absolute path, so a venv rebuild does not leave every
#: harness pointing at a deleted interpreter.
STDIO_COMMAND = "phronix-mcp-server"


def _url(host: str, port: int, path: str = "/mcp") -> str:
    return f"http://{host}:{port}{path.rstrip('/') or '/mcp'}"


def _server_entry(transport: str, host: str, port: int) -> Dict[str, Any]:
    if transport == "http":
        return {"type": "http", "url": _url(host, port)}
    return {"command": STDIO_COMMAND, "args": []}


def _merge_json(path: Path, mutate, dry_run: bool = False) -> str:
    """Read a JSON file, apply *mutate*, write it back only if it changed."""
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return "skipped_unreadable"
    if not isinstance(data, dict):
        return "skipped_unexpected_shape"
    before = json.dumps(data, sort_keys=True)
    mutate(data)
    if json.dumps(data, sort_keys=True) == before:
        return "already_current"
    if dry_run:
        return "would_update"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "updated"


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------

def configure_claude(root: Path, entry: Dict[str, Any], dry_run: bool = False) -> Dict[str, str]:
    """Write ``.mcp.json`` and enable the server in ``.claude/settings.json``.

    Both files are needed: ``.mcp.json`` declares the server, and
    ``enabledMcpjsonServers`` is what stops Claude Code prompting for approval on
    every session start. Declaring without enabling looks configured and behaves
    as if it were not.
    """
    def set_server(data: Dict[str, Any]) -> None:
        data.setdefault("mcpServers", {})[MCP_SERVER_NAME] = entry

    def enable(data: Dict[str, Any]) -> None:
        enabled = data.setdefault("enabledMcpjsonServers", [])
        if isinstance(enabled, list) and MCP_SERVER_NAME not in enabled:
            enabled.append(MCP_SERVER_NAME)

    return {
        ".mcp.json": _merge_json(root / ".mcp.json", set_server, dry_run),
        ".claude/settings.json": _merge_json(
            root / ".claude" / "settings.json", enable, dry_run),
    }


# ---------------------------------------------------------------------------
# VS Code / Copilot
# ---------------------------------------------------------------------------

def configure_vscode(root: Path, entry: Dict[str, Any], dry_run: bool = False) -> str:
    def mutate(data: Dict[str, Any]) -> None:
        data.setdefault("servers", {})[MCP_SERVER_NAME] = entry

    return _merge_json(root / ".vscode" / "mcp.json", mutate, dry_run)


# ---------------------------------------------------------------------------
# OpenCode
# ---------------------------------------------------------------------------

def configure_opencode(root: Path, transport: str, host: str, port: int,
                       dry_run: bool = False) -> str:
    """Write ``mcp.phronix`` into ``.opencode/opencode.jsonc``.

    OpenCode's MCP entry has its own shape — ``type: local`` with a ``command``
    ARRAY, or ``type: remote`` with a ``url`` — rather than the Claude-style
    ``command``/``args`` split, so the shared entry is reshaped here.
    """
    from phronix.permissions import _strip_jsonc

    path = root / ".opencode" / "opencode.jsonc"
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            parsed = json.loads(_strip_jsonc(path.read_text()))
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            return "skipped_unreadable"

    entry: Dict[str, Any] = (
        {"type": "remote", "url": _url(host, port), "enabled": True}
        if transport == "http"
        else {"type": "local", "command": [STDIO_COMMAND], "enabled": True}
    )
    if data.get("mcp", {}).get(MCP_SERVER_NAME) == entry:
        return "already_current"
    if dry_run:
        return "would_update"

    data.setdefault("$schema", "https://opencode.ai/config.json")
    data.setdefault("mcp", {})[MCP_SERVER_NAME] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "updated"


# ---------------------------------------------------------------------------
# Codex CLI
# ---------------------------------------------------------------------------

_CODEX_MARK = "# phronix: MCP server registration"


def configure_codex(root: Path, transport: str, host: str, port: int,
                    dry_run: bool = False) -> str:
    """Append (or refresh) the ``[mcp_servers.phronix]`` table in ``.codex/config.toml``.

    Edited textually rather than through a TOML round-trip: Codex's config is
    hand-written and comment-heavy, and a round-trip would silently reformat and
    strip the user's own annotations. Our block is delimited by a marker so it
    can be replaced in place without touching anything else.
    """
    path = root / ".codex" / "config.toml"
    block = (
        f"{_CODEX_MARK}\n"
        f"[mcp_servers.{MCP_SERVER_NAME}]\n"
        + (f'url = "{_url(host, port)}"\n' if transport == "http"
           else f'command = "{STDIO_COMMAND}"\nargs = []\n')
    )

    text = path.read_text() if path.exists() else ""
    if _CODEX_MARK in text:
        start = text.index(_CODEX_MARK)
        # Our block runs to the next table header that is not ours, or to EOF.
        rest = text[start + len(_CODEX_MARK):]
        offset = rest.find("\n[")
        while offset != -1 and rest[offset + 1:].startswith(f"[mcp_servers.{MCP_SERVER_NAME}]"):
            offset = rest.find("\n[", offset + 1)
        end = start + len(_CODEX_MARK) + (offset + 1 if offset != -1 else len(rest))
        updated = text[:start] + block + text[end:]
    else:
        updated = (text.rstrip("\n") + "\n\n" if text.strip() else "") + block

    if updated == text:
        return "already_current"
    if dry_run:
        return "would_update"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated)
    return "updated"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def configure_all(
    target_root: Optional[Path] = None,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 10000,
    harnesses: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    from phronix.layers import project_root

    root = Path(target_root) if target_root else (project_root() or Path.cwd())
    entry = _server_entry(transport, host, port)
    wanted = set(harnesses or ("claude", "opencode", "copilot", "codex"))
    results: Dict[str, Any] = {"target": str(root), "transport": transport}

    if "claude" in wanted:
        results["claude"] = configure_claude(root, entry, dry_run)
    if "copilot" in wanted:
        results["copilot"] = configure_vscode(root, entry, dry_run)
    if "opencode" in wanted:
        results["opencode"] = configure_opencode(root, transport, host, port, dry_run)
    if "codex" in wanted:
        results["codex"] = configure_codex(root, transport, host, port, dry_run)

    def statuses(value: Any) -> List[str]:
        return list(value.values()) if isinstance(value, dict) else [str(value)]

    changed = [
        key for key, value in results.items()
        if key not in ("target", "transport") and "updated" in statuses(value)
    ]
    results["changed"] = changed
    results["summary"] = (f"{len(changed)} harness MCP config(s) updated" if changed
                          else "all harness MCP configs already current")
    return results


def ensure_mcp_setup(target_root: Optional[Path] = None, force: bool = False) -> Dict[str, Any]:
    """Startup self-heal step.

    Deliberately NOT run by default on server start — see
    :func:`phronix.mcp_server.run_startup_setup`. Rewriting a user's harness
    configs every time a server boots is a side effect they did not ask for; this
    is called by ``phronix init`` and ``phronix-configure-mcp`` instead.
    """
    result = configure_all(target_root=target_root)
    return {"status": "installed" if result["changed"] or force else "already_done", **result}


def main() -> None:
    """Entry point for ``phronix-configure-mcp``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="phronix-configure-mcp",
        description="Register the phronix MCP server with Claude Code, OpenCode, "
                    "Copilot (VS Code) and Codex.",
    )
    parser.add_argument("--target", default=None,
                        help="Project root (default: detected project root, else cwd).")
    parser.add_argument("--transport", choices=("stdio", "http"), default="stdio",
                        help="stdio spawns a private server per harness (default); "
                             "http points every harness at one shared server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--harness", action="append", default=None,
                        choices=("claude", "opencode", "copilot", "codex"),
                        help="Restrict to one harness (repeatable).")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.target).expanduser().resolve() if args.target else None
    result = configure_all(root, args.transport, args.host, args.port,
                           args.harness, args.dry_run)
    print(f"Target:    {result['target']}")
    print(f"Transport: {result['transport']}")
    for key, value in result.items():
        if key in ("target", "transport", "changed", "summary"):
            continue
        if isinstance(value, dict):
            for file, status in value.items():
                print(f"  {key:9s} {status:20s} {file}")
        else:
            print(f"  {key:9s} {value}")
    print(result["summary"])
    if args.transport == "http":
        print(f"\nStart the shared server:  phronix-mcp-server --transport http "
              f"--host {args.host} --port {args.port}")


if __name__ == "__main__":
    main()

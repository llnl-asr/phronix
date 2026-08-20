"""Render one harness-neutral permission policy into each harness's dialect.

The canonical policy is ``<layer>/workspace/permissions.yaml`` — a single
document describing which paths may be written without asking, which commands
are denied outright, and which MCP tools are pre-approved. Highest-precedence
layer wins *wholesale*: a permission policy is a single coherent statement about
risk, and merging two of them field-by-field produces a policy nobody wrote and
nobody reviewed.

Per-harness reality:

``claude``
    ``.claude/settings.json`` → ``permissions.allow`` / ``permissions.deny``.
    Deny always wins, and anything unlisted falls through to Claude's own "ask"
    default — so the policy's ``ask`` tier is a deliberate no-op here rather than
    an explicit rule.
``opencode``
    ``.opencode/opencode.jsonc`` → the top-level ``permission`` block, a glob map
    evaluated in order where LAST MATCH WINS. The catch-all is therefore emitted
    first and the specific overrides after — the opposite of Claude's ordering.
``copilot``
    Not applicable. Copilot custom agents have no path- or command-scoped
    permission mechanism at all; the only boundary is the per-agent ``tools:``
    allowlist that :mod:`phronix.agent_templates` already renders.
``codex``
    Not settable from a repo-tracked file. Codex ignores ``sandbox_mode`` and
    ``approval_policy`` in project-scoped config as an anti-supply-chain-attack
    measure, so the rendered agents carry a fixed ``sandbox_mode`` instead and
    the trust level is left to the user's own global config.

The MCP tool allowlist is *discovered*, not hand-maintained: :func:`discover_mcp_tool_names`
statically scans for ``@…tool()``-decorated functions, including runtime-authored
capabilities. A hand-written list drifts the moment a capability is added, and
drift here shows up as a permission prompt in the middle of an unattended run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_TOOL_DEF_RE = re.compile(r"@[A-Za-z_][A-Za-z0-9_.]*\.tool\(\)\s*def\s+(\w+)\s*\(")

#: The MCP server name tool permissions are namespaced under.
MCP_SERVER_NAME = "phronix"

#: Used when no ``permissions.yaml`` is found, so a fresh install still renders a
#: safe policy rather than an empty (i.e. wide-open-looking) one.
_FALLBACK_POLICY: Dict[str, Any] = {
    "paths": [{"glob": "**", "mode": "ask"}],
    "deny_write_prefixes": ["/etc/*", "/usr/*", "/var/*", "/boot/*", "/root/*"],
    "bash": {"deny": ["sudo *", "sudo", "rm -rf /*", "rm -rf ~*"], "allow": []},
    "path_scoped_tools": {"edit": "tiers", "read": "allow_only"},
}


def policy_path() -> Optional[Path]:
    """The highest-precedence ``permissions.yaml`` across layers, or ``None``."""
    from phronix.layers import layers

    found = None
    for layer in layers():
        candidate = layer.root / "workspace" / "permissions.yaml"
        if candidate.is_file():
            found = candidate
    return found


def load_policy() -> Dict[str, Any]:
    path = policy_path()
    if path is None:
        return dict(_FALLBACK_POLICY)
    try:
        import yaml

        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else dict(_FALLBACK_POLICY)
    except Exception:
        return dict(_FALLBACK_POLICY)


def _tool_names_in(source: str) -> List[str]:
    """Tool names registered in *source*, found by parsing rather than matching.

    An AST walk, not a regex, because a regex cannot tell code from a docstring.
    The tool docstrings in this package contain illustrative ``@mcp.tool()``
    examples, and a regex scan dutifully added those to the permission allowlist —
    pre-approving tools that do not exist, which is both wrong and the kind of
    error nobody notices because it never fails loudly.

    Falls back to the regex when a file does not parse, so a syntactically broken
    capability still contributes what can be recovered instead of nothing.
    """
    import ast

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return [m.group(1) for m in _TOOL_DEF_RE.finditer(source)]

    names: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            # Matches `@mcp.tool()` and the mounted form `@self.<x>.tool()`.
            call = decorator.func if isinstance(decorator, ast.Call) else decorator
            if isinstance(call, ast.Attribute) and call.attr == "tool":
                names.append(node.name)
                break
    return names


def discover_mcp_tool_names() -> List[str]:
    """Every tool name the built-in services and learned capabilities register.

    Statically determined — no server boot — so the allowlist this drives cannot
    silently fall behind what is actually registered, the way a hand-maintained
    list does the moment a capability is added.
    """
    from phronix.layers import capability_files

    names: List[str] = []
    tools_dir = Path(__file__).resolve().parent / "mcp_tools"
    sources = list(tools_dir.rglob("*.py")) if tools_dir.is_dir() else []
    sources += list(capability_files().values())
    for path in sorted(sources):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for name in _tool_names_in(text):
            if name not in names:
                names.append(name)
    return sorted(names)


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------

def _claude_glob(glob: str) -> str:
    """Convert a policy glob into Claude Code's dialect.

    This policy and OpenCode use ``**``; Claude's permission patterns use a
    single trailing ``*``. Without the conversion ``Edit(.phronix/**)`` matches
    nothing at all — a rule that looks present in the settings file, reads
    correctly, and silently never fires.
    """
    return glob[:-len("/**")] + "/*" if glob.endswith("/**") else glob


def _mcp_tool_names(policy: Dict[str, Any]) -> List[str]:
    """The MCP tools the policy pre-approves, in Claude's naming.

    ``all_phronix`` means "whatever the server registers", discovered rather
    than listed — a hand-maintained list drifts the moment a capability is
    added, and the drift surfaces as a permission prompt mid-run.
    """
    setting = policy.get("mcp_tools")
    if setting == "all_phronix":
        return [f"mcp__{MCP_SERVER_NAME}__{name}" for name in discover_mcp_tool_names()]
    if isinstance(setting, list):
        return [str(name) for name in setting]
    return []


def render_claude(policy: Dict[str, Any]) -> Dict[str, List[str]]:
    """Build Claude's ``permissions`` object from the neutral policy."""
    allow: List[str] = []
    deny: List[str] = []

    for entry in policy.get("paths") or []:
        glob = str(entry.get("glob", ""))
        mode = str(entry.get("mode", "ask"))
        if not glob or glob == "**":
            continue  # the catch-all IS Claude's default; emitting it changes nothing
        pattern = _claude_glob(glob)
        if mode == "allow":
            allow.extend([f"Edit({pattern})", f"Write({pattern})", f"Read({pattern})"])
        elif mode == "deny":
            deny.extend([f"Edit({pattern})", f"Write({pattern})"])

    for prefix in policy.get("deny_write_prefixes") or []:
        deny.append(f"Write({prefix})")

    bash = policy.get("bash") or {}
    deny.extend(f"Bash({rule})" for rule in bash.get("deny") or [])
    allow.extend(f"Bash({rule})" for rule in bash.get("allow") or [])
    allow.extend(_mcp_tool_names(policy))

    # De-duplicate while preserving order: a repeated rule is harmless but makes
    # the rendered file noisy and its diffs unreadable.
    return {
        "allow": list(dict.fromkeys(allow)),
        "deny": list(dict.fromkeys(deny)),
    }


def sync_claude_permissions(root: Path) -> str:
    """Merge the rendered permissions into ``.claude/settings.json``.

    Replaces only the ``permissions`` key. Other keys — env, hooks, MCP server
    enablement — belong to other syncs and to the user, and must survive.
    """
    path = Path(root) / ".claude" / "settings.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return "skipped_unreadable_settings"
    if not isinstance(data, dict):
        return "skipped_unexpected_shape"

    rendered = render_claude(load_policy())
    if data.get("permissions") == rendered:
        return "already_current"
    data["permissions"] = rendered
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return "updated"


# ---------------------------------------------------------------------------
# OpenCode
# ---------------------------------------------------------------------------

def render_opencode(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Build OpenCode's ``permission`` block.

    Order matters and is the reverse of Claude's: OpenCode evaluates the glob map
    in order with LAST MATCH WINS, so the catch-all goes first and the specific
    overrides after it. Emitting them the other way round silently makes the
    whole policy a single "ask everything" rule.
    """
    path_scoped = policy.get("path_scoped_tools") or {}
    tiers = policy.get("paths") or []
    out: Dict[str, Any] = {}

    for tool, coverage in path_scoped.items():
        if coverage not in ("tiers", "allow_only"):
            # Loud, because the quiet alternative is a tool rendered with no
            # rules at all — which reads as "no policy" and behaves as
            # "whatever the harness defaults to".
            raise ValueError(
                f"permissions.yaml: path_scoped_tools.{tool} must be 'tiers' or "
                f"'allow_only', got {coverage!r}")
        rules: Dict[str, str] = {}
        for entry in tiers:
            glob = str(entry.get("glob", ""))
            mode = str(entry.get("mode", "ask"))
            if not glob:
                continue
            if coverage == "allow_only" and mode != "allow":
                continue
            rules[glob] = mode
        if rules:
            out[str(tool)] = rules

    bash = policy.get("bash") or {}
    bash_rules: Dict[str, str] = {"*": "ask"}
    # Allow first, deny second: last match wins, so a denied pattern that also
    # matches an allow rule must be listed after it to actually deny.
    for rule in bash.get("allow") or []:
        bash_rules[str(rule)] = "allow"
    for rule in bash.get("deny") or []:
        bash_rules[str(rule)] = "deny"
    out["bash"] = bash_rules

    # MCP tools. OpenCode ids a tool as sanitize(server) + "_" + sanitize(tool)
    # and matches a permission NAME with the same anchored wildcard matcher it
    # uses for patterns, so one glob covers every tool exactly.
    setting = policy.get("mcp_tools")
    if setting == "all_phronix":
        out[f"{MCP_SERVER_NAME}_*"] = "allow"
    elif isinstance(setting, list):
        for name in setting:
            tool = str(name).split(f"mcp__{MCP_SERVER_NAME}__", 1)[-1]
            out[f"{MCP_SERVER_NAME}_{re.sub(r'[^a-zA-Z0-9_-]', '_', tool)}"] = "allow"
    return out


def _strip_jsonc(text: str) -> str:
    """Remove ``//`` and ``/* */`` comments so a JSONC file can be parsed.

    String-aware: a ``//`` inside a quoted value (a URL, most often) is content,
    not a comment, and stripping it corrupts the config.
    """
    out: List[str] = []
    i, n = 0, len(text)
    in_string = False
    while i < n:
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
            continue
        if char == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if char == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(char)
        i += 1
    return "".join(out)


def sync_opencode_permissions(root: Path) -> str:
    """Write the ``permission`` block into ``.opencode/opencode.jsonc``.

    Comments in an existing file are not preserved: rewriting JSONC while keeping
    comments attached to the right keys requires a full round-tripping parser,
    and a subtly misplaced comment in a permission policy is worse than no
    comment. The file is regenerated from the policy, which is where the
    explanatory comments belong anyway.
    """
    path = Path(root) / ".opencode" / "opencode.jsonc"
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            parsed = json.loads(_strip_jsonc(path.read_text()))
            if isinstance(parsed, dict):
                data = parsed
        except Exception:
            return "skipped_unreadable_config"

    rendered = render_opencode(load_policy())
    if data.get("permission") == rendered:
        return "already_current"
    data.setdefault("$schema", "https://opencode.ai/config.json")
    data["permission"] = rendered
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Generated in part by phronix.permissions — the `permission` block is\n"
        "// rendered from workspace/permissions.yaml. Run `phronix sync permissions`\n"
        "// after editing that policy.\n"
        + json.dumps(data, indent=2) + "\n"
    )
    return "updated"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def sync_permissions(target_root: Optional[Path] = None) -> Dict[str, Any]:
    from phronix.layers import project_root

    root = Path(target_root) if target_root else (project_root() or Path.cwd())
    results = {
        "target": str(root),
        "policy": str(policy_path() or "(built-in fallback)"),
        "claude": sync_claude_permissions(root),
        "opencode": sync_opencode_permissions(root),
        "copilot": "not_applicable",
        "codex": "not_applicable",
    }
    changed = [h for h in ("claude", "opencode") if results[h] == "updated"]
    results["changed"] = changed
    results["summary"] = (f"{len(changed)} harness permission file(s) updated"
                          if changed else "all harness permissions already current")
    return results


def ensure_permissions_setup(
    target_root: Optional[Path] = None, force: bool = False
) -> Dict[str, Any]:
    """Startup self-heal step."""
    result = sync_permissions(target_root)
    return {"status": "installed" if result["changed"] or force else "already_done", **result}


def main() -> None:
    """Entry point for ``phronix-sync-permissions``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="phronix-sync-permissions",
        description="Render the harness-neutral permission policy into each harness's dialect.",
    )
    parser.add_argument("--target", default=None,
                        help="Project root (default: detected project root, else cwd).")
    parser.add_argument("--show", action="store_true",
                        help="Print the rendered policy without writing it.")
    args = parser.parse_args()

    if args.show:
        policy = load_policy()
        print(f"policy: {policy_path() or '(built-in fallback)'}")
        print("\nclaude:")
        print(json.dumps(render_claude(policy), indent=2))
        print("\nopencode:")
        print(json.dumps(render_opencode(policy), indent=2))
        return

    root = Path(args.target).expanduser().resolve() if args.target else None
    result = sync_permissions(root)
    print(f"Target: {result['target']}")
    print(f"Policy: {result['policy']}")
    for harness in ("claude", "opencode", "copilot", "codex"):
        print(f"  {harness:9s} {result[harness]}")
    print(result["summary"])


if __name__ == "__main__":
    main()

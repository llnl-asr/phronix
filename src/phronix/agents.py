"""Render the YAML agent templates into every harness's discovery path.

:mod:`phronix.agent_templates` turns a template into text. This module is the
filesystem side: it writes each rendered file where the harness looks for it,

    claude    <root>/.claude/agents/<name>.md
    opencode  <root>/.opencode/agents/<name>.md
    copilot   <root>/.github/agents/<name>.agent.md
    codex     <root>/.codex/agents/<name>.toml

and it self-heals — a rendered file that was deleted, hand-edited, or left stale
by a model-map change is regenerated on the next sync.

The rendered files are build artifacts: gitignored, stamped with a generation
marker, and never merged back. Track changes in the YAML templates only. The
marker is also how :func:`_is_ours` tells a file we own (safe to overwrite) from
a user's own agent that happens to share a name (never touched).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from phronix.agent_templates import HARNESSES, render_all

#: Substring identifying a file this module generated, in every dialect.
_MARKER = "# generated-by: phronix"


def _is_ours(dest: Path) -> bool:
    """True when *dest* is a phronix-rendered agent we may overwrite."""
    try:
        if dest.is_symlink():
            # A legacy layout that symlinked straight into the template tree.
            from phronix.layers import which_layer

            return which_layer(dest.resolve()) is not None
        return dest.is_file() and _MARKER in dest.read_text(errors="replace")
    except OSError:
        return False


def install_agents(
    target_root: Optional[Path] = None,
    harnesses: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Render every visible template into each harness's agents directory.

    Idempotent and merge-safe: a file already matching what we would render is
    left untouched, a stale copy we own is refreshed, and a name colliding with
    an unrelated user file is reported as a conflict and never overwritten.
    """
    from phronix.layers import project_root

    root = Path(target_root) if target_root else (project_root() or Path.cwd())
    rendered = render_all(target_root=root, harnesses=harnesses)

    installed: List[Dict[str, str]] = []
    conflicts: List[str] = []
    dirs: List[str] = []

    for harness, files in rendered.items():
        for rel, content in files.items():
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if str(dest.parent) not in dirs:
                dirs.append(str(dest.parent))

            # If the agents directory itself is a leftover symlink into the
            # template tree, replace it with a real directory before writing.
            if dest.parent.is_symlink():
                dest.parent.unlink()
                dest.parent.mkdir(parents=True)

            try:
                current = dest.read_text(errors="replace") if dest.is_file() else None
            except OSError:
                current = None

            if current == content:
                installed.append({"harness": harness, "name": dest.name,
                                  "action": "already_installed"})
                continue
            if (dest.exists() or dest.is_symlink()) and not _is_ours(dest):
                conflicts.append(str(dest))
                continue

            action = "refreshed" if (dest.exists() or dest.is_symlink()) else "installed"
            if dest.is_symlink():
                dest.unlink()
            dest.write_text(content)
            installed.append({"harness": harness, "name": dest.name, "action": action})

    return {"target": str(root), "dirs": dirs, "installed": installed, "conflicts": conflicts}


#: Template key order. Fixed so a re-render never reshuffles the file and a diff
#: shows only what actually changed.
_TEMPLATE_KEY_ORDER = ("name", "description", "model_level", "effort", "isolation",
                       "tools", "skills", "sections")


def define_agent(
    name: str,
    description: str,
    model_level: str,
    sections: List[Dict[str, str]],
    tools: Optional[List[str]] = None,
    skills: Optional[List[str]] = None,
    effort: str = "",
    isolation: str = "",
    layer: Optional[str] = None,
    sync: bool = True,
) -> Dict[str, Any]:
    """Create or update an agent template declaratively. Idempotent.

    The arguments fully determine the YAML: keys in a fixed order, sections in the
    order given, block scalars for bodies. The same input produces a byte-identical
    template on any machine, so re-running is a no-op that reports ``unchanged``.

    ``sections`` entries are either ``{"include": "<shared-section>"}`` or
    ``{"title": ..., "body": ...}``. Includes are validated against the shared
    section library before anything is written — an unresolved include breaks
    rendering for all four harnesses at once, and finding that out at sync time
    means the authoring session has already ended.

    The template is validated and run through the built-in structural corrector
    before it is written, so a broken agent is rejected now rather than becoming a
    rendered file that misbehaves silently.
    """
    import re

    import yaml

    from phronix.agent_templates import load_common_sections, load_template
    from phronix.layers import resolve_write_layer, skill_dirs
    from phronix.privacy import anonymize, current_users

    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    if not slug:
        return {"status": "error", "error": "name must contain letters or digits"}
    if not re.fullmatch(r"level_[0-9]+", str(model_level)):
        return {"status": "error",
                "error": f"model_level must look like level_N, got {model_level!r}. "
                         "Never pin a model id: the level is what lets one definition "
                         "run on all four harnesses."}
    if not sections:
        return {"status": "error", "error": "an agent needs at least one section"}

    common = load_common_sections()
    unknown = [s["include"] for s in sections
               if isinstance(s, dict) and s.get("include") and s["include"] not in common]
    if unknown:
        return {"status": "error",
                "error": f"unknown shared section(s) {unknown}; known: "
                         f"{', '.join(sorted(common))}"}

    missing_skills = [s for s in (skills or []) if s not in skill_dirs()]
    if missing_skills:
        return {"status": "error",
                "error": f"declares skill(s) {missing_skills} that do not exist; the agent "
                         "would be told to load something that is not there"}

    users = current_users()
    payload: Dict[str, Any] = {
        "name": slug,
        "description": anonymize(description, extra_users=users).strip(),
        "model_level": model_level,
    }
    if effort:
        payload["effort"] = effort
    if isolation:
        payload["isolation"] = isolation
    if tools:
        payload["tools"] = list(tools)
    if skills:
        payload["skills"] = list(skills)

    rendered_sections: List[Dict[str, str]] = []
    for entry in sections:
        if entry.get("include"):
            rendered_sections.append({"include": str(entry["include"])})
        else:
            rendered_sections.append({
                "title": anonymize(str(entry.get("title", "")), extra_users=users).strip(),
                "body": anonymize(str(entry.get("body", "")), extra_users=users).rstrip() + "\n",
            })
    payload["sections"] = rendered_sections

    ordered = {k: payload[k] for k in _TEMPLATE_KEY_ORDER if k in payload}
    text = yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True,
                          width=88, default_flow_style=False)

    target = resolve_write_layer(layer)
    directory = target.dir("agents")
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug}.yaml"

    existed = path.exists()
    if existed and path.read_text() == text:
        action = "unchanged"
    else:
        path.write_text(text)
        action = "updated" if existed else "created"

    # Validate what we just wrote, by loading it back through the same parser the
    # renderers use. A template that writes but does not load is the worst outcome:
    # it looks successful and breaks the next sync.
    try:
        load_template(path, common)
    except Exception as exc:
        return {"status": "error", "file": str(path),
                "error": f"template written but does not validate: {exc}"}

    from phronix.correctors import correct

    result = {
        "status": "ok", "action": action, "agent": slug, "layer": target.name,
        "file": str(path), "corrector": correct("agent", slug),
    }
    if sync and action != "unchanged":
        try:
            result["sync"] = sync_agents()
        except Exception as exc:
            result["sync"] = {"error": f"{type(exc).__name__}: {exc}"}
        result["next"] = "Ask the user to reload the harness so it picks up the new file."
    return result


def sync_agents(target_root: Optional[Path] = None) -> Dict[str, Any]:
    """Re-render every harness copy from the templates — one-way and lossless.

    This is what the ``agents_sync`` MCP tool calls after a self-learning edit to
    a template or to ``common-sections.yaml``. Templates are the only source of
    truth; rendered copies are never read back.
    """
    result = install_agents(target_root=target_root)
    changed = [i for i in result["installed"] if i["action"] != "already_installed"]
    result["changed"] = changed
    result["summary"] = (
        f"{len(changed)} rendered file(s) updated across {len(HARNESSES)} harnesses"
        if changed else "all rendered agents already current"
    )
    return result


#: The per-harness directories a working tree needs to see.
#:
#: Whatever a harness reads from the project — agent definitions, its MCP
#: server declaration, skills — lives under one directory per harness. Linking
#: the whole directory rather than naming its contents means something added
#: later is picked up without editing this list.
HARNESS_DIRS = {
    "opencode": ".opencode",
    "claude": ".claude",
    "copilot": ".github",
    "codex": ".codex",
}


def link_harness(target: Path, harness: str = "opencode",
                 source_root: Optional[Path] = None) -> Dict[str, Any]:
    """Make the project's harness config visible from another working tree.

    A harness resolves `--agent`, its MCP servers and its skills against the
    directory it was pointed at. Point it at a checked-out repository — which is
    what a benchmark task is — and it finds none of them, then falls back to a
    default and says so only on stderr:

        agent "phronix-healer" is a subagent, not a primary agent.
        Falling back to default agent

    So every invocation silently ran as the default agent, with none of the tool
    scoping its definition describes.

    A SYMLINK rather than a copy, and idempotent. Copies go stale the moment
    `sync_agents` re-renders, and a stale definition fails the same silent way.
    One source of truth means a re-render reaches every linked tree at once, and
    anything added to the harness directory later comes along without this
    function knowing about it.

    A tree with its own directory of that name is left alone: it belongs to the
    repository under test, and overwriting it would change what is being
    measured.
    """
    relative = HARNESS_DIRS.get(harness)
    if not relative:
        return {"status": "unknown-harness", "harness": harness, "linked": False}

    source = Path(source_root or Path(__file__).resolve().parents[2]) / relative
    if not source.is_dir():
        return {"status": "nothing-to-link", "source": str(source), "linked": False}

    destination = Path(target) / relative
    try:
        if destination.is_symlink():
            if destination.resolve() == source.resolve():
                return {"status": "already_linked", "target": str(destination),
                        "source": str(source), "linked": True}
            destination.unlink()
        elif destination.exists():
            return {"status": "occupied", "target": str(destination),
                    "linked": False}
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=True)

        # Keep it out of the tree's own bookkeeping. Harmless where the tree is
        # not a repository.
        exclude = Path(target) / ".git" / "info" / "exclude"
        if exclude.parent.is_dir():
            current = exclude.read_text() if exclude.is_file() else ""
            if f"{relative}/" not in current:
                exclude.write_text(current + f"\n{relative}/\n")
        return {"status": "linked", "target": str(destination),
                "source": str(source), "linked": True}
    except OSError as exc:
        # Falling back to the default agent is how it behaved before this
        # existed; it is not worth failing the caller over.
        return {"status": "failed", "error": str(exc), "linked": False}


def ensure_agents_setup(
    target_root: Optional[Path] = None, force: bool = False
) -> Dict[str, Any]:
    """Startup self-heal step, called by the MCP server before it serves anything.

    No state-file fast path, for the same reason as the skills step: rendering
    compares content directly, which is both cheap and the only check that
    survives someone deleting the output directory.
    """
    result = install_agents(target_root=target_root)
    changed = [i for i in result["installed"] if i["action"] != "already_installed"]
    return {
        "status": "installed" if changed or force else "already_done",
        "changed": changed,
        **result,
    }


def main() -> None:
    """Entry point for ``phronix-install-agents``."""
    import argparse
    import json

    from phronix.layers import agent_templates, project_root

    parser = argparse.ArgumentParser(
        prog="phronix-install-agents",
        description="Render the phronix YAML agent templates into every harness's "
                    "discovery path: .claude/agents/, .opencode/agents/, "
                    ".github/agents/, .codex/agents/.",
    )
    parser.add_argument("--target", default=None,
                        help="Workspace root (default: detected project root, else cwd).")
    parser.add_argument("--harness", choices=[*HARNESSES, "all"], default="all")
    parser.add_argument("--list", action="store_true", help="Print template names and exit.")
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args()

    if args.list:
        from phronix.layers import which_layer

        for name, path in sorted(agent_templates().items()):
            print(f"{which_layer(path) or '?':8s} {Path(name).stem}")
        return

    root = Path(args.target).expanduser().resolve() if args.target else (project_root() or Path.cwd())
    harnesses = None if args.harness == "all" else [args.harness]
    result = install_agents(target_root=root, harnesses=harnesses)

    if args.json:
        print(json.dumps(result, indent=2))
        return
    print(f"Target root: {result['target']}")
    for item in result["installed"]:
        marker = {"installed": "+", "refreshed": "~"}.get(item["action"], "=")
        print(f"  {marker} [{item['harness']}] {item['name']}")
    for conflict in result["conflicts"]:
        print(f"  ! conflict, left alone: {conflict}")


if __name__ == "__main__":
    main()

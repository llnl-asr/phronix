"""The four-level model map, and which concrete model each harness uses per level.

Agents declare a *capability level*, never a model id:

=========  ==========================================================
level_1    deterministic orchestration and tool plumbing
level_2    routing, planning, limited reasoning
level_3    analysis, diagnosis, stage-to-stage decisions
level_4    deep synthesis and cross-cutting reasoning
=========  ==========================================================

That indirection is what lets the same agent definition run on Claude, OpenCode,
Copilot and Codex, and lets a model upgrade be a one-line edit rather than a
sweep through every template.

Two files, with clearly separated jobs:

``.agents/workspace/models.yaml``
    The checked-in map of level → model, per provider. Edited by a human.

``<write-layer>/active-models.json``
    The LIVE choice: which provider each harness is pointed at right now, plus
    Claude's per-level model *class*. Written by ``phronix configure-harness``.
    Kept out of ``models.yaml`` because it is a local decision — pinning it in
    the shared file would make every user's harness choice a diff for everyone.

When the two disagree, ``active-models.json`` wins. ``models.yaml`` is the menu;
``active-models.json`` is the order.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

LEVELS = ("level_1", "level_2", "level_3", "level_4")

#: Harnesses that get a model resolved for them. Claude is handled separately
#: (it takes a model *class* alias rather than a pinned id).
HARNESSES = ("claude", "opencode", "copilot", "codex")

#: Used when ``models.yaml`` is missing or unreadable, so a fresh install still
#: renders working agent files instead of a wall of UNRESOLVED.
_FALLBACK_LEVELS: Dict[str, Dict[str, Any]] = {
    "level_1": {"default": "haiku", "providers": {}},
    "level_2": {"default": "sonnet", "providers": {}},
    "level_3": {"default": "sonnet", "providers": {}},
    "level_4": {"default": "opus", "providers": {}},
}

_DEFAULT_PROVIDER = {
    "claude": "claude",
    "opencode": "ollama",
    "copilot": "copilot",
    "codex": "codex",
}


# ---------------------------------------------------------------------------
# File locations
# ---------------------------------------------------------------------------

def models_yaml_path() -> Optional[Path]:
    """The highest-precedence ``models.yaml`` across layers, or ``None``."""
    from phronix.layers import layers

    found = None
    for layer in layers():
        candidate = layer.root / "workspace" / "models.yaml"
        if candidate.is_file():
            found = candidate
    return found


def active_models_path(target_root: Optional[Path] = None) -> Path:
    """Where the live harness/provider choice is stored.

    Written to the resolved write layer, so a project pins its own harness
    configuration and a bare pip install still has somewhere to put one.
    """
    from phronix.layers import resolve_write_layer

    if target_root is not None:
        return Path(target_root) / "active-models.json"
    return resolve_write_layer().root / "active-models.json"


def _read_level_map() -> Dict[str, Dict[str, Any]]:
    path = models_yaml_path()
    if path is None:
        return dict(_FALLBACK_LEVELS)
    try:
        import yaml

        data = yaml.safe_load(path.read_text()) or {}
        levels = data.get("levels")
        if isinstance(levels, dict) and levels:
            return {str(k): dict(v) for k, v in levels.items() if isinstance(v, dict)}
    except Exception:
        pass
    return dict(_FALLBACK_LEVELS)


def available_providers() -> List[str]:
    """Every provider column present in ``models.yaml``."""
    providers = set()
    for entry in _read_level_map().values():
        providers.update((entry.get("providers") or {}).keys())
    return sorted(providers)


# ---------------------------------------------------------------------------
# The active configuration
# ---------------------------------------------------------------------------

def _default_active_config(level_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    class_by_level = {
        level: str((level_map.get(level) or {}).get("default")
                   or _FALLBACK_LEVELS[level]["default"])
        for level in LEVELS
    }
    return {
        "harnesses": {
            harness: (
                {"provider": provider, "class_by_level": class_by_level}
                if harness == "claude" else {"provider": provider}
            )
            for harness, provider in _DEFAULT_PROVIDER.items()
        }
    }


def load_active_config(target_root: Optional[Path] = None) -> Dict[str, Any]:
    """Read ``active-models.json``, falling back to defaults derived from ``models.yaml``.

    A corrupt or partial file degrades to the defaults for the missing parts
    rather than raising: a bad config here would otherwise block agent rendering
    entirely, which is a much worse failure than running on default models.
    """
    level_map = _read_level_map()
    config = _default_active_config(level_map)
    try:
        path = active_models_path(target_root)
    except Exception:
        return config
    if not path.is_file():
        return config
    try:
        stored = json.loads(path.read_text())
    except Exception:
        return config
    if not isinstance(stored, dict):
        return config
    for harness, entry in (stored.get("harnesses") or {}).items():
        if isinstance(entry, dict):
            config["harnesses"].setdefault(harness, {}).update(entry)
    return config


def save_active_config(config: Dict[str, Any], target_root: Optional[Path] = None) -> Path:
    path = active_models_path(target_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n")
    return path


def resolve_models(
    config: Dict[str, Any], target_root: Optional[Path] = None
) -> Dict[str, Dict[str, str]]:
    """Resolve ``{harness: {level_N: concrete-model-id, provider: name}}``.

    Each harness reads exactly ONE provider column — the one named by its own
    ``provider`` key. Reading another harness's column is the classic failure
    here (an agent once resolved OpenCode's level_2 through the ``ollama``
    column and called a model that host did not serve), so the lookup is
    deliberately keyed on the harness, never scanned across providers.
    """
    level_map = _read_level_map()
    out: Dict[str, Dict[str, str]] = {}
    for harness in HARNESSES:
        entry = config.get("harnesses", {}).get(harness, {})
        provider = str(entry.get("provider") or _DEFAULT_PROVIDER.get(harness, "claude"))
        resolved: Dict[str, str] = {"provider": provider}
        for level in LEVELS:
            spec = level_map.get(level) or {}
            providers = spec.get("providers") or {}
            resolved[level] = str(providers.get(provider) or spec.get("default") or "UNRESOLVED")
        out[harness] = resolved
    return out


def summarize(target_root: Optional[Path] = None) -> List[str]:
    """Human-readable lines describing the live model choice per harness."""
    resolved = resolve_models(load_active_config(target_root), target_root)
    lines = []
    for harness in HARNESSES:
        entry = resolved[harness]
        levels = " ".join(f"{level.replace('level_', 'L')}={entry[level]}" for level in LEVELS)
        lines.append(f"{harness:9s} provider={entry['provider']:10s} {levels}")
    return lines


def update_harness_config(
    harness: str,
    provider: Optional[str] = None,
    class_by_level: Optional[Dict[str, str]] = None,
    target_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Point *harness* at a provider (and, for claude, at per-level classes)."""
    if harness not in HARNESSES:
        raise ValueError(f"unknown harness {harness!r}; expected one of {', '.join(HARNESSES)}")
    config = load_active_config(target_root)
    entry = config["harnesses"].setdefault(harness, {})
    if provider:
        known = available_providers()
        if known and provider not in known:
            raise ValueError(
                f"provider {provider!r} is not in models.yaml (known: {', '.join(known)})")
        entry["provider"] = provider
    if class_by_level:
        entry.setdefault("class_by_level", {}).update(class_by_level)
    path = save_active_config(config, target_root)
    return {"status": "ok", "file": str(path), "harness": harness, "config": entry}


def _choose(prompt: str, options: Sequence[str], default_index: int = 0) -> str:
    print(prompt)
    for i, option in enumerate(options, 1):
        marker = " (default)" if i - 1 == default_index else ""
        print(f"  [{i}] {option}{marker}")
    raw = input(f"Choose [1-{len(options)}]: ").strip()
    if not raw:
        return options[default_index]
    try:
        return options[int(raw) - 1]
    except (ValueError, IndexError):
        return options[default_index]


def main() -> None:
    """Entry point for ``phronix-configure-harness``."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="phronix-configure-harness",
        description="Choose which model provider each harness uses for the four "
                    "capability levels agents are written against.",
    )
    parser.add_argument("--harness", choices=HARNESSES, default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--show", action="store_true", help="Print the live map and exit.")
    args = parser.parse_args()

    if args.show or (not args.harness and not args.provider):
        for line in summarize():
            print(line)
        path = models_yaml_path()
        print(f"\nmenu:  {path or '(none found — using built-in defaults)'}")
        print(f"order: {active_models_path()}")
        if args.show:
            return

    harness = args.harness or _choose("Which harness?", list(HARNESSES))
    providers = available_providers() or ["claude"]
    provider = args.provider or _choose(f"Which provider for {harness}?", providers)
    result = update_harness_config(harness, provider=provider)
    print(f"\n{harness} -> {provider}   (written to {result['file']})")
    print("Re-render agents so they pick this up:  phronix sync agents")


if __name__ == "__main__":
    main()

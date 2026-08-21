"""The numbers that decide how phronix behaves, in a file rather than in code.

Thresholds, intervals and limits were constants scattered across the modules
that read them, which made changing one a code edit and a reinstall. They are
not logic — the right block limit for a laptop is the right block limit
everywhere, but the right graph refresh interval on a 192-thread node is not the
one for a workstation — so they belong somewhere a deployment can own.

Layered exactly like the rest of the store, and for the same reason: a project
should be able to say "rebuild the graph every 15 seconds here" without editing
the wheel or changing it for every other project on the machine.

    bundled   inside the installed package     what phronix ships with
    user      ~/.phronix/workspace             this person, every project
    project   <repo>/.phronix/workspace        this repository

Higher layers override key by key, not file by file: an override naming one
value inherits every other. A file-level shadow would mean copying the whole
file to change one number, and the copy would then rot silently as the shipped
defaults moved on.
"""
from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: Where a layer keeps it, under the layer root.
TUNING_FILE = "workspace/tuning.yaml"

#: Cached, because this is read on hot paths — every skill write asks for a
#: block limit. Cleared by :func:`reload`, which the MCP server's refresh calls
#: so an edit takes effect without a restart.
_CACHE: Optional[Dict[str, Any]] = None
_SOURCES: Dict[str, str] = {}


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import yaml

        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        # A malformed override must not take the framework down: the shipped
        # defaults are always valid, and a broken file is better reported by
        # `phronix tuning` than by an import error in an agent's tool call.
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _merge(base: Dict[str, Any], over: Dict[str, Any],
           prefix: str, source: str) -> Dict[str, Any]:
    """Deep-merge *over* onto *base*, recording where each leaf came from."""
    for key, value in over.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            # Recurse even when the base has nothing here, so every LEAF is
            # attributed. Assigning the group wholesale recorded one source for
            # `skills` and none for `skills.block_limits.rule`, which is the
            # question anyone actually asks — "where did this number come from".
            if not isinstance(base.get(key), dict):
                base[key] = {}
            _merge(base[key], value, path, source)
        else:
            base[key] = value
            _SOURCES[path] = source
    return base


def _layer_roots() -> List[Tuple[str, Path]]:
    """Every layer that may hold tuning, lowest precedence first."""
    from phronix.layers import layers

    # `layers()` yields lowest-precedence first — bundled, then user, then
    # project — which is already the order a merge wants: the most specific
    # layer is applied last and wins. Verified rather than assumed, because
    # reversing it silently made the shipped defaults override the project's.
    return [(layer.name, Path(layer.root)) for layer in layers()]


def load(refresh: bool = False) -> Dict[str, Any]:
    """Every value in force, merged across layers."""
    global _CACHE
    if _CACHE is not None and not refresh:
        return _CACHE

    _SOURCES.clear()
    merged: Dict[str, Any] = {}
    for name, root in _layer_roots():
        _merge(merged, _read(root / TUNING_FILE), "", name)
    _CACHE = merged
    return merged


def reload() -> Dict[str, Any]:
    """Re-read from disk. Called by the server's refresh, so edits take hold."""
    return load(refresh=True)


def get(dotted: str, default: Any = None) -> Any:
    """One value by dotted path: ``get("graph.refresh_seconds")``.

    Falls back to *default* rather than raising. A caller asking for a key that
    an override has deleted should behave as it did before the override existed,
    not crash — the values are tuning, and a missing one means "unchanged".
    """
    node: Any = load()
    for part in str(dotted).split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return copy.deepcopy(node) if isinstance(node, (dict, list)) else node


def source_of(dotted: str) -> str:
    """Which layer supplied a value. Empty when nothing sets it."""
    load()
    return _SOURCES.get(dotted, "")


def flatten(node: Optional[Dict[str, Any]] = None,
            prefix: str = "") -> List[Tuple[str, Any]]:
    """Every leaf as ``(dotted.path, value)``, in file order."""
    if node is None:
        node = load()
    out: List[Tuple[str, Any]] = []
    for key, value in node.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.extend(flatten(value, path))
        else:
            out.append((path, value))
    return out


def _coerce(text: str) -> Any:
    """Turn a command-line string into the type the value already had.

    A tuning file whose numbers are strings is a file whose numbers stop being
    compared: ``"60" > 30`` raises, and ``if "0"`` is true. The shipped value
    decides the type, because the shipped value is the one the reader was
    written against.
    """
    lowered = text.strip().lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            continue
    return text


def set_value(dotted: str, raw: str, layer: str = "project") -> Dict[str, Any]:
    """Write one value into a layer's tuning file, leaving the rest alone.

    Only the key being set is written. Copying the whole file to change one
    number is how an override comes to shadow defaults that have since moved on
    — the copy keeps working and stops being right.
    """
    from phronix.layers import resolve_write_layer

    target = resolve_write_layer(layer)
    path = Path(target.root) / TUNING_FILE

    known = get(dotted, None)
    value = _coerce(raw)
    if known is not None and not isinstance(known, type(value)):
        # Only when the shipped type is unambiguous — bool before int, since
        # `isinstance(True, int)` is true and would let "on" become 1.
        if isinstance(known, bool):
            value = bool(value)
        elif isinstance(known, float) and isinstance(value, int):
            value = float(value)
        elif isinstance(known, int) and isinstance(value, float):
            return {"status": "error",
                    "error": (f"{dotted} is an integer ({known}); {raw!r} is "
                              f"fractional. Round it or change the reader.")}

    current = _read(path)
    node = current
    parts = str(dotted).split(".")
    for part in parts[:-1]:
        node = node.setdefault(part, {})
        if not isinstance(node, dict):
            return {"status": "error",
                    "error": f"{dotted}: {part} already holds a value, not a group"}
    node[parts[-1]] = value

    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    header = ("# phronix tuning overrides for this layer.\n"
              "# Only the keys set here differ from the shipped defaults;\n"
              "# everything else falls through. See `phronix tuning`.\n")
    path.write_text(header + yaml.safe_dump(current, sort_keys=False),
                    encoding="utf-8")
    reload()
    return {"status": "ok", "key": dotted, "value": value,
            "layer": target.name, "file": str(path)}


def unset(dotted: str, layer: str = "project") -> Dict[str, Any]:
    """Remove an override, so the value falls back to the layer beneath."""
    from phronix.layers import resolve_write_layer

    target = resolve_write_layer(layer)
    path = Path(target.root) / TUNING_FILE
    current = _read(path)

    node = current
    parts = str(dotted).split(".")
    for part in parts[:-1]:
        node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return {"status": "absent", "key": dotted, "layer": target.name}
    if parts[-1] not in node:
        return {"status": "absent", "key": dotted, "layer": target.name}
    node.pop(parts[-1])

    import yaml

    path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    reload()
    return {"status": "ok", "key": dotted, "layer": target.name,
            "now": get(dotted), "from": source_of(dotted)}

"""Learning more must not make the system worse at using what it learned.

Every registered MCP tool's name, description and JSON schema is re-sent on
EVERY request. Registering each learned capability as its own tool made that
payload grow without bound: at ~1,150 capabilities it reached 370 KB -- about
95k tokens, half a 200k context window -- before the task prompt was added.
The harness compacted, refilled within three turns, and gave up with
"Autocompact is thrashing".

It degraded in exact step with the store: reuse runs carrying 203 capabilities
lost 11% of attempts to it, 847 lost 98%. That is the failure this module
exists to prevent.
"""
from __future__ import annotations

from typing import Any, Dict, List

import pytest

from phronix import capabilities

pytestmark = pytest.mark.usefixtures("isolated_bundled_layer")


class FakeMCP:
    """Records what a real server would publish a schema for."""

    def __init__(self) -> None:
        self.published: List[str] = []

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        def capture(fn: Any) -> Any:
            self.published.append(kwargs.get("name") or fn.__name__)
            return fn
        if args and callable(args[0]) and not kwargs:
            return capture(args[0])
        return capture


def _write_capability(root, name: str, returns: str = "ok") -> None:
    path = root / f"{name}.py"
    path.write_text(
        "def register(mcp):\n"
        "    @mcp.tool()\n"
        f"    def {name}(value: str = '') -> str:\n"
        f"        '''{name}'''\n"
        f"        return {returns!r} + value\n"
    )


@pytest.fixture()
def capability_dir(tmp_path, monkeypatch):
    root = tmp_path / "tools"
    root.mkdir()

    def visible_files() -> Dict[str, Any]:
        return {p.name: p for p in sorted(root.glob("*.py"))}

    monkeypatch.setattr(capabilities, "visible_files", visible_files)
    return root


def test_small_store_registers_each_capability(capability_dir) -> None:
    """Below the threshold, direct tools -- they are cheap and discoverable."""
    for i in range(3):
        _write_capability(capability_dir, f"cap_{i}")

    mcp = FakeMCP()
    report = capabilities.load_all(mcp, threshold=10)

    assert report["dispatched"] is False
    assert sorted(mcp.published) == ["cap_0", "cap_1", "cap_2"]


def test_large_store_does_not_grow_the_tool_list(capability_dir) -> None:
    """The invariant: published tools must not scale with what was learned."""
    for i in range(50):
        _write_capability(capability_dir, f"cap_{i}")

    mcp = FakeMCP()
    report = capabilities.load_all(mcp, threshold=10)

    assert report["dispatched"] is True
    assert report["tools"] == 50, "all 50 must still be reachable"
    # Two entries regardless of store size: the dispatcher and the search.
    assert len(mcp.published) == 2, f"published {len(mcp.published)} tools, expected 2"


def test_growth_does_not_change_the_published_surface(capability_dir) -> None:
    for i in range(20):
        _write_capability(capability_dir, f"cap_{i}")
    small = FakeMCP()
    capabilities.load_all(small, threshold=10)

    for i in range(20, 400):
        _write_capability(capability_dir, f"cap_{i}")
    large = FakeMCP()
    capabilities.load_all(large, threshold=10)

    assert sorted(large.published) == sorted(small.published)


def test_dispatcher_runs_a_capability(capability_dir) -> None:
    """Reachable, not merely counted."""
    for i in range(20):
        _write_capability(capability_dir, f"cap_{i}", returns="ran:")
    mcp = FakeMCP()
    calls: Dict[str, Any] = {}

    def tool(*args: Any, **kwargs: Any):
        def capture(fn):
            calls[kwargs.get("name") or fn.__name__] = fn
            return fn
        return capture(args[0]) if args and callable(args[0]) and not kwargs else capture

    mcp.tool = tool  # type: ignore[method-assign]
    capabilities.load_all(mcp, threshold=10)

    assert calls["capability_call"]("cap_3", {"value": "x"}) == "ran:x"


def test_dispatcher_explains_an_unknown_name(capability_dir) -> None:
    for i in range(20):
        _write_capability(capability_dir, f"cap_{i}")
    mcp = FakeMCP()
    calls: Dict[str, Any] = {}
    mcp.tool = lambda *a, **k: (lambda fn: calls.setdefault(k.get("name") or fn.__name__, fn))  # type: ignore[method-assign]
    capabilities.load_all(mcp, threshold=10)

    answer = calls["capability_call"]("cap_", None)
    assert "error" in answer
    # A caller that guessed the name needs a route back, not just a refusal.
    assert answer["did_you_mean"], "no suggestions offered for a near miss"


def test_search_finds_a_capability(capability_dir) -> None:
    for i in range(20):
        _write_capability(capability_dir, f"cap_{i}")
    mcp = FakeMCP()
    calls: Dict[str, Any] = {}
    mcp.tool = lambda *a, **k: (lambda fn: calls.setdefault(k.get("name") or fn.__name__, fn))  # type: ignore[method-assign]
    capabilities.load_all(mcp, threshold=10)

    found = calls["capability_search"]("cap_1", limit=5)
    assert found["total"] == 20
    assert "cap_1" in found["names"]

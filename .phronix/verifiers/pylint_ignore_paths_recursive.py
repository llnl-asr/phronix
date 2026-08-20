"""Verifier for software-pylint skill: ignore-paths works with --recursive=y.

Checks that the fix (applying os.path.normpath before ignore checks) actually
prevents ignored paths from being linted when using recursive directory traversal.
"""

import os
import subprocess
import tempfile
from pathlib import Path


SPEC = {
    "kind": "skill",
    "target": "software-pylint",
    "claim": "When using --recursive=y with ignore-paths patterns, pylint correctly "
             "ignores matching paths after os.path.normpath() is applied",
    
    "assumptions": [
        {
            "name": "pylint_installed",
            "detail": "pylint executable is available",
            "check": lambda ctx: (
                subprocess.run(["which", "pylint"], capture_output=True).returncode == 0,
                "pylint must be on PATH"
            )
        },
    ],
    
    "inputs": [
        {
            "name": "test_tree",
            "required": True,
            "resolve": lambda ctx: _create_test_tree()
        },
    ],
    
    "constraints": [
        {
            "name": "ignored_path_not_checked",
            "detail": "files matching ignore-paths pattern are not linted",
            "check": lambda ctx: _check_ignored_path_not_linted(ctx["test_tree"])
        },
        {
            "name": "non_ignored_path_checked",
            "detail": "files not matching ignore-paths are still linted",
            "check": lambda ctx: _check_non_ignored_path_linted(ctx["test_tree"])
        },
    ],
    
    "invariants": [],
    
    "outputs": [],
}


def _create_test_tree():
    """Create a temporary directory structure for testing."""
    tmpdir = tempfile.mkdtemp(prefix="pylint_verify_")
    base = Path(tmpdir)
    
    # Create structure: src/main.py (should be checked) and src/gen/auto.py (should be ignored)
    (base / "src").mkdir()
    (base / "src" / "gen").mkdir()
    
    # Write files with obvious pylint violations
    (base / "src" / "main.py").write_text("x=1\n")  # missing spaces around =
    (base / "src" / "gen" / "auto.py").write_text("y=2\n")  # missing spaces around =
    
    # Write pyproject.toml with ignore-paths
    (base / "pyproject.toml").write_text("""
[tool.pylint.main]
ignore-paths = [
    "^src/gen/.*$",
]
""")
    
    return str(base)


def _check_ignored_path_not_linted(test_tree):
    """Verify that src/gen/auto.py is NOT in pylint output."""
    result = subprocess.run(
        ["pylint", "--recursive=y", "src/"],
        cwd=test_tree,
        capture_output=True,
        text=True
    )
    
    # Check that src/gen/auto.py is NOT mentioned
    output = result.stdout + result.stderr
    ignored_file_checked = "src/gen/auto.py" in output or "gen/auto.py" in output
    
    return (
        not ignored_file_checked,
        f"Ignored file should not appear in output. Output: {output[:500]}"
    )


def _check_non_ignored_path_linted(test_tree):
    """Verify that src/main.py IS in pylint output (it should be checked)."""
    result = subprocess.run(
        ["pylint", "--recursive=y", "src/"],
        cwd=test_tree,
        capture_output=True,
        text=True
    )
    
    # Check that src/main.py IS mentioned
    output = result.stdout + result.stderr
    main_file_checked = "src/main.py" in output or "main.py" in output
    
    return (
        main_file_checked,
        f"Non-ignored file should appear in output. Output: {output[:500]}"
    )


def register(mcp):
    """Register this verifier with the MCP server."""
    pass  # Verifiers don't register tools

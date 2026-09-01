"""Where a skill's files live, asked of the code rather than restated."""

def skill_home_under(root, name, subject=""):
    """Where a skill's files live under *root*, by the same rule the code uses.

    Tests used to hardcode `<root>/skills/<name>`, which was true when every
    skill lived in one place. It is not any more: `skills/` holds the
    framework's METHOD and a problem's ANSWER lives under
    `capabilities/tasks/<subject>/`, so that a from-scratch run can be given
    the first and not the second.

    Asking the code where a skill goes — rather than restating the rule here —
    is what stops a test passing against a layout the system no longer uses.
    """
    from pathlib import Path

    from phronix.skills import skill_home

    del subject                       # the slug decides, not the prose

    # Asked of the code, not restated.
    #
    # This function's whole point was to stop tests pinning a layout the
    # system had moved off, and it restated the rule anyway — so when
    # `capabilities/tasks/<slug>/<slug>/` flattened to
    # `capabilities/skills/<slug>/`, twenty-six tests failed against a path
    # nothing writes any more. `skill_home` is the one place that decides;
    # a `Layer`-shaped stand-in is all it needs to answer for any root.
    class _At:
        def __init__(self, base): self.base = Path(base)
        def dir(self, kind): return self.base / kind

    return skill_home(name, _At(root))


def skill_names_under(root):
    """Every skill filed under *root*, whichever home holds it.

    Tests that counted `<root>/skills/*` were counting one of two stores. A
    skill written by a run is an answer and lives under
    `capabilities/tasks/<subject>/`; only the framework's method stays in
    `skills/`. Counting one store now measures the wrong thing.
    """
    from pathlib import Path

    root = Path(root)
    names = {d.name for d in (root / "skills").glob("*") if d.is_dir()}
    # Both layouts: `capabilities/skills/<name>/` now, and
    # `capabilities/tasks/<slug>/<name>/` in any store written before the
    # flattening — a carry root of 348 answers is not worth invalidating.
    for pattern in ("capabilities/skills/*", "capabilities/tasks/*/*"):
        names |= {d.name for d in root.glob(pattern)
                  if d.is_dir() and (d / "SKILL.md").is_file()}
    return sorted(names)

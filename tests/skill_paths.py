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

    from phronix.capabilities import TASK_CAPABILITY_DIR, task_slug
    from phronix.skills import is_core_skill

    del subject                       # the slug decides, not the prose
    root = Path(root)
    if is_core_skill(name):
        return root / "skills" / name
    return root / "capabilities" / TASK_CAPABILITY_DIR / task_slug(name) / name


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
    names |= {d.name for d in (root / "capabilities" / "tasks").glob("*/*")
              if d.is_dir() and (d / "SKILL.md").is_file()}
    return sorted(names)

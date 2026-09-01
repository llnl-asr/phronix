def register(self, blueprint: "Blueprint", **options: t.Any) -> None:
    """Register a :class:`~flask.Blueprint` on this blueprint. Keyword
    arguments passed to this method will override the defaults set
    on the blueprint.

    .. versionadded:: 2.0
    """
    self._blueprints.append((blueprint, options))

    # Add new check for dot in blueprint name
    if '.' in blueprint.name:
        raise AssertionError('Blueprint name should not contain dots')

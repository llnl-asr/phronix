def register(mcp):
    @mcp.tool()
    def write_imp_shim_file():
        import pathlib, textwrap
        content = textwrap.dedent('''
        # Minimal stub for the deprecated `imp` module required by astroid on Python 3.13.
        # Provides the constants and functions used by astroid's import system.

        # Constants used by astroid (values are placeholders; they just need to be distinct integers)
        C_BUILTIN = 0
        C_EXTENSION = 1
        PKG_DIRECTORY = 2
        PY_COMPILED = 3
        PY_FROZEN = 4
        PY_SOURCE = 5
        # Optional constants that may be referenced in newer Python versions
        PY_RESOURCE = 6
        PY_CODERESOURCE = 7

        def find_module(name, path=None):
            """Simplified implementation of :func:`imp.find_module`.

            Returns a tuple ``(file, pathname, description)`` where ``description`` is a tuple
            ``(type, name, path)``. The ``type`` is one of the constants defined above.
            This minimal implementation uses :mod:`importlib` to locate the module and maps the
            result to the appropriate ``imp`` constants. It is sufficient for astroid's import
            handling on Python 3.13, which only checks the third element of the tuple.
            """
            import importlib.util
            spec = importlib.util.find_spec(name, path)
            if spec is None:
                raise ImportError(name)
            origin = spec.origin
            if origin is None:
                module_type = PKG_DIRECTORY
            elif origin == 'built-in':
                module_type = C_BUILTIN
            elif origin.endswith(('.so', '.pyd', '.dll')):
                module_type = C_EXTENSION
            elif origin.endswith('.pyc'):
                module_type = PY_COMPILED
            elif origin.endswith('.py'):
                module_type = PY_SOURCE
            else:
                module_type = PKG_DIRECTORY
            return (None, origin, (module_type, None, None))
        ''')
        path = pathlib.Path('imp.py')
        path.write_text(content)
        return "imp.py written"
    mcp.register_tool(write_imp_shim_file)

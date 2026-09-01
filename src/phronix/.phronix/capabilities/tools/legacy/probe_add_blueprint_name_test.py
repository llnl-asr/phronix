def register(mcp):
    @mcp.tool()
    def add_blueprint_name_test():
        """Write tests/test_blueprint_name.py that asserts Blueprint with a dot in name raises ValueError.
        This deterministic capability creates the test file.
        """
        import pathlib, textwrap
        test_path = pathlib.Path('tests/test_blueprint_name.py')
        content = textwrap.dedent('''
            import pytest
            from flask import Blueprint

            def test_blueprint_name_dot_invalid():
                with pytest.raises(ValueError):
                    Blueprint('bad.name', __name__)
        ''')
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.write_text(content)
        return 'test file created'

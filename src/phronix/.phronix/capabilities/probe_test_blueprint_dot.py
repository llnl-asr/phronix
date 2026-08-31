def register(mcp):
    @mcp.tool()
    def probe_test_blueprint_dot():
        """Create a temporary test file, run pytest, return True if test passes."""
        import os, subprocess, textwrap, tempfile
        test_code = textwrap.dedent('''
            from flask import Blueprint
            import pytest
            def test_blueprint_dot():
                with pytest.raises(ValueError):
                    Blueprint('admin.api', __name__)
        ''')
        with tempfile.TemporaryDirectory() as td:
            test_path = os.path.join(td, 'test_blueprint_dot.py')
            with open(test_path, 'w') as f:
                f.write(test_code)
            result = subprocess.run(['pytest', '-q', test_path], capture_output=True, text=True)
            return result.returncode == 0
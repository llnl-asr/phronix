def register(mcp):
    @mcp.tool()
    def probe_reproduce_flask_routes_domain(
        repo_path: str,
        server_name: str = "test.local",
        subdomains: str = "admin,test",
    ) -> str:
        """Reproduce a `flask routes` invocation with subdomain blueprints.

        repo_path: path to a Flask checkout with an installed/importable `flask`
        package (run inside the environment where it's installed).
        server_name: value to set as app.config['SERVER_NAME'].
        subdomains: comma-separated subdomain names; one blueprint with a
        '/home' route is registered per subdomain, plus one route with no
        subdomain.

        Returns the captured stdout of `flask routes`, for comparing against
        an issue's expected Domain-column table by eye.
        """
        import subprocess
        import sys
        import textwrap

        names = [s.strip() for s in subdomains.split(",") if s.strip()]
        blueprint_code = "\n".join(
            f"""
bp_{i} = Blueprint('{name}_blueprint', __name__, subdomain='{name}')
@bp_{i}.route('/home')
def home_{i}(): pass
app.register_blueprint(bp_{i})
"""
            for i, name in enumerate(names)
        )

        script = textwrap.dedent(
            f"""
            from flask import Flask, Blueprint
            from click.testing import CliRunner
            from flask.cli import FlaskGroup

            app = Flask(__name__)
            app.config['SERVER_NAME'] = {server_name!r}

            {blueprint_code}

            cli = FlaskGroup(create_app=lambda: app)
            runner = CliRunner()
            result = runner.invoke(cli, ['routes'])
            print(result.output)
            """
        )

        proc = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc.stdout + proc.stderr

def register(mcp):
    @mcp.tool()
    def probe_reproduce_flask_routes_host(
        repo_path: str,
        static_host: str = "static.example.com",
        hosts: str = "a.example.com,b.example.com",
    ) -> str:
        """Reproduce a `flask routes` invocation with host_matching enabled.

        repo_path: path to a Flask checkout with an installed/importable
        `flask` package (run inside the environment where it's installed).
        static_host: value passed as Flask(static_host=...), required when
        host_matching=True and a static folder is configured.
        hosts: comma-separated host values; one route with '/x' is
        registered per host.

        Returns the captured stdout of `flask routes`, for comparing
        against the expected Host-column table by eye.
        """
        import subprocess
        import sys
        import textwrap

        names = [s.strip() for s in hosts.split(",") if s.strip()]
        route_code = "\n".join(
            f"""
@app.route('/x{i}', host={host!r})
def x_{i}(): pass
"""
            for i, host in enumerate(names)
        )

        script = textwrap.dedent(
            f"""
            from flask import Flask
            from click.testing import CliRunner
            from flask.cli import FlaskGroup

            app = Flask(__name__, static_host={static_host!r})
            app.url_map.host_matching = True

            {route_code}

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

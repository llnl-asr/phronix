def register(mcp):
    @mcp.tool()
    def probe_routes_sort_all_methods_interplay(repo_path: str) -> str:
        """Verify `flask routes -s endpoint` and `--all-methods` still work
        correctly together with a conditional Host/Subdomain column.

        repo_path: path to a Flask checkout with an installed/importable
        `flask` package (run inside the environment where it's installed).

        Registers routes with subdomain_matching enabled and mixed HTTP
        methods, then runs `flask routes -s endpoint` and
        `flask routes --all-methods`, returning both outputs concatenated
        for comparison by eye: sorting should be unaffected and the
        Methods column should expand to include HEAD/OPTIONS when
        --all-methods is passed, with the Subdomain column still present.
        """
        import subprocess
        import sys
        import textwrap

        script = textwrap.dedent(
            """
            from flask import Flask
            from click.testing import CliRunner
            from flask.cli import FlaskGroup

            app = Flask(__name__, static_folder=None)
            app.config['SERVER_NAME'] = 'test.local'
            app.url_map.host_matching = False
            app.subdomain_matching = True

            @app.route('/b', subdomain='b', methods=['POST'])
            def b(): pass

            @app.route('/a', subdomain='a')
            def a(): pass

            cli = FlaskGroup(create_app=lambda: app)
            runner = CliRunner()
            r1 = runner.invoke(cli, ['routes', '-s', 'endpoint'])
            r2 = runner.invoke(cli, ['routes', '--all-methods'])
            print("--- sorted by endpoint ---")
            print(r1.output)
            print("--- all methods ---")
            print(r2.output)
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

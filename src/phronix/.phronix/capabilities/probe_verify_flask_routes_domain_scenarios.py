import subprocess
import sys
import textwrap


def register(mcp):
    @mcp.tool()
    def probe_verify_flask_routes_domain_scenarios(repo_src_path: str, scenario: str) -> str:
        """Run `flask routes` for one of a fixed set of domain-matching
        scenarios against the flask checkout at repo_src_path (a directory
        containing the 'flask' package, prepended to sys.path) and return the
        captured stdout table so it can be compared to expected Domain values.

        scenario is one of:
          'subdomain_and_server_name'   - blueprint subdomain='admin' + SERVER_NAME set
          'host_matching'               - host_matching=True with host='admin.<SERVER_NAME>'
          'server_name_only'            - SERVER_NAME set, no subdomain rules
          'subdomain_no_server_name'    - subdomain set but SERVER_NAME unset
          'no_domain_matching'          - plain app, no subdomain/host_matching/SERVER_NAME
        """
        scenarios = {
            "subdomain_and_server_name": """
                app = Flask(__name__)
                app.config['SERVER_NAME'] = 'test.local'
                bp = Blueprint('admin', __name__, subdomain='admin')
                @bp.route('/')
                def index(): return 'ok'
                app.register_blueprint(bp)
                @app.route('/')
                def root(): return 'ok'
            """,
            "host_matching": """
                app = Flask(__name__, host_matching=True, static_host='static.test.local')
                @app.route('/', host='admin.test.local')
                def index(): return 'ok'
            """,
            "server_name_only": """
                app = Flask(__name__)
                app.config['SERVER_NAME'] = 'test.local'
                @app.route('/')
                def index(): return 'ok'
            """,
            "subdomain_no_server_name": """
                app = Flask(__name__)
                bp = Blueprint('admin', __name__, subdomain='admin')
                @bp.route('/')
                def index(): return 'ok'
                app.register_blueprint(bp)
            """,
            "no_domain_matching": """
                app = Flask(__name__)
                @app.route('/')
                def index(): return 'ok'
            """,
        }
        if scenario not in scenarios:
            return f"error: unknown scenario {scenario!r}; choices: {sorted(scenarios)}"

        script = textwrap.dedent(f"""
            import sys
            sys.path.insert(0, {repo_src_path!r})
            from flask import Flask, Blueprint
            from flask.cli import routes_command
            from click.testing import CliRunner

            {textwrap.indent(textwrap.dedent(scenarios[scenario]), "            ")}

            runner = CliRunner()
            result = runner.invoke(routes_command, [], obj=None, standalone_mode=False,
                                    prog_name='flask')
            with app.app_context():
                result = runner.invoke(routes_command, [])
            print(result.output)
        """)
        try:
            out = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=60,
            )
        except Exception as e:
            return f"error: {e}"
        return f"returncode={out.returncode}\nstdout:\n{out.stdout}\nstderr:\n{out.stderr[-2000:]}"

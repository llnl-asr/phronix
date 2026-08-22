import os


def register(mcp):
    @mcp.tool()
    def add_ignore_path_recursive_current_dir_test(repo_root: str) -> str:
        """Insert the test_ignore_path_recursive_current_dir regression
        test into tests/test_self.py, right before
        TestRunTC.test_recursive_current_dir. Idempotent. Returns a status
        string.
        """
        path = os.path.join(repo_root, "tests", "test_self.py")
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if "def test_ignore_path_recursive_current_dir" in content:
            return "already applied: test_ignore_path_recursive_current_dir present"

        marker = "    def test_recursive_current_dir(self):"
        if marker not in content:
            return "error: could not find insertion point (test_recursive_current_dir)"

        test_code = '''    def test_ignore_path_recursive_current_dir(self) -> None:
        """Tests recursive run of linter ignoring directory using --ignore-path parameter.

        Test uses the same testset as test_ignore_path_recursive but the pylint run
        changes to the directory HERE/regrtest_data/directory first and then runs
        pylint with "." as argument.
        """
        with _test_sys_path():
            # pytest is including directory HERE/regrtest_data to sys.path which causes
            # astroid to believe that directory is a package.
            sys.path = [
                path
                for path in sys.path
                if not os.path.basename(path) == "regrtest_data"
            ]
            with _test_cwd():
                os.chdir(join(HERE, "regrtest_data", "directory"))
                self._runtest(
                    [
                        ".",
                        "--recursive=y",
                        "--ignore-paths=.*ignored.*",
                    ],
                    code=0,
                )

'''
        content = content.replace(marker, test_code + marker, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return "applied: inserted test_ignore_path_recursive_current_dir"

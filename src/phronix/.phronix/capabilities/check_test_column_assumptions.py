def register(mcp):
    import subprocess

    @mcp.tool()
    def check_test_column_assumptions(test_file_path: str) -> str:
        """Grep test_file_path for helpers/assertions that depend on a
        table's column-0 content or fixed row layout (e.g. `expect_order`,
        `line[:len`, `startswith`, `.split()[0]`). Use this before adding a
        new leading column to CLI table output, to see which existing tests
        would break if the new column shifted column 0."""
        cmd = [
            "grep", "-n", "-E",
            "expect_order|line\\[:len|startswith|\\.split\\(\\)\\[0\\]|class Test",
            test_file_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return res.stdout or res.stderr or "no matches"

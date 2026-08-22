def register(mcp):
    @mcp.tool()
    def probe_ignore_paths_matrix(repo_path: str, module_path: str = "pylint.lint.expand_modules") -> str:
        """Import *module_path* from a repo on sys.path and exercise its
        `_is_ignored_file` function across a matrix of path forms: relative
        arg + relative pattern, absolute arg + relative pattern, relative arg
        + absolute pattern, absolute arg + absolute pattern, nested subdir,
        and a sibling directory sharing a name prefix (false-positive check).
        Builds a throwaway package tree under a temp dir, runs the matrix,
        and reports pass/fail per case with the raw element/pattern used.
        Use this both to reproduce a path-normalization bug and to verify a
        candidate fix against the same case set."""
        import sys, os, re, tempfile, shutil, importlib

        sys.path.insert(0, repo_path)
        try:
            mod = importlib.import_module(module_path)
            importlib.reload(mod)
        except Exception as e:
            return f"IMPORT ERROR: {e}"

        tmp = tempfile.mkdtemp(prefix="ignore_paths_probe_")
        try:
            pkg = os.path.join(tmp, "testpkg")
            sub = os.path.join(pkg, "sub")
            os.makedirs(sub)
            open(os.path.join(pkg, "__init__.py"), "w").close()
            open(os.path.join(sub, "__init__.py"), "w").close()
            target = os.path.join(sub, "leaf.py")
            open(target, "w").close()

            rel_target = os.path.relpath(target, tmp)
            abs_target = os.path.abspath(target)

            cases = [
                ("rel_arg+rel_pattern", rel_target, r"^testpkg/sub/.*$"),
                ("abs_arg+rel_pattern", abs_target, r"^testpkg/sub/.*$"),
                ("rel_arg+abs_pattern", rel_target, "^" + re.escape(os.path.join(tmp, "testpkg/sub")) + r"/.*$"),
                ("abs_arg+abs_pattern", abs_target, "^" + re.escape(os.path.join(tmp, "testpkg/sub")) + r"/.*$"),
                ("sibling_false_positive", os.path.join(tmp, "testpkg_other", "leaf.py"), r"^testpkg/sub/.*$"),
            ]

            results = []
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                for name, element, pattern in cases:
                    compiled = [re.compile(pattern)]
                    try:
                        ignored = mod._is_ignored_file(element, [], [], compiled)
                    except Exception as e:
                        ignored = f"ERROR: {e}"
                    expect_ignored = name != "sibling_false_positive"
                    ok = (ignored == expect_ignored)
                    results.append(f"{name}: element={element!r} pattern={pattern!r} -> ignored={ignored} expected={expect_ignored} {'OK' if ok else 'MISMATCH'}")
            finally:
                os.chdir(cwd)

            return "\n".join(results)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            if repo_path in sys.path:
                sys.path.remove(repo_path)

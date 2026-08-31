"""Generate test instances for pylint ignore-paths with --recursive=y.

Covers combinations of:
- Path forms: normalized, with ./, with //, relative, absolute
- Ignore pattern types: regex prefix (^path/.*$), directory name, suffix
- Directory structures: nested packages, nested dirs without __init__, single level
- File types: .py files, __init__.py, package directories
"""

def register(mcp):
    @mcp.tool()
    def generate_pylint_ignore_test_instances() -> str:
        """Generate test instances for pylint --recursive=y ignore-paths testing.
        
        Returns JSON array of instance objects with name, behaviour, command, expected, dimensions, and source.
        """
        import json
        import itertools
        
        instances = []
        
        # Dimensions
        path_forms = ["with_dot_slash", "with_double_slash", "normalized", "relative"]
        ignore_patterns = [
            ("regex_prefix", "^src/gen/.*$", "src/gen/"),
            ("regex_dir_name", ".*/gen/.*", "nested/gen/"),
            ("regex_suffix", ".*_generated\\.py$", "file_generated.py")
        ]
        dir_structures = [
            ("nested_package", "src/subdir/gen", "has __init__.py"),
            ("nested_dir_no_init", "src/gen/modules", "no __init__.py"),
            ("single_level", "gen", "single directory")
        ]
        file_types = [
            ("python_file", "test.py"),
            ("init_file", "__init__.py")
        ]
        
        counter = 0
        
        # Generate combinations
        for path_form, (pattern_type, pattern, example_path), (struct_type, struct_path, struct_desc), (file_type, filename) in itertools.product(
            path_forms, ignore_patterns, dir_structures, file_types
        ):
            # Skip some invalid combinations
            if pattern_type == "regex_suffix" and file_type == "init_file":
                continue  # __init__.py won't match *_generated.py
                
            counter += 1
            
            # Build test path based on path_form
            test_path = f"{struct_path}/{filename}"
            if path_form == "with_dot_slash":
                test_path = f"./{test_path}"
            elif path_form == "with_double_slash":
                test_path = test_path.replace("/", "//", 1)
            elif path_form == "relative":
                test_path = f"../{test_path}"
            # normalized stays as-is
            
            instances.append({
                "name": f"test_{counter:03d}_{path_form}_{pattern_type}_{struct_type}_{file_type}",
                "behaviour": f"Files matching pattern '{pattern}' should be ignored when using --recursive=y, even with {path_form} paths in {struct_type} structure",
                "command": f"pylint --recursive=y {struct_path.split('/')[0]}/",
                "expected": f"File {test_path} matching ignore pattern should not appear in pylint output",
                "dimensions": {
                    "path_form": path_form,
                    "ignore_pattern_type": pattern_type,
                    "directory_structure": struct_type,
                    "file_type": file_type
                },
                "source": "generated"
            })
        
        # Add some edge cases
        instances.append({
            "name": "edge_case_root_relative",
            "behaviour": "Root-relative paths (starting with /) should work with ignore-paths",
            "command": "pylint --recursive=y /abs/path/to/src/",
            "expected": "Absolute paths should be normalized and checked against ignore patterns",
            "dimensions": {
                "path_form": "absolute",
                "ignore_pattern_type": "regex_prefix",
                "directory_structure": "nested_dir_no_init",
                "file_type": "python_file"
            },
            "source": "edge_case"
        })
        
        instances.append({
            "name": "edge_case_windows_backslash",
            "behaviour": "Windows-style paths (with backslashes) should be normalized",
            "command": "pylint --recursive=y src\\\\gen\\\\",
            "expected": "Backslash paths should be converted to forward slashes for regex matching",
            "dimensions": {
                "path_form": "normalized",
                "ignore_pattern_type": "regex_prefix", 
                "directory_structure": "nested_dir_no_init",
                "file_type": "python_file"
            },
            "source": "windows_specific"
        })
        
        return json.dumps(instances, indent=2)

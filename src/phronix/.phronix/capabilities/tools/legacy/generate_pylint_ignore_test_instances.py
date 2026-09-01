#!/usr/bin/env python3
"""Generate test instances for pylint ignore-paths with --recursive bug."""

import json
from itertools import product


def register(mcp):
    @mcp.tool()
    def generate_pylint_ignore_test_instances() -> str:
        """Generate test instances for pylint ignore-paths testing.
        
        Returns JSON array of test instances covering:
        - Different path formats (./path, path, path//file, etc.)
        - Different ignore pattern types
        - Different recursive modes
        - Different target locations (ignored vs allowed)
        """
        path_formats = [
            ("relative_with_dot", "./"),
            ("relative_without_dot", ""),
            ("double_slash", "//"),
            ("normalized", "")
        ]
        
        ignore_patterns = [
            ("simple_prefix", "^src/gen/.*$", "src/gen/"),
            ("regex_pattern", "^.*/gen/.*\\.py$", "src/gen/"),
            ("nested_path", "^src/gen/subdir/.*$", "src/gen/subdir/")
        ]
        
        recursive_modes = [
            ("recursive_y", "--recursive=y"),
            ("recursive_current_dir", ".")
        ]
        
        target_locations = [
            ("ignored_subdir", "gen/test.py", True),  # Should be ignored
            ("ignored_file", "gen/test.py", True),    # Should be ignored
            ("allowed_file", "main.py", False)        # Should be checked
        ]
        
        instances = []
        instance_id = 1
        
        for (path_fmt_name, path_prefix), (pattern_name, ignore_regex, base_path), \
            (mode_name, recursive_flag), (location_name, target_file, should_ignore) in \
            product(path_formats, ignore_patterns, recursive_modes, target_locations):
            
            # Construct the actual path based on format
            if path_fmt_name == "double_slash":
                # Insert double slash in the middle of path
                if "/" in base_path:
                    parts = base_path.split("/", 1)
                    actual_path = f"{parts[0]}//{parts[1]}{target_file}"
                else:
                    actual_path = f"{base_path}//{target_file}"
            elif path_fmt_name == "relative_with_dot":
                actual_path = f"./{base_path}{target_file}"
            else:
                actual_path = f"{base_path}{target_file}"
            
            # Only include test cases where the pattern should match the location
            # Skip cases where pattern and location don't align
            if pattern_name == "nested_path" and "subdir" not in target_file:
                continue
            if pattern_name == "simple_prefix" and location_name == "allowed_file":
                should_ignore = False
            
            instance = {
                "name": f"test_{instance_id:03d}_{path_fmt_name}_{pattern_name}_{mode_name}_{location_name}",
                "behaviour": f"Test that pylint with {recursive_flag} and ignore-paths='{ignore_regex}' correctly {'ignores' if should_ignore else 'checks'} file at path '{actual_path}'",
                "command": f"pylint {recursive_flag} --ignore-paths='{ignore_regex}' {actual_path}",
                "expected": f"Path {actual_path} should {'not appear in output' if should_ignore else 'be linted'}",
                "dimensions": {
                    "path_format": path_fmt_name,
                    "ignore_pattern_type": pattern_name,
                    "recursive_mode": mode_name,
                    "target_location": location_name
                },
                "source": "generated"
            }
            instances.append(instance)
            instance_id += 1
        
        return json.dumps(instances, indent=2)

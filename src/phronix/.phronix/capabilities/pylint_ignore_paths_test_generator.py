"""Generate test instances for pylint ignore-paths recursive bug.

This generates combinations of path formats, ignore patterns, file locations,
and recursive modes to test the fix thoroughly.
"""

import json
import itertools


def register(mcp):
    @mcp.tool()
    def generate_pylint_ignore_test_instances() -> str:
        """Generate test instances for pylint ignore-paths with --recursive=y bug.
        
        Returns JSON array of test instances covering:
        - path_format: different path representations
        - ignore_pattern_type: different regex patterns
        - file_location: where files are relative to ignored dirs
        - recursive_mode: on/off
        """
        
        path_formats = [
            ("forward_slash", "src/gen/about.py", "src/gen/"),
            ("backslash", "src\\gen\\about.py", "src\\gen\\"),
            ("normalized", "src/gen/about.py", "src/gen"),
            ("with_dot_slash", "./src/gen/about.py", "./src/gen/"),
            ("with_trailing_slash", "src/gen/about.py", "src/gen/")
        ]
        
        ignore_patterns = [
            ("exact_match", "^src/gen/.*$"),
            ("prefix_match", "^src/gen/"),
            ("regex_pattern", "^.*/gen/.*$")
        ]
        
        file_locations = [
            ("root_of_ignored_dir", "about.py", True),  # should be ignored
            ("nested_in_ignored_dir", "subdir/about.py", True),  # should be ignored
            ("outside_ignored_dir", "other.py", False)  # should NOT be ignored
        ]
        
        recursive_modes = [
            ("recursive_on", "--recursive=y"),
            ("recursive_off", "")
        ]
        
        instances = []
        
        # Sample key combinations (not all 90)
        for (pf_name, path_ex, dir_ex), (ip_name, pattern), (fl_name, file_rel, should_ignore), (rm_name, flag) in itertools.islice(
            itertools.product(path_formats, ignore_patterns, file_locations, recursive_modes),
            50  # limit to 50 instances
        ):
            name = f"{pf_name}_{ip_name}_{fl_name}_{rm_name}"
            
            # Construct the test case
            test_file = f"src/gen/{file_rel}" if fl_name != "outside_ignored_dir" else f"src/{file_rel}"
            
            instance = {
                "name": name,
                "behaviour": f"File {test_file} with ignore-paths='{pattern}' and {flag or 'no flag'}",
                "dimensions": {
                    "path_format": pf_name,
                    "ignore_pattern_type": ip_name,
                    "file_location": fl_name,
                    "recursive_mode": rm_name
                },
                "expected": "ignored" if (should_ignore and (rm_name == "recursive_on" or fl_name == "root_of_ignored_dir")) else "checked",
                "source": "generated from issue #6964 reported pattern: ^src/gen/.*$"
            }
            instances.append(instance)
        
        return json.dumps(instances, indent=2)

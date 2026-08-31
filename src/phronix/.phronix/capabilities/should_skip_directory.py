"""Check if a directory should be skipped during recursive file discovery.

A directory should be skipped if:
1. It exactly matches an ignored directory pattern
2. It's a subdirectory of an ignored directory
"""

from typing import List
import os


def register(mcp):
    @mcp.tool()
    def should_skip_directory(dir_path: str, ignored_dirs: List[str]) -> bool:
        """Check if directory should be skipped based on ignore patterns.
        
        Args:
            dir_path: The directory path being checked (from os.walk)
            ignored_dirs: List of directory paths extracted from ignore-paths patterns
            
        Returns:
            True if the directory should be skipped, False otherwise
            
        Example:
            >>> should_skip_directory("src/gen", ["src/gen"])
            True
            >>> should_skip_directory("src/gen/subdir", ["src/gen"])
            True
            >>> should_skip_directory("src/other", ["src/gen"])
            False
        """
        # Normalize the dir_path to use forward slashes
        normalized_dir = dir_path.replace('\\', '/')
        
        for ignored_dir in ignored_dirs:
            # Normalize ignored pattern
            ignored_normalized = ignored_dir.replace('\\', '/')
            
            # Check if paths match exactly
            if normalized_dir == ignored_normalized:
                return True
            
            # Check if dir_path is a subdirectory of ignored_dir
            # src/gen/subdir should match ignored pattern src/gen
            if normalized_dir.startswith(ignored_normalized + '/'):
                return True
                
            # Also check the other way - if the pattern is more specific
            # e.g., if walking "src" and pattern is "src/gen"
            # we don't skip "src" itself, only "src/gen"
            # This is already handled by the above checks
        
        return False

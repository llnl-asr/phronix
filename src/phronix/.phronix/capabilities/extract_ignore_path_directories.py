"""Extract directory paths from ignore-paths regex patterns.

Given regex patterns like ^src/gen/.*$ that are meant to match files,
extract the directory portion (src/gen) so we can skip walking into
those directories entirely.
"""

import re
from typing import Pattern, List


def register(mcp):
    @mcp.tool()
    def extract_ignore_path_directories(patterns: List[str]) -> List[str]:
        """Extract literal directory paths from ignore-paths regex patterns.
        
        Args:
            patterns: List of regex pattern strings (not compiled Pattern objects)
            
        Returns:
            List of directory path strings extracted from the patterns
            
        Example:
            >>> extract_ignore_path_directories(["^src/gen/.*$", "^build/.*$"])
            ["src/gen", "build"]
        """
        directories = []
        
        for pattern_str in patterns:
            # Remove common regex anchors and wildcards
            # ^src/gen/.*$ -> src/gen
            cleaned = pattern_str
            
            # Remove leading ^
            if cleaned.startswith("^"):
                cleaned = cleaned[1:]
            
            # Remove trailing $ 
            if cleaned.endswith("$"):
                cleaned = cleaned[:-1]
                
            # Remove trailing /.*  or /.* or /*
            cleaned = re.sub(r'/\.?\*+$', '', cleaned)
            
            # If there's still something left and it looks like a path
            if cleaned and ('/' in cleaned or '\\' in cleaned):
                # Normalize to forward slashes
                cleaned = cleaned.replace('\\', '/')
                directories.append(cleaned)
        
        return directories

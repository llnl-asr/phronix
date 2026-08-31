"""Document the fix applied to resolve pylint issue #7080.

Records the symptom, root cause, and exact fix for the ignore-paths regression
in recursive mode.
"""

def register(mcp):
    @mcp.tool()
    def research_document_fix(approach_name: str, fix_location: str, fix_description: str) -> str:
        """Document a research finding and its implementation.
        
        Args:
            approach_name: Name of the approach that was implemented
            fix_location: File and line where the fix was applied
            fix_description: Description of what was changed and why
            
        Returns:
            Formatted documentation string
        """
        doc = f"""
# Fix Documentation

## Approach: {approach_name}

## Location: {fix_location}

## Description:
{fix_description}

## Root Cause:
Paths passed to _is_ignored_file() in recursive mode contained redundant
separators (e.g., ./src/gen/) which prevented regex patterns like ^src/gen/.*$
from matching. The non-recursive code path (expand_modules) normalized paths
at line 110 with os.path.normpath(), but the recursive path (_discover_files)
did not normalize before calling _is_ignored_file().

## Fix:
Added path normalization at the start of _is_ignored_file() so both code paths
benefit from normalized paths when checking ignore patterns. This is the same
fix merged in upstream PR #7080.

## Impact:
- Files matching ignore-paths patterns are now correctly excluded in recursive mode
- No changes to non-recursive behavior
- Single line addition with minimal risk
"""
        return doc
